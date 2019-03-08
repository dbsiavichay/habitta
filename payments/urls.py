from django.urls import path
from django.contrib.auth.decorators import login_required
from authentication.decorators import owner_required
from .views import (
	PaypalView
)

urlpatterns = [	
	path('paypal/<int:pk>/', login_required(PaypalView.as_view()), name='paypal_payment'),	
	path('paypal/exito/', login_required(PaypalView.as_view()), name='aceptar_pago_paypal'),	
]