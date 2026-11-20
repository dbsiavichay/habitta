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


@override_settings(MEDIA_ROOT=MEDIA_ROOT, SITE_URL='https://habitta.test')
class BankPaymentAdminTests(TestCase):
    """Confirmar y rechazar transferencias desde el admin (fase B del rediseño del admin)."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = create_user('revisora', is_staff=True, is_superuser=True)
        cls.buyer = create_user('ana')
        cls.listing = create_listing(create_user('luis'), title='Planos casa')
        cls.content_type = ContentType.objects.get_for_model(Property)
        cls.bank = Bank.objects.create(name='Banco Pichincha', account_number='2200123456', account_type=2,
                                       recipient_name='Habitta', recipient_charter='1790000000001')

    def setUp(self):
        self.client.force_login(self.staff)

    def transfer(self, status=Payment.REGISTRY):
        return BankPayment.objects.create(user=self.buyer, object_id=self.listing.pk, content_type=self.content_type,
                                          amount=Decimal('15.00'), status=status, bank=self.bank,
                                          voucher=SimpleUploadedFile('v.png', b'png', content_type='image/png'))

    def action_url(self, payment, name):
        return reverse(f'admin:payments_bankpayment_{name}', args=[payment.pk])

    def test_dialog_opens_without_changing_anything(self):
        payment = self.transfer()
        response = self.client.get(self.action_url(payment, 'reject_payment'))
        self.assertContains(response, '¿Rechazar esta transferencia?')
        self.assertContains(response, 'name="reason"')
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.REGISTRY)

    def test_confirm_notifies_the_user(self):
        from django.core import mail

        payment = self.transfer()
        response = self.client.post(self.action_url(payment, 'confirm_payment'), {'_form_submitted': 'on'},
                                    HTTP_HX_REQUEST='true', HTTP_HX_CURRENT_URL='http://testserver/admin/payments/bankpayment/')
        self.assertEqual(response.headers['HX-Redirect'], 'http://testserver/admin/payments/bankpayment/')
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.CONFIRMED)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['ana@example.com'])
        self.assertEqual(email.subject, 'Confirmamos tu pago en Habitta')
        self.assertIn('https://habitta.test' + reverse('downloads'), email.body)
        self.assertIn('Planos casa', email.alternatives[0][0])

    def test_reject_sends_the_reason(self):
        from django.core import mail

        payment = self.transfer()
        self.client.post(self.action_url(payment, 'reject_payment'),
                         {'_form_submitted': 'on', 'reason': 'El monto no coincide.'})
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.REJECTED)
        self.assertEqual(mail.outbox[0].subject, 'No pudimos confirmar tu pago en Habitta')
        self.assertIn('Motivo: El monto no coincide.', mail.outbox[0].body)
        self.assertIn(reverse('list_bank_payment'), mail.outbox[0].body)

    def test_resolved_transfers_are_not_touched(self):
        from django.core import mail

        payment = self.transfer(status=Payment.REJECTED)
        response = self.client.post(self.action_url(payment, 'confirm_payment'), {'_form_submitted': 'on'}, follow=True)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.REJECTED)
        self.assertEqual(mail.outbox, [])
        self.assertContains(response, 'ya estaba resuelta')

    def test_bulk_actions_only_resolve_pending(self):
        from django.core import mail

        pending, confirmed = self.transfer(), self.transfer(status=Payment.CONFIRMED)
        self.client.post(reverse('admin:payments_bankpayment_changelist'), {
            'action': 'reject_selected', '_selected_action': [pending.pk, confirmed.pk],
        })
        pending.refresh_from_db()
        confirmed.refresh_from_db()
        self.assertEqual((pending.status, confirmed.status), (Payment.REJECTED, Payment.CONFIRMED))
        self.assertEqual(len(mail.outbox), 1)

    def test_detail_hides_actions_once_resolved(self):
        pending, done = self.transfer(), self.transfer(status=Payment.CONFIRMED)
        self.assertContains(self.client.get(reverse('admin:payments_bankpayment_change', args=[pending.pk])),
                            self.action_url(pending, 'confirm_payment'))
        self.assertNotContains(self.client.get(reverse('admin:payments_bankpayment_change', args=[done.pk])),
                               self.action_url(done, 'confirm_payment'))

    def test_staff_without_change_permission_cannot_resolve(self):
        from django.contrib.auth.models import Permission

        viewer = create_user('mirona', is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename='view_bankpayment'))
        self.client.force_login(viewer)
        payment = self.transfer()
        response = self.client.post(self.action_url(payment, 'confirm_payment'), {'_form_submitted': 'on'})
        self.assertEqual(response.status_code, 403)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.REGISTRY)
