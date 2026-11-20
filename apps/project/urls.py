from django.urls import path
from .views import HomeView, TermListView, HelpListView, healthz

urlpatterns = [
	path('', HomeView.as_view(), name='home'),
	path('terms/', TermListView.as_view(), name='terms'),	
	path('help/', HelpListView.as_view(), name='help'),	
	# Sin barra final: es lo que piden el HEALTHCHECK de la imagen y el deploy.
	path('healthz', healthz, name='healthz'),
]
