"""Cambia la marca anterior (Larbit) por la actual en el contenido que vive en la base de datos.

    python manage.py rebrand_content --dry-run      # muestra qué cambiaría, sin guardar nada
    python manage.py rebrand_content [--legal-name "Habitta S.A."] [--domain habitta.ec]

- Ajustes del sitio (``Settings.title``/``subtitle``): «LARBIT» → ``SITE_NAME``.
- Términos y condiciones (``Term``): «Larbit Company S.A.» → ``LEGAL_NAME``, ``www.larbit.com`` →
  dominio de ``SITE_URL`` y cualquier otro «Larbit» → ``SITE_NAME``.
- Fuente de íconos de especificaciones (``Icons``): los archivos de ``larbitfonts/`` pasan a
  ``spec_icons/`` con el nombre ``spec-icons`` (también dentro del CSS y del SVG).

Los datos de los usuarios (nombres, anuncios) y el historial del admin no se tocan. Es idempotente:
una segunda corrida no encuentra nada que cambiar.
"""
import os
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.project.models import Icons, Settings, Term

# «Larbit Company S.A.», «Larbit company S.A», «LARBIT COMPANY S. A.»
LEGAL_RE = re.compile(r'larbit\s+company\s+s\.?\s?a\b\.?', re.IGNORECASE)
DOMAIN_RE = re.compile(r'(?:https?://)?www\.larbit\.com\b', re.IGNORECASE)
# «Larbit» suelto; no toca correos, dominios ni rutas (larbitecuador@…, www.larbit.com, /larbit)
WORD_RE = re.compile(r'(?<![\w.@/])larbit(?!\.\w|[\w@])', re.IGNORECASE)
# Dentro de los archivos de la fuente sí se cambia todo: font-family, «fonts/larbit.eot» e id del SVG
ICONS_RE = re.compile(r'larbit', re.IGNORECASE)
SENTENCE_END_RE = re.compile(r'(?:\s*$|\s*\n|\s+[A-ZÁÉÍÓÚÑ¿¡(“"])')

OLD_ICONS_DIR = 'larbitfonts/'
NEW_ICONS_DIR = 'spec_icons'
NEW_ICONS_NAME = 'spec-icons'
ICONS_TITLE = 'Íconos de especificaciones'
FONT_FIELDS = ('eot', 'svg', 'ttf', 'woff')
TEXT_EXTENSIONS = ('.css', '.svg')


def _snippet(text, start, end, width=28):
    before = text[max(0, start - width):start]
    after = text[end:end + width]
    return ' '.join(('…' + before + '[' + text[start:end] + ']' + after + '…').split())


class Rebrander:
    """Aplica los reemplazos a un texto y recuerda cada cambio para el informe."""

    def __init__(self, site_name, legal_name, domain):
        self.site_name = site_name
        self.legal_name = legal_name
        self.domain = domain

    def legal(self, match):
        text = match.string
        new = self.legal_name
        # «S.A.» puede cerrar la oración: el punto se conserva si después empieza otra
        if match.group(0).endswith('.') and not new.endswith('.') and SENTENCE_END_RE.match(text, match.end()):
            new += '.'
        return new

    def apply(self, text):
        """Devuelve (texto_nuevo, [(fragmento_original, reemplazo), ...])."""
        changes = []
        rules = [(LEGAL_RE, self.legal)]
        if self.domain:
            rules.append((DOMAIN_RE, lambda m: self.domain))
        rules.append((WORD_RE, lambda m: self.site_name))

        for regex, replace in rules:
            def record(match, replace=replace):
                new = replace(match)
                changes.append((_snippet(match.string, match.start(), match.end()), new))
                return new
            text = regex.sub(record, text)
        return text, changes


class Command(BaseCommand):
    help = 'Reemplaza la marca anterior (Larbit) en los ajustes, los términos y la fuente de íconos.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Muestra los cambios sin guardarlos.')
        parser.add_argument('--legal-name', default=None, help='Razón social para los términos (por defecto LEGAL_NAME).')
        parser.add_argument('--domain', default=None, help='Dominio que reemplaza a www.larbit.com (por defecto el de SITE_URL).')

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        legal_name = (options['legal_name'] or settings.LEGAL_NAME or settings.SITE_NAME).strip()
        domain = (options['domain'] or urlsplit(settings.SITE_URL).netloc or '').strip()
        if not legal_name:
            raise CommandError('Falta la razón social: define LEGAL_NAME o usa --legal-name.')
        if not domain:
            self.stdout.write(self.style.WARNING(
                'SITE_URL está vacío y no se pasó --domain: «www.larbit.com» no se reemplaza.'
            ))
        self.rebrander = Rebrander(settings.SITE_NAME, legal_name, domain)
        self.total = 0
        self.pending_deletes = []

        if self.dry_run:
            self.stdout.write(self.style.NOTICE('Modo --dry-run: no se guarda nada.'))

        with transaction.atomic():
            self.rebrand_settings()
            self.rebrand_terms()
            self.move_icons()
            if self.dry_run:
                transaction.set_rollback(True)
            else:
                transaction.on_commit(self.delete_old_files)

        verb = 'Se cambiarían' if self.dry_run else 'Se cambiaron'
        self.stdout.write(self.style.SUCCESS('%s %d fragmentos.' % (verb, self.total)))
        self.report_leftovers()

    # ------------------------------------------------------------------ textos

    def rebrand_fields(self, obj, label, fields, tidy=False):
        dirty = []
        for field in fields:
            old = getattr(obj, field) or ''
            new, changes = self.rebrander.apply(old)
            if tidy:
                new = re.sub(r' {2,}', ' ', new).strip()
            if new == old:
                continue
            setattr(obj, field, new)
            dirty.append(field)
            self.total += max(len(changes), 1)
            self.stdout.write('%s · %s: %d cambio(s)' % (label, field, max(len(changes), 1)))
            for snippet, replacement in changes:
                self.stdout.write('    %s  →  %s' % (snippet, replacement))
            if tidy and not changes:
                self.stdout.write('    espacios: %r  →  %r' % (old, new))
        if dirty and not self.dry_run:
            obj.save(update_fields=dirty)

    def rebrand_settings(self):
        for obj in Settings.objects.all():
            self.rebrand_fields(obj, 'Ajustes #%s' % obj.pk, ('title', 'subtitle'), tidy=bool(WORD_RE.search(obj.title or '')))

    def rebrand_terms(self):
        for term in Term.objects.order_by('order', 'pk'):
            self.rebrand_fields(term, 'Término #%s «%s»' % (term.pk, term.title), ('title', 'description'))

    # ------------------------------------------------------------------ fuente de íconos

    def new_icons_name(self, field, old_name):
        # Nombres fijos: el CSS reescrito apunta a «fonts/spec-icons.<ext>»
        ext = os.path.splitext(old_name)[1].lower()
        folder = NEW_ICONS_DIR if field == 'css' else '%s/fonts' % NEW_ICONS_DIR
        return '%s/%s%s' % (folder, NEW_ICONS_NAME, ext)

    def move_icons(self):
        for icons in Icons.objects.order_by('pk'):
            moves = []
            for field in FONT_FIELDS + ('css',):
                file = getattr(icons, field)
                if file and file.name.startswith(OLD_ICONS_DIR):
                    moves.append((field, file, self.new_icons_name(field, file.name)))
            rename = bool(ICONS_RE.search(icons.name))
            if not moves and not rename:
                continue

            self.stdout.write('Íconos #%s «%s»:' % (icons.pk, icons.name))
            if rename:
                self.stdout.write('    nombre  →  %s' % ICONS_TITLE)
                self.total += 1
            for field, file, new_name in moves:
                self.stdout.write('    %s  →  %s' % (file.name, new_name))
                self.total += 1

            if self.dry_run:
                continue
            for field, file, new_name in moves:
                storage = file.storage
                if not storage.exists(file.name):
                    raise CommandError('No existe el archivo %s (campo %s de Íconos #%s).' % (file.name, field, icons.pk))
                with storage.open(file.name, 'rb') as source:
                    content = source.read()
                if os.path.splitext(new_name)[1] in TEXT_EXTENSIONS:
                    content = ICONS_RE.sub(NEW_ICONS_NAME, content.decode('utf-8')).encode('utf-8')
                if storage.exists(new_name):
                    storage.delete(new_name)
                saved = storage.save(new_name, ContentFile(content))
                self.pending_deletes.append((storage, file.name))
                setattr(icons, field, saved)
            if rename:
                icons.name = ICONS_TITLE
            icons.save()

    def delete_old_files(self):
        for storage, name in self.pending_deletes:
            if storage.exists(name):
                storage.delete(name)
        self.pending_deletes = []

    # ------------------------------------------------------------------ informe

    def report_leftovers(self):
        if self.dry_run:
            return
        leftovers = []
        for obj in Settings.objects.all():
            leftovers += ['Ajustes #%s' % obj.pk for value in (obj.title, obj.subtitle) if 'larbit' in (value or '').lower()]
        for term in Term.objects.all():
            if 'larbit' in (term.title + term.description).lower():
                leftovers.append('Término #%s' % term.pk)
        if leftovers:
            self.stdout.write(self.style.WARNING(
                'Aún mencionan «larbit» (p. ej. correos o palabras compuestas; revísalos en el admin): %s'
                % ', '.join(sorted(set(leftovers)))
            ))
