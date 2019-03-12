from django.urls import path
from django.contrib.auth.decorators import login_required
from authentication.decorators import owner_required
from .views import (
	PaypalPaymentView, PaypalPaymentExecuteView
)

urlpatterns = [	
	path('paypal/<int:pk>/process/', login_required(PaypalPaymentView.as_view()), name='process_paypal_payment'),	
	path('paypal/execute/', login_required(PaypalPaymentExecuteView.as_view()), name='execute_paypal_payment'),	
]