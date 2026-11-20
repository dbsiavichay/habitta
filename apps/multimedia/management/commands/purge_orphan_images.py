"""Limpia las imágenes huérfanas que dejaron los borrados anteriores.

    python manage.py purge_orphan_images --dry-run          # sólo informa
    python manage.py purge_orphan_images                    # borra las filas de Image sin objeto (y sus archivos)
    python manage.py purge_orphan_images --files            # además, archivos de media/images/ sin fila

Desde la fase 4 los anuncios borran sus imágenes en cascada; esto es para lo que quedó de antes.
Los archivos borrados no se pueden recuperar: corre primero con --dry-run.
"""
import posixpath
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.multimedia.models import Image


def _size(storage, name):
    try:
        return storage.size(name) if storage.exists(name) else 0
    except OSError:
        return 0


def _human(size):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':
            return ('%d %s' % (size, unit)) if unit == 'B' else ('%.1f %s' % (size, unit))
        size /= 1024


class Command(BaseCommand):
    help = 'Borra las filas de Image cuyo objeto ya no existe y, con --files, los archivos de imágenes sin fila.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Sólo muestra qué se borraría.')
        parser.add_argument('--files', action='store_true', help='También borra archivos de media/images/ que ninguna fila usa.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.storage = Image._meta.get_field('img').storage
        if dry_run:
            self.stdout.write(self.style.NOTICE('Modo --dry-run: no se borra nada.'))

        rows = self.orphan_rows()
        by_model = Counter(label for _, label in rows)
        files = [image.img.name for image, _ in rows if image.img]
        size = sum(_size(self.storage, name) for name in files)
        verb = 'Se borrarían' if dry_run else 'Se borran'
        self.stdout.write('%s %d filas de Image huérfanas (%s en %d archivos).' % (
            verb, len(rows), _human(size), sum(1 for name in files if self.storage.exists(name))
        ))
        for label, count in sorted(by_model.items()):
            self.stdout.write('    %s: %d' % (label, count))
        if rows and not dry_run:
            with transaction.atomic():
                # La señal post_delete de Image borra cada archivo al confirmar
                Image.objects.filter(pk__in=[image.pk for image, _ in rows]).delete()

        if options['files']:
            loose = self.loose_files()
            size = sum(_size(self.storage, name) for name in loose)
            self.stdout.write('%s %d archivos de imágenes sin fila (%s).' % (verb, len(loose), _human(size)))
            if not dry_run:
                for name in loose:
                    self.storage.delete(name)

        self.stdout.write(self.style.SUCCESS('Listo.'))

    def orphan_rows(self):
        """[(image, 'app.modelo'), ...] de las imágenes cuyo objeto ya no existe."""
        orphans = []
        images = Image.objects.select_related('content_type').order_by('pk')
        groups = {}
        for image in images:
            groups.setdefault(image.content_type, []).append(image)
        for content_type, group in groups.items():
            model = content_type.model_class()
            label = '%s.%s' % (content_type.app_label, content_type.model)
            if model is None:
                orphans += [(image, label) for image in group]
                continue
            ids = {image.object_id for image in group}
            existing = set(model._base_manager.filter(pk__in=ids).values_list('pk', flat=True))
            orphans += [(image, label) for image in group if image.object_id not in existing]
        return orphans

    def loose_files(self):
        """Archivos dentro de la carpeta de Image.img que ninguna fila referencia.

        En --dry-run las filas huérfanas siguen en la BD, así que sus archivos no se cuentan dos veces.
        """
        folder = Image._meta.get_field('img').upload_to
        if not self.storage.exists(folder):
            return []
        referenced = set(Image.objects.exclude(img='').values_list('img', flat=True))
        loose = []
        pending = [folder]
        while pending:
            current = pending.pop()
            dirs, names = self.storage.listdir(current)
            pending += [posixpath.join(current, d) for d in dirs]
            loose += [posixpath.join(current, n) for n in names if posixpath.join(current, n) not in referenced]
        return sorted(loose)
