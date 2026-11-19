from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, ListView, DetailView
from django.contrib.auth.models import User
from .models import Conversation, Message
from .forms import MessageForm
from django.db.models import Count, OuterRef, Q, Subquery

def conversations_for(user):
    """Conversaciones con mensajes del usuario, la más reciente primero, con el último mensaje y
    cuántos no ha leído (todo en una consulta)."""
    last = Message.objects.filter(conversation=OuterRef('pk')).order_by('-create_date', '-pk')
    return (
        Conversation.objects.filter(Q(owner=user) | Q(member=user))
        .annotate(
            last_date=Subquery(last.values('create_date')[:1]),
            last_content=Subquery(last.values('content')[:1]),
            last_sender=Subquery(last.values('sender_id')[:1]),
            unread=Count('messages', filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=user)),
        )
        .filter(last_date__isnull=False)
        .select_related('owner__profile', 'member__profile')
        .order_by('-last_date', '-pk')
    )


class ConversationListView(ListView):
    model = Conversation
    paginate_by = 20

    def get_queryset(self):
        return conversations_for(self.request.user)


class ConversationDetailView(DetailView):
    model = Conversation

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(Q(owner=user) | Q(member=user)).select_related('owner__profile', 'member__profile')

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Se marca antes de renderizar para que los contadores ya salgan actualizados
        self.object.mark_read(request.user)
        return self.render_to_response(self.get_context_data(object=self.object))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'receiver': self.object.other(self.request.user),
            'chat_messages': self.object.messages.select_related('sender__profile').order_by('create_date', 'pk'),
            'conversations': conversations_for(self.request.user)[:40],
        })
        return context


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

