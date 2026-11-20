from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Image
from .utils import delete_image_file_on_commit


@receiver(post_delete, sender=Image)
def delete_image_file(sender, instance, **kwargs):
	"""Al borrar una Image (también en cascada, p. ej. con su anuncio) se borra su archivo."""
	if instance.img:
		delete_image_file_on_commit(instance.img.storage, instance.img.name)
