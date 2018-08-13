from .models import Category, Purpose

def search_bar(request):
	categories = Category.objects.all()	
	purposes = Purpose.objects.all()
	return {
		'categories': categories,
		'purposes': purposes,
	}