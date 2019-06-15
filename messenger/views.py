from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, DetailView
from django.contrib.auth.models import User
from .models import Conversation, Message
from .forms import MessageForm
from django.db.models import Q

class ConversationListView(ListView):
	model = Conversation

	def get_queryset(self):
		queryset = super().get_queryset()
		queryset = queryset.filter(Q(owner=self.request.user)|Q(member=self.request.user))
		return queryset

class ConversationDetailView(DetailView):
	model = Conversation

class MessageCreateView(CreateView):
	model = Message
	form_class = MessageForm
	success_url = reverse_lazy('conversations')

	def form_valid(self, form):
		receiver = get_object_or_404(User, pk=form.cleaned_data['receiver'])
		sender = self.request.user
		try:
			conversation = Conversation.objects.get(Q(owner=sender, member=receiver)|Q(owner=receiver, member=sender))
		except:
			conversation = Conversation.objects.create(owner=sender, member=receiver)

		self.object = form.save(commit=False)
		self.object.sender = sender
		self.object.conversation = conversation
		self.object.save()
		
		return redirect(form.cleaned_data['success_url'])

	def form_invalid(self, form):
		print(form.errors)

	def get(self, request, *args, **kwargs):
		raise Http404

