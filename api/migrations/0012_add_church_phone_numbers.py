from django.db import migrations, models


def copy_phone_forward(apps, schema_editor):
    Church = apps.get_model('api', 'Church')
    for c in Church.objects.all():
        val = getattr(c, 'phone_number', None)
        if val:
            c.phone_number_1 = val
            c.save(update_fields=['phone_number_1'])


def copy_phone_backward(apps, schema_editor):
    Church = apps.get_model('api', 'Church')
    for c in Church.objects.all():
        val = getattr(c, 'phone_number_1', None)
        if val:
            c.phone_number = val
            c.save(update_fields=['phone_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_ticket_ticketreservation_tickettype_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='church',
            name='phone_number_1',
            field=models.CharField(max_length=20, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='church',
            name='phone_number_2',
            field=models.CharField(max_length=20, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='church',
            name='phone_number_3',
            field=models.CharField(max_length=20, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='church',
            name='phone_number_4',
            field=models.CharField(max_length=20, null=True, blank=True),
        ),
        migrations.RunPython(copy_phone_forward, copy_phone_backward),
        migrations.RemoveField(
            model_name='church',
            name='phone_number',
        ),
    ]
