from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import LogCreateView, LogDeleteView

urlpatterns = [
	path('log/add/', login_required(LogCreateView.as_view()), name='add_log'),
	path('log/<int:pk>/delete/', login_required(LogDeleteView.as_view()), name='delete_log'),
]