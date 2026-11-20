from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import (
	MethodPaymentListView, BankPaymentCreateView, BankPaymentListView,
	PaypalPaymentCreateView, PaypalPaymentExecuteView,
	DownloadListView, DownloadView
)

urlpatterns = [	
	path('method/select/', login_required(MethodPaymentListView.as_view()), name='select_method_payment'),
	path('bank/payment/list/', login_required(BankPaymentListView.as_view()), name='list_bank_payment'),	
	path('bank/payment/add/', login_required(BankPaymentCreateView.as_view()), name='add_bank_payment'),	

	path('paypal/payment/add/', login_required(PaypalPaymentCreateView.as_view()), name='add_paypal_payment'),	
	path('paypal/execute/', login_required(PaypalPaymentExecuteView.as_view()), name='execute_paypal_payment'),	



	path('downloads/', login_required(DownloadListView.as_view()), name='downloads'),    		
	path('<int:pk>/download/', login_required(DownloadView.as_view()), name='download'),    		
]