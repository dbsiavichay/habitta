from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Bank, BankPayment, PaypalPayment


@admin.register(Bank)
class BankAdmin(ModelAdmin):
	pass


@admin.register(BankPayment)
class BankPaymentAdmin(ModelAdmin):
	pass


@admin.register(PaypalPayment)
class PaypalPaymentAdmin(ModelAdmin):
	pass
