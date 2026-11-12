from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, ListView, DetailView
from django.contrib.auth.models import User
from .models import Conversation, Message
from .forms import MessageForm
from django.db.models import Q, Max

class ConversationListView(ListView):
    model = Conversation

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(Q(owner=self.request.user)|Q(member=self.request.user))\
            .exclude(messages__isnull=True).annotate(max_create_date=Max('messages__create_date')).order_by('-max_create_date')
        return queryset

class ConversationDetailView(DetailView):
    model = Conversation

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(Q(owner=user) | Q(member=user))

class MessageCreateView(CreateView):
    model = Message
    form_class = MessageForm
    success_url = reverse_lazy('conversations')

    def form_valid(self, form):
        receiver = get_object_or_404(User, pk=form.cleaned_data['receiver'])
        sender = self.request.user
        if receiver == sender:
            raise Http404
        conversation = Conversation.objects.filter(
            Q(owner=sender, member=receiver) | Q(owner=receiver, member=sender)
        ).first()
        if conversation is None:
            conversation = Conversation.objects.create(owner=sender, member=receiver)

        self.object = form.save(commit=False)
        self.object.sender = sender
        self.object.conversation = conversation
        self.object.save()
        
        # Evita redirecciones abiertas: sólo se aceptan URLs del propio sitio.
        next_url = form.cleaned_data['success_url']
        if not url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure()
        ):
            next_url = self.get_success_url()
        return redirect(next_url)

    def get(self, request, *args, **kwargs):
        raise Http404

