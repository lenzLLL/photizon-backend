from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_add_church_phone_numbers'),
    ]

    operations = [
        migrations.AddField(
            model_name='deny',
            name='previous_church',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='previously_denied', to='api.church'),
        ),
    ]
