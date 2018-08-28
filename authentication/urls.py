from django.urls import path
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import logout_then_login, password_change, password_change_done
from .views import (
	UserCreationView, CompleteRegisterView, LoginView,
	ProfileUpdateView, ProfileUploadImageView, ProfileDetailView,
	SocialLoginView
)

urlpatterns = [
	path('register/', UserCreationView.as_view(), name='register'),
	path('user/<int:pk>/complete/', login_required(CompleteRegisterView.as_view()), name='complete_register'),
	path('login/', LoginView.as_view(), name='login'),
	path('logout/', login_required(logout_then_login), name='logout'),
	path('profile/update/', login_required(ProfileUpdateView.as_view()), name='update_profile'),
	path('profile/avatar/upload/', login_required(ProfileUploadImageView.as_view()), name='upload_avatar_profile'),
	path('profile/<slug:username>/', ProfileDetailView.as_view(), name='detail_profile'),
	
	path(
		'change-password/', password_change, 
		{
			'template_name': 'authentication/change_password.html',
			'post_change_redirect': '/authentication/change-password-done/'
		},
		name='change_password'
	),
	path(
    	'change-password-done/', password_change_done, 
    	{
    		'template_name': 'authentication/change_password_done.html',
    	}
    ),

	
	path('social-login/', SocialLoginView.as_view(), name='social_login'),
]
