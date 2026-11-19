"""Pruebas de subastas en el panel (fase 3).

    docker compose exec web python manage.py test apps.auctions.tests
"""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.auctions.models import Auction, Offer
from apps.project.testing import create_listing, create_user


class AuctionPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user('ana')
        cls.other = create_user('luis')
        cls.listing = create_listing(cls.owner)
        cls.theirs = create_listing(cls.other, name='Lotes', title='Lote ajeno')
        now = timezone.now()
        cls.open = Auction.objects.create(property=cls.listing, start_date=now, ending_date=now + timedelta(days=2), base_amount=1000)
        cls.expired = Auction.objects.create(property=cls.listing, start_date=now - timedelta(days=3), ending_date=now - timedelta(hours=1), base_amount=500)
        cls.foreign = Auction.objects.create(property=cls.theirs, start_date=now, ending_date=now + timedelta(days=1), base_amount=200)
        Offer.objects.create(user=cls.other, auction=cls.open, amount=1100)
        Offer.objects.create(user=cls.other, auction=cls.open, amount=1250)

    def setUp(self):
        self.client.force_login(self.owner)

    def test_list_only_shows_my_auctions_and_closes_expired(self):
        response = self.client.get(reverse('auctions'))
        self.assertTemplateUsed(response, 'layouts/app.html')
        auctions = {a.pk: a for a in response.context['object_list']}
        self.assertEqual(set(auctions), {self.open.pk, self.expired.pk})
        self.assertEqual(auctions[self.open.pk].offers_count, 2)
        self.assertEqual(auctions[self.open.pk].best_offer, 1250)
        self.expired.refresh_from_db()
        self.assertEqual(self.expired.stage, Auction.CLOSED)
        self.assertContains(response, reverse('cancel_auction', args=[self.open.pk]))
        self.assertNotContains(response, reverse('cancel_auction', args=[self.expired.pk]))

    def test_cancel_open_auction(self):
        response = self.client.post(reverse('cancel_auction', args=[self.open.pk]), follow=True)
        self.assertRedirects(response, reverse('auctions'))
        self.open.refresh_from_db()
        self.assertEqual(self.open.stage, Auction.CANCELED)
        self.assertContains(response, 'Cancelaste la subasta')

    def test_cannot_cancel_someone_elses_auction(self):
        self.assertEqual(self.client.post(reverse('cancel_auction', args=[self.foreign.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('cancel_auction', args=[self.open.pk])).status_code, 405)
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.stage, Auction.OPEN)

    def test_create_auction(self):
        Auction.objects.filter(pk=self.open.pk).update(stage=Auction.CLOSED)
        response = self.client.get(reverse('add_auction') + f'?id={self.listing.pk}')
        self.assertTemplateUsed(response, 'layouts/app.html')
        self.assertEqual(list(response.context['form'].fields['property'].queryset), [self.listing])

        response = self.client.post(reverse('add_auction'), {'property': self.listing.pk, 'base_amount': '1500', 'duration': '72'}, follow=True)
        self.assertRedirects(response, reverse('auctions'))
        self.assertContains(response, 'Tu subasta está abierta hasta')
        self.assertTrue(Auction.objects.filter(property=self.listing, stage=Auction.OPEN, base_amount=1500).exists())

    def test_without_available_listings_shows_empty_state(self):
        self.client.force_login(create_user('eva'))
        response = self.client.get(reverse('add_auction'))
        self.assertContains(response, 'No tienes anuncios para subastar')
