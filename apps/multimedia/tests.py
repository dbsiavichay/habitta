"""Limpieza de imágenes: borrado en cascada con el anuncio y comando purge_orphan_images.

    docker compose exec web python manage.py test apps.multimedia.tests
"""
import os
import shutil
import tempfile
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image as PILImage

from apps.multimedia.models import Image
from apps.project.testing import create_listing, create_user
from apps.realty.models import Property

MEDIA_ROOT = tempfile.mkdtemp(prefix='habitta-multimedia-')


def tearDownModule():
    shutil.rmtree(MEDIA_ROOT, ignore_errors=True)


def pil(size=(40, 30)):
    return PILImage.new('RGB', size, (11, 110, 95))


@override_settings(MEDIA_ROOT=MEDIA_ROOT, TINIFY_API_KEY='')
class ImageCleanupTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user('ana')

    def setUp(self):
        self.listing = create_listing(self.owner)

    def test_deleting_a_listing_deletes_its_images_and_attachments(self):
        cover = self.listing.add_image(pil())
        thumbnail = self.listing.add_image(pil(), 'thumbnail')
        attachment = os.path.join(MEDIA_ROOT, 'files', '2026', 'planos.pdf')
        os.makedirs(os.path.dirname(attachment), exist_ok=True)
        with open(attachment, 'wb') as file:
            file.write(b'%PDF-1.4')
        self.listing.details['specifications']['99'] = attachment
        self.listing.save()
        paths = [cover.img.path, thumbnail.img.path]

        self.client.force_login(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('delete_property', args=[self.listing.pk]))

        self.assertFalse(Image.objects.filter(pk__in=[cover.pk, thumbnail.pk]).exists())
        for path in paths + [attachment]:
            self.assertFalse(os.path.exists(path), path)

    def test_attachments_outside_media_files_are_never_deleted(self):
        outside = tempfile.NamedTemporaryFile(delete=False)
        outside.close()
        self.listing.details['specifications']['99'] = outside.name
        self.listing.save()
        with self.captureOnCommitCallbacks(execute=True):
            self.listing.delete()
        self.assertTrue(os.path.exists(outside.name))
        os.remove(outside.name)

    def test_update_image_deletes_the_previous_file(self):
        first = self.listing.add_image(pil(), 'thumbnail')
        old_path = first.img.path
        with self.captureOnCommitCallbacks(execute=True):
            updated = self.listing.update_image(pil((20, 10)), 'thumbnail')
        self.assertEqual(updated.pk, first.pk)
        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(os.path.exists(updated.img.path))

    def test_file_shared_by_another_row_is_kept(self):
        image = self.listing.add_image(pil())
        Image.objects.create(img=image.img.name, object_id=self.listing.pk,
                             content_type=ContentType.objects.get_for_model(Property))
        with self.captureOnCommitCallbacks(execute=True):
            image.delete()
        self.assertTrue(os.path.exists(image.img.path))


@override_settings(MEDIA_ROOT=MEDIA_ROOT, TINIFY_API_KEY='')
class PurgeOrphanImagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user('ana')

    def setUp(self):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)  # sin archivos sueltos de otras pruebas
        self.listing = create_listing(self.owner)
        self.kept = self.listing.add_image(pil())
        gone = create_listing(self.owner, name='Lotes', title='Lote')
        self.orphan = gone.add_image(pil())
        # Borrado "a la antigua": la fila del anuncio desaparece y la imagen queda
        Property.objects.filter(pk=gone.pk)._raw_delete(Property.objects.db)
        self.loose = default_storage.save('images/suelta.png', ContentFile(b'png'))

    def run_command(self, *args):
        out = StringIO()
        with self.captureOnCommitCallbacks(execute=True):
            call_command('purge_orphan_images', *args, stdout=out)
        return out.getvalue()

    def test_dry_run_deletes_nothing(self):
        output = self.run_command('--dry-run', '--files')
        self.assertIn('Se borrarían 1 filas', output)
        self.assertIn('realty.property: 1', output)
        self.assertIn('Se borrarían 1 archivos de imágenes sin fila', output)
        self.assertTrue(Image.objects.filter(pk=self.orphan.pk).exists())
        self.assertTrue(os.path.exists(self.orphan.img.path))
        self.assertTrue(default_storage.exists(self.loose))

    def test_deletes_orphan_rows_and_files(self):
        self.run_command()
        self.assertFalse(Image.objects.filter(pk=self.orphan.pk).exists())
        self.assertFalse(os.path.exists(self.orphan.img.path))
        self.assertTrue(Image.objects.filter(pk=self.kept.pk).exists())
        self.assertTrue(os.path.exists(self.kept.img.path))
        self.assertTrue(default_storage.exists(self.loose))  # sin --files no se tocan

    def test_files_option_deletes_loose_files(self):
        self.run_command('--files')
        self.assertFalse(default_storage.exists(self.loose))
        self.assertTrue(os.path.exists(self.kept.img.path))
