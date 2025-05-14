# projetos/migrations/0018_auto_20250513_1626.py

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('projetos', '0017_briefing_pdf_file_briefing_pdf_generated_at_and_more'),
    ]

    operations = [
        # Adicione estas operações (ou use SeparateDatabaseAndState se as tabelas não existirem)
        migrations.DeleteModel(
            name='ProjetoPlanta',
        ),
        migrations.DeleteModel(
            name='ProjetoReferencia',
        ),
        
        # Se houver outras operações já definidas, deixe-as aqui também
    ]
