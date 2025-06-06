# Generated by Django 5.1.7 on 2025-04-20 18:32

import core.storage
import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_mensagem_anexomensagem_notificacao'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='mensagem',
            options={'ordering': ['-data_envio'], 'verbose_name': 'Mensagem', 'verbose_name_plural': 'Mensagens'},
        ),
        migrations.RemoveField(
            model_name='anexomensagem',
            name='nome',
        ),
        migrations.RemoveField(
            model_name='anexomensagem',
            name='tipo',
        ),
        migrations.RemoveField(
            model_name='mensagem',
            name='arquivada',
        ),
        migrations.RemoveField(
            model_name='mensagem',
            name='data',
        ),
        migrations.RemoveField(
            model_name='mensagem',
            name='data_leitura',
        ),
        migrations.RemoveField(
            model_name='mensagem',
            name='importante',
        ),
        migrations.RemoveField(
            model_name='mensagem',
            name='is_cliente',
        ),
        migrations.RemoveField(
            model_name='mensagem',
            name='tem_anexo',
        ),
        migrations.AddField(
            model_name='anexomensagem',
            name='nome_original',
            field=models.CharField(default='arquivo.txt', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='anexomensagem',
            name='tipo_arquivo',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='mensagem',
            name='data_envio',
            field=models.DateTimeField(auto_now_add=True, default=datetime.datetime(2025, 4, 20, 18, 32, 6, 89579, tzinfo=datetime.timezone.utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='mensagem',
            name='destacada',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mensagem',
            name='destinatario',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mensagens_recebidas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='anexomensagem',
            name='arquivo',
            field=models.FileField(storage=core.storage.MinioStorage(), upload_to='mensagens/anexos/'),
        ),
        migrations.AlterField(
            model_name='anexomensagem',
            name='tamanho',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='mensagem',
            name='conteudo',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='mensagem',
            name='lida',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterModelTable(
            name='anexomensagem',
            table=None,
        ),
        migrations.AlterModelTable(
            name='mensagem',
            table=None,
        ),
        migrations.DeleteModel(
            name='Notificacao',
        ),
    ]
