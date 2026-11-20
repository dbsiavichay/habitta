"""Prepara una COPIA de la base de datos para tomar las capturas de los manuales de uso.

El dump trae datos reales y los manuales son públicos. Este comando:
- anonimiza a los usuarios (nombres ficticios, correos @ejemplo.com, teléfonos falsos, sin fotos);
- quita teléfonos y correos de las descripciones y especificaciones de los anuncios;
- borra mensajes, pagos, sesiones, inicios de sesión con redes y el historial del admin;
- deja cuentas bancarias, comentarios y comprobantes de ejemplo;
- siembra lo que muestran los manuales: pagos en cada estado (por los archivos de un anuncio de
  Planos, que marca como vendible), una subasta con ofertas, conversaciones y favoritos.

Sólo corre sobre una base cuyo nombre termine en `_capturas`. Ver "Capturas de los manuales" en el
README. Nunca borra anuncios ni imágenes: sus señales borrarían archivos de media/, que se comparte
con la base real.
"""
import json
import re
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.auctions.models import Auction, Offer
from apps.authentication.models import Profile, SocialNetwork, SocialNetworkProfile, SocialProfile
from apps.comments.models import Comment
from apps.logs.models import Log
from apps.messenger.models import Conversation, Message
from apps.payments.models import Bank, BankPayment, Payment, PaypalPayment
from apps.payments.views import get_server_price
from apps.project.models import Settings as ProjectSettings
from apps.realty.models import Category, Property, Specification

FIRST_NAMES = ('Ana', 'Carlos', 'Sofía', 'Diego', 'Valeria', 'Andrés', 'Camila', 'Mateo', 'Lucía', 'Javier',
               'Paula', 'Gabriel', 'Daniela', 'Martín', 'Isabel', 'Tomás', 'Elena', 'Ricardo', 'Natalia', 'Felipe')
LAST_NAMES = ('Torres', 'Mena', 'Andrade', 'Vega', 'Paredes', 'Salazar', 'Cordero', 'Ruiz', 'Herrera', 'Molina',
              'Castro', 'Ortiz', 'Rojas', 'Navarro', 'Benítez', 'Cevallos', 'Aguirre', 'Delgado', 'Romero', 'Flores')
COMMENTS = ('¿Sigue disponible?', 'Me interesa, ¿se puede visitar el fin de semana?', '¿El precio es negociable?')

# Celulares (09…, +593 9…, 9 dígitos sin el 0) y fijos con código de área, también entre paréntesis:
# (07) 2700 337.
PHONE_RE = re.compile(r'(?:\+?593[\s-]?\(?|\(?\b0)[2-9]\)?(?:[\s.-]?\d){6,8}\b|\b9\d{8}\b')
# Especificaciones con datos de contacto: su valor se reemplaza entero (un fijo de 7 dígitos no se
# distingue de un precio por el formato).
CONTACT_SPEC_RE = re.compile(r'\btel|whats|celu|fijo|contacto|correo electr|\be-?mail|sitio web|nombre', re.IGNORECASE)
EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
# Nombre de una persona tras "Informes:", "Contacto:"…: "INFORMES: Josué Aguilera 099…".
CONTACT_NAME_RE = re.compile(
    r'((?i:informes|información|contactos?|atención|llamar a)\s*:?\s+)'
    r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})'
)
VOUCHER_NAME = 'payments/bankvouchers/capturas-comprobante.png'


def scrub(text, owner_name='Habitta'):
    """Quita teléfonos, correos y nombres de contacto de un texto libre (el nombre pasa a ser el del dueño)."""
    if not isinstance(text, str):
        return text
    text = PHONE_RE.sub('099 000 0000', text)
    text = EMAIL_RE.sub('contacto@ejemplo.com', text)
    return CONTACT_NAME_RE.sub(lambda match: match.group(1) + owner_name, text)


class Command(BaseCommand):
    help = 'Anonimiza una copia de la base (nombre terminado en _capturas) y siembra datos para las capturas de los manuales.'

    def add_arguments(self, parser):
        parser.add_argument('--sesiones', action='store_true',
                            help='Sólo crea sesiones para ana.torres, carlos.mena y sofia y las imprime en JSON '
                                 '(las lee scripts/manual_screenshots.py).')
        parser.add_argument('--limpiar', action='store_true',
                            help='Sólo borra las sesiones y, de media/, el comprobante de ejemplo que crea este comando.')

    def handle(self, *args, **options):
        name = settings.DATABASES['default']['NAME']
        if not str(name).endswith('_capturas'):
            raise CommandError(
                f'La base "{name}" no termina en "_capturas". Este comando reescribe usuarios y borra datos: '
                'córrelo sólo sobre la copia para las capturas.'
            )
        if options['sesiones']:
            self.stdout.write(json.dumps(self.sessions()))
            return
        if options['limpiar']:
            Session.objects.all().delete()
            if default_storage.exists(VOUCHER_NAME):
                default_storage.delete(VOUCHER_NAME)
            self.stdout.write(self.style.SUCCESS('Sesiones y comprobante de ejemplo borrados.'))
            return

        with transaction.atomic():
            self.anonymize()
            self.spread_dates()
            ana, carlos, others = self.demo_users()
            self.scrub_listings()
            self.seed_payments(ana, carlos, others)
            self.seed_conversations(ana, carlos, others)
            self.seed_auction(ana, carlos, others)
            self.seed_favorites(ana, carlos)
        self.stdout.write(self.style.SUCCESS(
            f'Listo. Usuario demo: {ana.username} (id {ana.pk}); interesado: {carlos.username} (id {carlos.pk}); '
            'administradora: sofia.'
        ))

    def sessions(self):
        """Cookies `sessionid` de los usuarios demo ({'ana': clave, 'carlos': …, 'sofia': …}) y, en 'ids',
        los registros de ejemplo que usan las rutas de las capturas ('/admin/…/{pago_pendiente}/change/')."""
        from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
        from django.contrib.sessions.backends.db import SessionStore

        data = {}
        users = {}
        for alias, username in (('ana', 'ana.torres'), ('carlos', 'carlos.mena'), ('sofia', 'sofia')):
            user = users[alias] = User.objects.get(username=username)
            session = SessionStore()
            session[SESSION_KEY] = str(user.pk)
            session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
            session[HASH_SESSION_KEY] = user.get_session_auth_hash()
            session.create()
            data[alias] = session.session_key

        auction = Auction.objects.filter(stage=Auction.OPEN, property__user=users['ana']).order_by('-pk').first()
        listings = Property.objects.filter(user=users['ana']).exclude(pk=auction.property_id if auction else None)
        listing = listings.annotate(photos=Count('images')).filter(photos__gte=4).order_by('pk').first()
        salable = Property.objects.filter(category__is_salable=True).exclude(user=users['ana']).order_by('pk').first()
        pending = BankPayment.objects.filter(status=Payment.REGISTRY).order_by('-date').first()
        spec = Specification.objects.filter(field_type='ChoiceField').order_by('pk').first()
        data['ids'] = {
            'ana': users['ana'].pk,
            'anuncio': listing.pk if listing else 0,
            'anuncio_subasta': auction.property_id if auction else 0,
            'subasta': auction.pk if auction else 0,
            'planos': salable.pk if salable else 0,
            'pago_pendiente': pending.pk if pending else 0,
            'conversacion': Conversation.objects.filter(owner=users['carlos'], member=users['ana']).values_list('pk', flat=True).first() or 0,
            'categoria': listing.category_id if listing else 0,
            'especificacion': spec.pk if spec else 0,
            'portada': ProjectSettings.objects.filter(is_active=True).values_list('pk', flat=True).first() or 0,
        }
        return data

    # ------------------------------------------------------------------ anonimizar
    def anonymize(self):
        reserved = {('Ana', 'Torres'), ('Carlos', 'Mena'), ('Sofía', 'Andrade')}  # los de demo_users
        for index, user in enumerate(User.objects.order_by('pk')):
            first = FIRST_NAMES[index % len(FIRST_NAMES)]
            last = LAST_NAMES[(index * 7 + index // len(LAST_NAMES)) % len(LAST_NAMES)]
            if (first, last) in reserved:
                last = LAST_NAMES[(LAST_NAMES.index(last) + 1) % len(LAST_NAMES)]
            username = f'usuario{user.pk}'
            User.objects.filter(pk=user.pk).update(
                first_name=first, last_name=last, username=username, email=f'{username}@ejemplo.com',
            )
        Profile.objects.update(image=None)
        for profile in Profile.objects.all():
            Profile.objects.filter(pk=profile.pk).update(phone=f'0990000{profile.user_id % 1000:03d}')

        for index, bank in enumerate(Bank.objects.order_by('pk'), start=1):
            Bank.objects.filter(pk=bank.pk).update(
                account_number=f'2200{index:06d}', recipient_name=f'{settings.SITE_NAME} Demo S.A.',
                recipient_charter='1790000000001',
            )
        for index, comment in enumerate(Comment.objects.order_by('pk')):
            Comment.objects.filter(pk=comment.pk).update(content=COMMENTS[index % len(COMMENTS)])

        Message.objects.all().delete()
        Conversation.objects.all().delete()
        Payment.objects.all().delete()
        SocialProfile.objects.all().delete()
        SocialNetworkProfile.objects.all().delete()
        Session.objects.all().delete()
        LogEntry.objects.all().delete()

    def scrub_listings(self):
        """Contactos en descripciones y especificaciones; va después de demo_users para usar sus nombres."""
        contact_specs = {
            str(spec.pk): spec.name for spec in Specification.objects.all()
            if CONTACT_SPEC_RE.search(f'{spec.name} {spec.internal_name}')
        }
        for listing in Property.objects.select_related('user'):
            owner = listing.user.get_full_name() or settings.SITE_NAME
            details = listing.details or {}
            specs = details.get('specifications')
            if isinstance(specs, dict):
                details['specifications'] = {
                    key: (self.fake_contact(contact_specs[key], owner) if key in contact_specs and value else scrub(value, owner))
                    for key, value in specs.items()
                }
            Property.objects.filter(pk=listing.pk).update(description=scrub(listing.description, owner), details=details)

    @staticmethod
    def fake_contact(spec_name, owner):
        name = spec_name.lower()
        if 'correo' in name or 'mail' in name:
            return 'contacto@ejemplo.com'
        if 'web' in name:
            return 'www.ejemplo.com'
        if 'nombre' in name:
            return owner
        return '099 000 0000'

    def spread_dates(self):
        """Reparte publicaciones y registros en los últimos 12 meses: el dump es de 2020 y el gráfico del
        dashboard saldría vacío."""
        now = timezone.now()
        for index, pk in enumerate(Property.objects.order_by('pk').values_list('pk', flat=True)):
            Property.objects.filter(pk=pk).update(pub_date=now - timedelta(days=(index * 37) % 360 + 2, hours=index % 9))
        for index, pk in enumerate(User.objects.order_by('pk').values_list('pk', flat=True)):
            User.objects.filter(pk=pk).update(date_joined=now - timedelta(days=(index * 53) % 365 + 1, hours=index % 7))

    def demo_users(self):
        """Ana (la que más publica), Carlos (un interesado) y Sofía (superusuaria)."""
        ana = (User.objects.filter(is_staff=False).annotate(listings=Count('property'))
               .order_by('-listings', 'pk').first())
        carlos = User.objects.filter(is_staff=False).exclude(pk=ana.pk).order_by('pk').first()
        for user, username, first, last, phone in (
            (ana, 'ana.torres', 'Ana', 'Torres', '0991234567'),
            (carlos, 'carlos.mena', 'Carlos', 'Mena', '0987654321'),
        ):
            user.username, user.first_name, user.last_name = username, first, last
            user.email = f'{username}@ejemplo.com'
            user.save()
            Profile.objects.filter(user=user).update(phone=phone)

        sofia, _ = User.objects.get_or_create(username='sofia')
        sofia.first_name, sofia.last_name, sofia.email = 'Sofía', 'Andrade', 'sofia@ejemplo.com'
        sofia.is_staff = sofia.is_superuser = True
        sofia.set_unusable_password()
        sofia.save()

        network = SocialNetwork.objects.filter(name__icontains='facebook').first()
        if network:
            SocialNetworkProfile.objects.create(social_network=network, profile=ana.profile, username='ana.torres.demo')

        others = list(User.objects.filter(is_staff=False).exclude(pk__in=[ana.pk, carlos.pk]).order_by('pk')[:4])
        return ana, carlos, others

    # ------------------------------------------------------------------ sembrar
    def voucher(self, amount):
        from PIL import Image, ImageDraw, ImageFont

        image = Image.new('RGB', (720, 960), '#ffffff')
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 720, 150), fill='#0b6e5f')
        draw.text((48, 52), 'Comprobante de transferencia', fill='#ffffff', font=ImageFont.load_default(size=34))
        draw.text((48, 98), 'Documento de ejemplo', fill='#cfe7e2', font=ImageFont.load_default(size=22))
        rows = ('Banco: Banco de ejemplo', 'Cuenta destino: 2200000001', f'Beneficiario: {settings.SITE_NAME} Demo S.A.',
                f'Monto: USD {amount}', 'Referencia: 000123456', 'Estado: Acreditada')
        for line, text in enumerate(rows):
            draw.text((48, 220 + line * 70), text, fill='#13211e', font=ImageFont.load_default(size=28))
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        if default_storage.exists(VOUCHER_NAME):
            default_storage.delete(VOUCHER_NAME)
        return default_storage.save(VOUCHER_NAME, ContentFile(buffer.getvalue()))

    def seed_payments(self, ana, carlos, others):
        """Compras de los archivos de un anuncio de Planos: la categoría que vende archivos, aunque en el
        dump no está marcada como vendible."""
        Category.objects.filter(name__iexact='Planos').update(is_salable=True)
        listing = (Property.objects.filter(category__is_salable=True).exclude(user__in=[ana, carlos]).order_by('pk').first()
                   or Property.objects.filter(user=ana).order_by('pk').first())
        bank = Bank.objects.order_by('pk').first()
        if not (listing and bank):
            return
        amount = get_server_price(listing) or Decimal('25.00')
        content_type = ContentType.objects.get_for_model(Property)
        voucher = self.voucher(amount)
        now = timezone.now()
        for payer, status, days in (
            (carlos, Payment.REJECTED, 12),
            (carlos, Payment.CONFIRMED, 10),
            (others[0], Payment.REGISTRY, 0),
            (others[1], Payment.REGISTRY, 1),
            (others[2], Payment.CONFIRMED, 4),
            (others[3], Payment.REJECTED, 9),
        ):
            payment = BankPayment.objects.create(
                user=payer, amount=amount, status=status, bank=bank, voucher=voucher,
                content_type=content_type, object_id=listing.pk,
            )
            Payment.objects.filter(pk=payment.pk).update(date=now - timedelta(days=days, hours=2))
        paypal = PaypalPayment.objects.create(
            user=others[-1], amount=amount, status=Payment.CONFIRMED, payment_id='CAPTURA-0001',
            payer_id='DEMO', payer_email='comprador@ejemplo.com', content_type=content_type, object_id=listing.pk,
        )
        Payment.objects.filter(pk=paypal.pk).update(date=now - timedelta(days=6))

    def conversation(self, owner, member, lines, unread_last=False):
        conversation = Conversation.objects.create(owner=owner, member=member)
        start = timezone.now() - timedelta(hours=len(lines))
        for index, (sender, text) in enumerate(lines):
            message = Message.objects.create(conversation=conversation, sender=sender, content=text)
            read = None if unread_last and index == len(lines) - 1 else start + timedelta(hours=index, minutes=5)
            Message.objects.filter(pk=message.pk).update(create_date=start + timedelta(hours=index), read_at=read)
        Conversation.objects.filter(pk=conversation.pk).update(create_date=start)

    def seed_conversations(self, ana, carlos, others):
        listing = Property.objects.filter(user=ana).order_by('pk').first()
        title = ((listing.title or '').strip() or listing.category.singular_name).capitalize() if listing else 'Casa'
        self.conversation(carlos, ana, [
            (carlos, f'Hola, Ana. Vi tu anuncio «{title}». ¿Sigue disponible?'),
            (ana, '¡Hola, Carlos! Sí, sigue disponible. ¿Te gustaría visitarlo?'),
            (carlos, 'Sí, me encantaría. ¿Podría ser este sábado en la mañana?'),
            (ana, 'Perfecto, el sábado a las 10:00. Te comparto la ubicación exacta por aquí.'),
            (carlos, 'Gracias. Una pregunta más: ¿el precio es negociable?'),
        ], unread_last=True)
        if others:
            self.conversation(others[0], ana, [
                (others[0], 'Buenas tardes, ¿aceptan mascotas?'),
                (ana, 'Buenas tardes. Sí, mascotas pequeñas.'),
            ])
            self.conversation(carlos, others[1], [
                (carlos, 'Hola, ¿el servicio incluye materiales?'),
                (others[1], 'Hola, Carlos. Sí, los materiales básicos están incluidos.'),
            ])

    def seed_auction(self, ana, carlos, others):
        busy = Auction.objects.filter(stage=Auction.OPEN).values('property')
        # Un anuncio con fotos; el primero queda libre para las capturas de «Ver un anuncio».
        candidates = list(Property.objects.filter(user=ana).exclude(pk__in=busy)
                          .annotate(photos=Count('images')).filter(photos__gte=4).order_by('pk')[:2])
        listing = candidates[-1] if candidates else Property.objects.filter(user=ana).exclude(pk__in=busy).first()
        if not listing:
            return
        now = timezone.now()
        auction = Auction.objects.create(
            property=listing, start_date=now - timedelta(days=1), ending_date=now + timedelta(days=3, hours=5),
            base_amount=Decimal('85000.00'), stage=Auction.OPEN,
        )
        for bidder, amount in ((carlos, '86000.00'), *zip(others[:2], ('88500.00', '90000.00'))):
            Offer.objects.create(auction=auction, user=bidder, amount=Decimal(amount))

    def seed_favorites(self, ana, carlos):
        for listing in Property.objects.exclude(user=ana).order_by('-pk')[:4]:
            Log.objects.get_or_create(type=Log.LIKE, property=listing, user=ana)
        for listing in Property.objects.filter(user=ana).order_by('pk')[:3]:
            Log.objects.get_or_create(type=Log.LIKE, property=listing, user=carlos)
