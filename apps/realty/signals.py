from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Property
from .utils import attachment_paths, delete_attachments_on_commit


@receiver(post_delete, sender=Property)
def delete_property_attachments(sender, instance, **kwargs):
    """Al borrar un anuncio se borran sus adjuntos (las imágenes las borra su GenericRelation)."""
    delete_attachments_on_commit(attachment_paths(instance.details))
