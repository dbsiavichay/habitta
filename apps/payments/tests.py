"""Pruebas de pagos y descargas en el panel (fase 3).

    docker compose exec web python manage.py test apps.payments.tests
"""
import shutil
import tempfile
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.payments.models import Bank, BankPayment, Payment, PaypalPayment
from apps.project.testing import create_listing, create_user
from apps.realty.models import Property

MEDIA_ROOT = tempfile.mkdtemp(prefix='habitta-tests-')


def tearDownModule():
    shutil.rmtree(MEDIA_ROOT, ignore_errors=True)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PaymentPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.buyer = create_user('ana')
        cls.seller = create_user('luis')
        cls.listing = create_listing(cls.seller, title='Planos casa')
        cls.content_type = ContentType.objects.get_for_model(Property)
        cls.bank = Bank.objects.create(name='Banco Pichincha', account_number='2200123456', account_type=2,
                                       recipient_name='Habitta', recipient_charter='1790000000001')

    def setUp(self):
        self.client.force_login(self.buyer)

    def payment(self, model=PaypalPayment, status=Payment.CONFIRMED, **extra):
        return model.objects.create(user=self.buyer, object_id=self.listing.pk, content_type=self.content_type,
                                    amount=120000, status=status, **extra)

    def test_my_payments_lists_bank_and_paypal(self):
        self.payment(PaypalPayment, payment_id='ORDER-1')
        self.payment(BankPayment, status=Payment.REGISTRY, bank=self.bank, voucher=SimpleUploadedFile('v.pdf', b'%PDF-1.4'))
        Payment.objects.create(user=self.seller, object_id=self.listing.pk, content_type=self.content_type, amount=1)
        response = self.client.get(reverse('list_bank_payment'))
        self.assertTemplateUsed(response, 'layouts/app.html')
        self.assertEqual(len(response.context['object_list']), 2)
        self.assertContains(response, 'PayPal')
        self.assertContains(response, 'Transferencia · Banco Pichincha')
        self.assertContains(response, 'En revisión')
        self.assertContains(response, 'Ver comprobante')

    def test_downloads_only_link_confirmed_payments(self):
        confirmed = self.payment(PaypalPayment, payment_id='ORDER-1')
        pending = self.payment(PaypalPayment, status=Payment.REGISTRY, payment_id='ORDER-2')
        rejected = self.payment(PaypalPayment, status=Payment.REJECTED, payment_id='ORDER-3')
        response = self.client.get(reverse('downloads'))
        self.assertEqual({p.pk for p in response.context['object_list']}, {confirmed.pk, pending.pk})
        self.assertContains(response, reverse('download', args=[confirmed.pk]))
        self.assertNotContains(response, reverse('download', args=[pending.pk]))
        self.assertNotContains(response, reverse('download', args=[rejected.pk]))
        self.assertContains(response, 'Pago en revisión')

    def test_bank_payment_flow_uses_the_session(self):
        response = self.client.post(reverse('select_method_payment'), {
            'amount': '1', 'object_id': self.listing.pk, 'content_type': self.content_type.pk,
        })
        self.assertTemplateUsed(response, 'layouts/app.html')
        self.assertContains(response, 'Banco Pichincha')
        self.assertContains(response, 'Planos casa')
        self.assertEqual(Decimal(self.client.session['amount']), Decimal('120000'))

        response = self.client.get(reverse('add_bank_payment'))
        self.assertEqual(Decimal(response.context['form'].initial['amount']), Decimal('120000'))

        response = self.client.post(reverse('add_bank_payment'), {
            'amount': '120000', 'bank': self.bank.pk, 'voucher': SimpleUploadedFile('v.pdf', b'%PDF-1.4'),
        }, follow=True)
        self.assertRedirects(response, reverse('list_bank_payment'))
        self.assertContains(response, 'Registramos tu pago')
        payment = BankPayment.objects.get(user=self.buyer)
        self.assertEqual(payment.object_id, self.listing.pk)
        self.assertNotIn('object_id', self.client.session)

    def test_without_pending_payment_shows_empty_state(self):
        for url in (reverse('select_method_payment'), reverse('add_bank_payment')):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), 'No tienes un pago en curso')
