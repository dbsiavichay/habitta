from django.urls import path
from django.contrib.auth.decorators import login_required
from authentication.decorators import owner_required
from .views import ConversationListView, ConversationDetailView, MessageCreateView

urlpatterns = [
	path('conversations/', login_required(ConversationListView.as_view()), name='conversations'),	
	path('conversation/<int:pk>/detail/', login_required(ConversationDetailView.as_view()), name='detail_conversation'),
	path('message/add/', login_required(MessageCreateView.as_view()), name='add_message'),	
]