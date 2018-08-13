from django.urls import path
from django.contrib.auth.decorators import login_required
from authentication.decorators import owner_required
from .views import CommentCreateView

urlpatterns = [
	path('comment/add/', login_required(CommentCreateView.as_view()), name='add_comment'),
	#path('comment/<int:pk>/delete/', login_required(PropertyListView.as_view()), name='delete_comment'),	
]