# Generated by Django 5.1.7 on 2025-06-24 20:42

import core.storage
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0019_empresa_razao_social_usuario_sexo'),
        ('projetos', '0025_alter_briefing_piso_elevado_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ConceitoVisualLegado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(blank=True, max_length=255, null=True)),
                ('descricao', models.TextField()),
                ('paleta_cores', models.TextField(blank=True, null=True)),
                ('materiais_principais', models.TextField(blank=True, null=True)),
                ('elementos_interativos', models.TextField(blank=True, null=True)),
                ('ia_gerado', models.BooleanField(default=False)),
                ('etapa_atual', models.PositiveSmallIntegerField(default=1)),
                ('status', models.CharField(default='em_elaboracao', max_length=20)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('agente_usado', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conceitos_legados_gerados', to='core.agente')),
                ('briefing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conceitos_visuais_legados', to='projetos.briefing')),
                ('projetista', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conceitos_legados_criados', to=settings.AUTH_USER_MODEL)),
                ('projeto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conceitos_visuais_legados', to='projetos.projeto')),
            ],
            options={
                'verbose_name': 'Conceito Visual (Legado)',
                'verbose_name_plural': 'Conceitos Visuais (Legados)',
                'db_table': 'projetista_conceitovisual',
            },
        ),
        migrations.CreateModel(
            name='ConceitoVisualNovo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imagem', models.ImageField(storage=core.storage.MinioStorage(), upload_to='conceitos_novos/', verbose_name='Imagem do Conceito')),
                ('descricao', models.CharField(max_length=255, verbose_name='Descrição do Conceito')),
                ('estilo_visualizacao', models.CharField(choices=[('fotorrealista', 'Fotorrealista'), ('artistico', 'Artístico'), ('tecnico', 'Técnico'), ('conceitual', 'Conceitual')], default='fotorrealista', max_length=50, verbose_name='Estilo de Visualização')),
                ('iluminacao', models.CharField(choices=[('diurna', 'Iluminação Diurna'), ('noturna', 'Iluminação Noturna'), ('feira', 'Iluminação de Feira'), ('dramatica', 'Iluminação Dramática')], default='feira', max_length=50, verbose_name='Tipo de Iluminação')),
                ('ia_gerado', models.BooleanField(default=True, verbose_name='Gerado por IA')),
                ('prompt_geracao', models.TextField(blank=True, null=True, verbose_name='Prompt de Geração')),
                ('instrucoes_adicionais', models.TextField(blank=True, null=True, verbose_name='Instruções Adicionais')),
                ('versao', models.PositiveSmallIntegerField(default=1, verbose_name='Versão')),
                ('status', models.CharField(choices=[('gerando', 'Gerando'), ('pronto', 'Pronto'), ('erro', 'Erro na Geração'), ('aprovado', 'Aprovado pelo Cliente')], default='gerando', max_length=20, verbose_name='Status')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('agente_usado', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conceitos_novos_gerados', to='core.agente', verbose_name='Agente Utilizado')),
                ('briefing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conceitos_visuais_novos', to='projetos.briefing')),
                ('conceito_anterior', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='versoes_posteriores', to='projetista.conceitovisualnovo', verbose_name='Versão Anterior')),
                ('projetista', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conceitos_novos_criados', to=settings.AUTH_USER_MODEL)),
                ('projeto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conceitos_visuais_novos', to='projetos.projeto')),
            ],
            options={
                'verbose_name': 'Conceito Visual Novo',
                'verbose_name_plural': 'Conceitos Visuais Novos',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='PlantaBaixa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('arquivo_svg', models.FileField(storage=core.storage.MinioStorage(), upload_to='plantas_baixas/svg/', verbose_name='Arquivo SVG da Planta')),
                ('arquivo_png', models.FileField(blank=True, null=True, storage=core.storage.MinioStorage(), upload_to='plantas_baixas/png/', verbose_name='Preview PNG')),
                ('dados_json', models.JSONField(help_text='Coordenadas, áreas, componentes da planta', verbose_name='Dados Estruturados')),
                ('algoritmo_usado', models.CharField(default='layout_generator_v1', max_length=100, verbose_name='Algoritmo Utilizado')),
                ('parametros_geracao', models.JSONField(blank=True, null=True, verbose_name='Parâmetros de Geração')),
                ('versao', models.PositiveSmallIntegerField(default=1, verbose_name='Versão')),
                ('status', models.CharField(choices=[('gerando', 'Gerando'), ('pronta', 'Pronta'), ('erro', 'Erro na Geração'), ('refinada_ia', 'Refinada por IA')], default='gerando', max_length=20, verbose_name='Status')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('briefing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plantas_baixas', to='projetos.briefing')),
                ('planta_anterior', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='versoes_posteriores', to='projetista.plantabaixa', verbose_name='Versão Anterior')),
                ('projetista', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='plantas_criadas', to=settings.AUTH_USER_MODEL)),
                ('projeto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plantas_baixas', to='projetos.projeto')),
            ],
            options={
                'verbose_name': 'Planta Baixa',
                'verbose_name_plural': 'Plantas Baixas',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='Modelo3D',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('arquivo_gltf', models.FileField(storage=core.storage.MinioStorage(), upload_to='modelos_3d/gltf/', verbose_name='Arquivo GLTF/GLB')),
                ('arquivo_obj', models.FileField(blank=True, null=True, storage=core.storage.MinioStorage(), upload_to='modelos_3d/obj/', verbose_name='Arquivo OBJ (opcional)')),
                ('arquivo_skp', models.FileField(blank=True, null=True, storage=core.storage.MinioStorage(), upload_to='modelos_3d/skp/', verbose_name='Arquivo SketchUp (opcional)')),
                ('imagem_preview', models.ImageField(blank=True, null=True, storage=core.storage.MinioStorage(), upload_to='modelos_3d/previews/', verbose_name='Imagem de Preview')),
                ('dados_cena', models.JSONField(help_text='Posições de câmera, iluminação, materiais, etc.', verbose_name='Dados da Cena 3D')),
                ('componentes_usados', models.JSONField(blank=True, help_text='Lista de componentes da biblioteca MinIO usados', null=True, verbose_name='Componentes Utilizados')),
                ('camera_inicial', models.JSONField(blank=True, null=True, verbose_name='Posição Inicial da Câmera')),
                ('pontos_interesse', models.JSONField(blank=True, help_text='Posições de câmera pré-definidas para navegação', null=True, verbose_name='Pontos de Interesse')),
                ('versao', models.PositiveSmallIntegerField(default=1, verbose_name='Versão')),
                ('status', models.CharField(choices=[('gerando', 'Gerando Modelo'), ('processando', 'Processando Componentes'), ('pronto', 'Pronto'), ('erro', 'Erro na Geração'), ('exportado', 'Exportado')], default='gerando', max_length=20, verbose_name='Status')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('briefing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modelos_3d', to='projetos.briefing')),
                ('conceito_visual', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modelos_3d', to='projetista.conceitovisualnovo', verbose_name='Conceito Visual Base')),
                ('modelo_anterior', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='versoes_posteriores', to='projetista.modelo3d', verbose_name='Versão Anterior')),
                ('projetista', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modelos_3d_criados', to=settings.AUTH_USER_MODEL)),
                ('projeto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modelos_3d', to='projetos.projeto')),
                ('planta_baixa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modelos_3d', to='projetista.plantabaixa', verbose_name='Planta Baixa Base')),
            ],
            options={
                'verbose_name': 'Modelo 3D',
                'verbose_name_plural': 'Modelos 3D',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.AddField(
            model_name='conceitovisualnovo',
            name='planta_baixa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conceitos_visuais', to='projetista.plantabaixa', verbose_name='Planta Baixa Base'),
        ),
    ]
