from django.contrib import admin
from .models import Bank, BankPayment, PaypalPayment

class BankAdmin(admin.ModelAdmin):
	pass

class BankPaymentAdmin(admin.ModelAdmin):
	pass

class PaypalPaymentAdmin(admin.ModelAdmin):
	pass

admin.site.register(Bank, BankAdmin)
admin.site.register(BankPayment, BankPaymentAdmin)
admin.site.register(PaypalPayment, PaypalPaymentAdmin)
