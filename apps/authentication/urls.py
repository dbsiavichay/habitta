from django.urls import path
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib.auth.views import LogoutView, PasswordChangeView, PasswordChangeDoneView
from .views import (
	UserCreationView, CompleteRegisterView, LoginView,
	ProfileUpdateView, ProfileUploadImageView, ProfileDetailView,
	SocialLoginView
)

urlpatterns = [
	path('register/', UserCreationView.as_view(), name='register'),
	path('user/<int:pk>/complete/', login_required(CompleteRegisterView.as_view()), name='complete_register'),
	path('login/', LoginView.as_view(), name='login'),
	path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
	path('profile/update/', login_required(ProfileUpdateView.as_view()), name='update_profile'),
	path('profile/avatar/upload/', login_required(ProfileUploadImageView.as_view()), name='upload_avatar_profile'),
	path('profile/<str:username>/', ProfileDetailView.as_view(), name='detail_profile'),
	path(
		'change-password/', PasswordChangeView.as_view(
			template_name = 'authentication/change_password.html',
			success_url = '/authentication/change-password-done/'
		), 		
		name='change_password'
	),
	path(
    	'change-password-done/', PasswordChangeDoneView.as_view(
    		template_name = 'authentication/change_password_done.html',
    	), 
    ),
	path('reset-password/', PasswordResetView.as_view(
		template_name='authentication/password_reset_form.html'
	), name='password_reset'),
	path('reset-password/done', PasswordResetDoneView.as_view(
		template_name='authentication/password_reset_done.html'
	), name='password_reset_done'),
	path('reset-password/confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(
		template_name='authentication/password_reset_confirm.html'
	), name='password_reset_confirm'),
	path('reset-password/complete/', PasswordResetCompleteView.as_view(
		template_name='authentication/password_reset_complete.html'
	),name='password_reset_complete'),

	path('social-login/', SocialLoginView.as_view(), name='social_login'),
]
