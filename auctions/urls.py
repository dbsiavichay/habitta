from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import (
	AuctionCreateView,
)

urlpatterns = [	
	path('property/<int:pk>/auction/add/', login_required(AuctionCreateView.as_view()), name='add_auction'),
	#path('paypal/<int:pk>/process/', login_required(PaypalPaymentView.as_view()), name='process_paypal_payment'),
]