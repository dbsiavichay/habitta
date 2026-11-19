from django.db import migrations, models
from django.db.models import F


def mark_existing_as_read(apps, schema_editor):
    # Los mensajes anteriores al contador no deben aparecer como nuevos
    Message = apps.get_model('messenger', 'Message')
    Message.objects.filter(read_at__isnull=True).update(read_at=F('create_date'))


class Migration(migrations.Migration):

    dependencies = [
        ('messenger', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='read_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='leído'),
        ),
        migrations.RunPython(mark_existing_as_read, migrations.RunPython.noop),
    ]
