from django.urls import path
from .views import HomeView, TermListView

urlpatterns = [
	path('', HomeView.as_view(), name='home'),
	path('terms/', TermListView.as_view(), name='terms'),	
]