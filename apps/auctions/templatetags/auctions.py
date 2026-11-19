from django import template
from ..models import Auction

register = template.Library()

@register.simple_tag
def get_auction(obj):
	try:
	    auction = Auction.objects.get(property = obj, stage = Auction.OPEN)
	    auction._check_stage()
	except Auction.DoesNotExist:
		return
	else:
		if auction.stage == Auction.OPEN:
			return auction

@register.simple_tag
def get_offers(obj):
	offers = obj.offer_set.all().order_by('-amount')[:5]
	return offers
