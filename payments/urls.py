from django.urls import path
from django.contrib.auth.decorators import login_required
from authentication.decorators import owner_required
from .views import (
	SelectMethodPaymentView, BankPaymentCreateView, BankPaymentListView,
	PaypalPaymentView, PaypalPaymentExecuteView
)

urlpatterns = [	
	path('select-method/<int:pk>/<int:ct>/', login_required(SelectMethodPaymentView.as_view()), name='select_method_payment'),
	path('bank/payment/list/', login_required(BankPaymentListView.as_view()), name='list_bank_payment'),	
	path('bank/payment/add/', login_required(BankPaymentCreateView.as_view()), name='add_bank_payment'),	

	path('paypal/<int:pk>/process/', login_required(PaypalPaymentView.as_view()), name='process_paypal_payment'),	
	path('paypal/execute/', login_required(PaypalPaymentExecuteView.as_view()), name='execute_paypal_payment'),	
]