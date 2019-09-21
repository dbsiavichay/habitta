from realty.models import Category

Category.objects.filter(kind=Category.REAL_STATE).update(price_area='Precio')
Category.objects.filter(kind=Category.SERVICE).update(price_area='A negociar')