# Generated by Django 5.1.7 on 2025-06-30 23:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_crew_alter_agente_options_remove_agente_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='crewtask',
            name='output_file',
            field=models.CharField(blank=True, help_text='Caminho do arquivo para salvar o output da task automaticamente', max_length=255, null=True),
        ),
    ]
