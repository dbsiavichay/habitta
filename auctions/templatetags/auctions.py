from django import template
from realty.models import Specification
from ..models import Auction

register = template.Library()

@register.simple_tag
def get_auction(obj):
	try:
	    auction = Auction.objects.get(property = obj, stage = Auction.OPEN)
	    auction._check_stage()
	except Auction.DoesNotExist:
		return
	finally:
		if auction.stage == Auction.OPEN:
			return auction
