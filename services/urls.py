# from django.urls import path
# from django.contrib.auth.decorators import login_required
# from authentication.decorators import owner_required
# from .views import (
# 	ServiceListView, UserServiceListView, UserServiceCreateView, UserServiceUpdateView, UserServiceDeleteView,
# 	ServiceDetailView
# )

urlpatterns = [
	# path('', ServiceListView.as_view(), name='services'),	
	# path('services/', login_required(UserServiceListView.as_view()), name='user_services'),	
	# path('service/add/', login_required(UserServiceCreateView.as_view()), name='add_service'),	
	# path('service/<int:pk>/update/', owner_required(UserServiceUpdateView.as_view()), name='update_service'),	
	# path('service/<int:pk>/delete/', owner_required(UserServiceDeleteView.as_view()), name='delete_service'),	
	# path('service/<int:pk>/detail/', ServiceDetailView.as_view(), name='detail_service'),	
]