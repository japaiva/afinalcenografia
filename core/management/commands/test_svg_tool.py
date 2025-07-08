# core/management/commands/test_svg_tools.py

from django.core.management.base import BaseCommand
from core.services.crewai.tools.svg_generator import SVGGeneratorTool
from core.services.crewai.verbose.manager import VerboseManager
import json
import os

class Command(BaseCommand):
    help = 'Testa a SVGGeneratorTool isoladamente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='test_output.svg',
            help='Arquivo de saída para o SVG'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Ativar logs verbose'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        use_verbose = options['verbose']
        
        self.stdout.write(self.style.SUCCESS('🧪 TESTANDO SVGGeneratorTool'))
        
        # Inicializar verbose se solicitado
        verbose_manager = None
        if use_verbose:
            verbose_manager = VerboseManager("test_svg_tool", "Teste SVG")
            verbose_manager.start()
            self.stdout.write('📡 Verbose ativado')
        
        # Dados de teste simulando um briefing real
        dados_teste = {
            "briefing_completo": {
                "projeto": {
                    "numero": "P2025-001",
                    "nome": "Hair Summit 2025",
                    "empresa": "Beauty Fair",
                    "tipo": "feira_de_negocio",
                    "orcamento": 150000.0
                },
                "evento": {
                    "nome": "Hair Summit 2025",
                    "local": "Expo Center Norte",
                    "objetivo": "Apresentar produtos de beleza profissional"
                },
                "estande": {
                    "tipo_stand": "ponta_de_ilha",
                    "area_total": 220.0,
                    "medida_frente": 20.0,
                    "medida_fundo": 11.0,
                    "estilo": "moderno",
                    "material": "misto"
                },
                "divisoes_funcionais": {
                    "areas_exposicao": [
                        {
                            "tipo": "exposicao",
                            "metragem": 40.0,
                            "equipamentos": "Displays para produtos",
                            "elementos": {
                                "vitrine_exposicao": True,
                                "balcao_recepcao": True
                            }
                        }
                    ],
                    "salas_reuniao": [
                        {
                            "tipo": "sala_reuniao",
                            "capacidade": 8,
                            "metragem": 30.0,
                            "equipamentos": "Mesa de reunião, TV 55"
                        }
                    ],
                    "copas": [
                        {
                            "tipo": "copa",
                            "metragem": 21.0,
                            "equipamentos": "Geladeira, micro-ondas, pia"
                        }
                    ],
                    "depositos": [
                        {
                            "tipo": "deposito",
                            "metragem": 22.0,
                            "equipamentos": "Prateleiras, armários"
                        }
                    ]
                }
            }
        }
        
        try:
            # Criar instância da tool
            self.stdout.write('🛠️ Criando SVGGeneratorTool...')
            svg_tool = SVGGeneratorTool(verbose_manager=verbose_manager)
            
            # Testar a tool
            self.stdout.write('🎨 Gerando SVG...')
            resultado = svg_tool._run(
                dados=dados_teste,
                tipo="planta_baixa",
                config={
                    'width': 800,
                    'height': 600,
                    'background_color': '#f8f9fa'
                }
            )
            
            # Verificar resultado
            if resultado and len(resultado) > 100:
                self.stdout.write(self.style.SUCCESS('✅ SVG gerado com sucesso!'))
                self.stdout.write(f'📊 Tamanho: {len(resultado)} caracteres')
                
                # Salvar arquivo
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(resultado)
                
                self.stdout.write(f'💾 SVG salvo em: {output_file}')
                
                # Mostrar preview do início
                preview = resultado[:200] + "..." if len(resultado) > 200 else resultado
                self.stdout.write(f'👀 Preview:\n{preview}')
                
            else:
                self.stdout.write(self.style.ERROR('❌ SVG não gerado ou muito pequeno'))
                if resultado:
                    self.stdout.write(f'Resultado: {resultado}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            
        finally:
            if verbose_manager:
                verbose_manager.stop()
                
                # Mostrar logs
                logs = verbose_manager.get_logs()
                self.stdout.write(f'\n📋 Logs verbose ({len(logs)} entradas):')
                for log in logs:
                    timestamp = log.get('timestamp', 'N/A')
                    message = log.get('message', 'N/A')
                    self.stdout.write(f'   [{timestamp}] {message}')
        
        self.stdout.write('\n🎯 Teste da SVGGeneratorTool concluído!')