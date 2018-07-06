from django.urls import path
from .views import (
	UserCreationView, CompleteRegisterView, LoginView
)

urlpatterns = [
	path('register/', UserCreationView.as_view(), name='register'),
	path('user/<int:pk>/complete/', CompleteRegisterView.as_view(), name='complete_register'),
	path('login/', LoginView.as_view(), name='login'),
]