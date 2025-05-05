# core/management/commands/init_campo_perguntas.py

from django.core.management.base import BaseCommand
from scripts.init_campo_perguntas import criar_campo_perguntas

class Command(BaseCommand):
    help = 'Inicializa as perguntas padrão para campos do cadastro de feira'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando criação de perguntas para campos...'))
        criar_campo_perguntas()
        self.stdout.write(self.style.SUCCESS('Perguntas para campos criadas com sucesso!'))