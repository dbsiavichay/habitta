from django.db import models
from django.db.models import Q
from django.utils import timezone


class Conversation(models.Model):
    owner = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='outbox')
    member = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='inbox')
    create_date = models.DateTimeField(auto_now_add=True)

    def last_message(self):
        return self.messages.order_by('create_date', 'pk').last()

    def other(self, user):
        """El otro participante de la conversación."""
        return self.member if user.pk == self.owner_id else self.owner

    def mark_read(self, reader):
        """Marca como leídos los mensajes que `reader` recibió en esta conversación."""
        return self.messages.filter(read_at__isnull=True).exclude(sender=reader).update(read_at=timezone.now())

    class Meta:
        unique_together = ('owner', 'member')
        verbose_name = 'conversación'
        verbose_name_plural = 'conversaciones'

    def __str__(self):
        return f'{self.owner.get_full_name() or self.owner} y {self.member.get_full_name() or self.member}'


class MessageQuerySet(models.QuerySet):
    def unread_for(self, user):
        """Mensajes que `user` recibió y todavía no abrió."""
        return self.filter(
            Q(conversation__owner=user) | Q(conversation__member=user), read_at__isnull=True,
        ).exclude(sender=user)


class Message(models.Model):
    sender = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    content = models.TextField()
    create_date = models.DateTimeField(auto_now_add=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT, related_name='messages')
    read_at = models.DateTimeField('leído', null=True, blank=True)

    objects = MessageQuerySet.as_manager()

    class Meta:
        verbose_name = 'mensaje'
        verbose_name_plural = 'mensajes'
