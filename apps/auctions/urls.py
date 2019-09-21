from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import (
	AuctionListView, AuctionCreateView,OfferCreateView
)

urlpatterns = [	
	path('auctions/', login_required(AuctionListView.as_view()), name='auctions'),
	path('auction/add/', login_required(AuctionCreateView.as_view()), name='add_auction'),
	path('offer/add/', login_required(OfferCreateView.as_view()), name='add_offer'),
	#path('paypal/<int:pk>/process/', login_required(PaypalPaymentView.as_view()), name='process_paypal_payment'),
]