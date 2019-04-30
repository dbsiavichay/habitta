from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import (	
	Base64ImageUploadView, ImageDeleteView,
)

urlpatterns = [	
	path('base64image/add/', login_required(Base64ImageUploadView.as_view()), name='add_base64image'),
	path('image/<int:pk>/delete/', login_required(ImageDeleteView.as_view()), name='delete_image'),		
]