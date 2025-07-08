# core/management/commands/test_svg_tools.py - VERSÃO CORRIGIDA

from django.core.management.base import BaseCommand
from core.services.crewai.tools.svg_function import svg_generator_tool
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

    def handle(self, *args, **options):
        output_file = options['output']
        
        self.stdout.write(self.style.SUCCESS('🧪 TESTANDO SVGGeneratorTool'))
        
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
            self.stdout.write('🛠️ Usando SVGGeneratorTool...')
            
            # ✅ CORREÇÃO: Converter para JSON string
            dados_json = json.dumps(dados_teste)
            self.stdout.write(f'📋 JSON preparado: {len(dados_json)} caracteres')
            
            # ✅ CORREÇÃO: Chamar com parâmetro correto
            self.stdout.write('🎨 Gerando SVG...')
            resultado = svg_generator_tool._run(dados_json)
            
            # Verificar resultado
            if resultado and len(resultado) > 100:
                self.stdout.write(self.style.SUCCESS('✅ SVG gerado com sucesso!'))
                self.stdout.write(f'📊 Tamanho: {len(resultado)} caracteres')
                
                # Verificar se é SVG válido
                if '<?xml' in resultado and '<svg' in resultado:
                    self.stdout.write('✅ SVG válido detectado')
                else:
                    self.stdout.write('⚠️ Resultado não parece ser SVG válido')
                
                # Salvar arquivo
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(resultado)
                    
                    self.stdout.write(f'💾 SVG salvo em: {output_file}')
                    
                    # Verificar se arquivo foi criado
                    if os.path.exists(output_file):
                        tamanho_arquivo = os.path.getsize(output_file)
                        self.stdout.write(f'📁 Arquivo criado: {tamanho_arquivo} bytes')
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Erro ao salvar arquivo: {e}'))
                
                # Mostrar preview do início
                preview = resultado[:300] + "..." if len(resultado) > 300 else resultado
                self.stdout.write(f'👀 Preview:\n{preview}')
                
                # Mostrar algumas linhas do meio
                if len(resultado) > 600:
                    meio = len(resultado) // 2
                    preview_meio = resultado[meio:meio+200] + "..."
                    self.stdout.write(f'🔍 Meio do SVG:\n{preview_meio}')
                
            else:
                self.stdout.write(self.style.ERROR('❌ SVG não gerado ou muito pequeno'))
                if resultado:
                    self.stdout.write(f'Resultado recebido: {resultado[:500]}')
                else:
                    self.stdout.write('Nenhum resultado retornado')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro durante execução: {str(e)}'))
            import traceback
            self.stdout.write('🔍 Traceback completo:')
            self.stdout.write(traceback.format_exc())
        
        self.stdout.write('\n🎯 Teste da SVGGeneratorTool concluído!')
        
        # Instruções finais
        if os.path.exists(output_file):
            self.stdout.write('\n📋 Para visualizar o SVG:')
            self.stdout.write(f'   1. Abrir arquivo: {os.path.abspath(output_file)}')
            self.stdout.write('   2. Usar navegador ou editor que suporte SVG')
            self.stdout.write('   3. Ou copiar conteúdo para ferramenta online de SVG')