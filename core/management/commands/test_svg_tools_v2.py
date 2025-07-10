# core/management/commands/test_svg_tools_v2.py - VERSÃO CORRIGIDA

from django.core.management.base import BaseCommand
from core.services.crewai.tools.svg_function import svg_generator_tool
import json
import os

class Command(BaseCommand):
    help = 'Testa a SVGGeneratorTool corrigida'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='test_svg_corrigido.svg',
            help='Arquivo de saída para o SVG'
        )
        parser.add_argument(
            '--test-type',
            type=str,
            choices=['simples', 'complexo', 'corrupto'],
            default='complexo',
            help='Tipo de teste a executar'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        test_type = options['test_type']
        
        self.stdout.write(self.style.SUCCESS('🧪 TESTANDO SVGGeneratorTool CORRIGIDA'))
        self.stdout.write(f'📋 Tipo de teste: {test_type}')
        
        # Escolher dados de teste baseado no tipo
        if test_type == 'simples':
            dados_teste = self._dados_simples()
        elif test_type == 'complexo':
            dados_teste = self._dados_complexos()
        else:  # corrupto
            dados_teste = self._dados_corruptos()
        
        try:
            self.stdout.write('🛠️ Executando SVGGeneratorTool...')
            
            # Converter para JSON string
            dados_json = json.dumps(dados_teste, ensure_ascii=False, indent=2)
            self.stdout.write(f'📋 JSON preparado: {len(dados_json)} caracteres')
            
            # 🔍 MOSTRAR DADOS DE ENTRADA
            self.stdout.write('🔍 Dados de entrada:')
            self.stdout.write(dados_json[:500] + "..." if len(dados_json) > 500 else dados_json)
            
            # Executar a tool
            self.stdout.write('🎨 Gerando SVG...')
            resultado = svg_generator_tool._run(dados_json)
            
            # Verificar resultado
            if resultado and len(resultado) > 100:
                self.stdout.write(self.style.SUCCESS('✅ SVG gerado com sucesso!'))
                self.stdout.write(f'📊 Tamanho: {len(resultado)} caracteres')
                
                # Validações específicas
                self._validar_svg_gerado(resultado)
                
                # Salvar arquivo
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(resultado)
                    
                    self.stdout.write(f'💾 SVG salvo em: {output_file}')
                    
                    # Verificar arquivo criado
                    if os.path.exists(output_file):
                        tamanho_arquivo = os.path.getsize(output_file)
                        self.stdout.write(f'📁 Arquivo criado: {tamanho_arquivo} bytes')
                    
                except Exception as e:
                        self.stdout.write(self.style.ERROR(f'❌ Erro ao salvar arquivo: {e}'))
                
                # Mostrar preview
                self._mostrar_preview_svg(resultado)
                
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
            self.stdout.write('   3. Validar XML: xmllint --noout ' + output_file)

    def _dados_simples(self):
        """Dados de teste simples"""
        return {
            "nome_projeto": "Teste Simples",
            "empresa": "Empresa Teste",
            "area_total": 150.0,
            "tipo_stand": "ilha"
        }

    def _dados_complexos(self):
        """Dados de teste complexos - similares ao CrewAI"""
        return {
            "briefing_completo": {
                "projeto": {
                    "numero": "P2025-TEST",
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
                            "equipamentos": "Displays para produtos"
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
                            "equipamentos": "Geladeira, micro-ondas"
                        }
                    ]
                }
            }
        }

    def _dados_corruptos(self):
        """Dados de teste com problemas comuns"""
        return "{'nome': 'Teste \"Aspas Quebradas', 'area': None, 'caracteres_especiais': 'ção, ã, ñ, €'}"

    def _validar_svg_gerado(self, svg_content):
        """Valida o SVG gerado"""
        validacoes = []
        
        # Validação 1: Estrutura básica
        if svg_content.startswith('<?xml'):
            validacoes.append("✅ Declaração XML presente")
        else:
            validacoes.append("❌ Declaração XML ausente")
        
        # Validação 2: Tags SVG
        if '<svg' in svg_content and '</svg>' in svg_content:
            validacoes.append("✅ Tags SVG presentes")
        else:
            validacoes.append("❌ Tags SVG malformadas")
        
        # Validação 3: Aspas balanceadas
        aspas_duplas = svg_content.count('"')
        if aspas_duplas % 2 == 0:
            validacoes.append(f"✅ Aspas balanceadas ({aspas_duplas})")
        else:
            validacoes.append(f"❌ Aspas desbalanceadas ({aspas_duplas})")
        
        # Validação 4: Elementos obrigatórios
        elementos_obrigatorios = ['<rect', '<text']
        for elemento in elementos_obrigatorios:
            if elemento in svg_content:
                validacoes.append(f"✅ {elemento} presente")
            else:
                validacoes.append(f"❌ {elemento} ausente")
        
        # Validação 5: Caracteres problemáticos
        caracteres_problematicos = len([c for c in svg_content if ord(c) > 127])
        if caracteres_problematicos == 0:
            validacoes.append("✅ Sem caracteres não-ASCII")
        else:
            validacoes.append(f"⚠️ {caracteres_problematicos} caracteres não-ASCII")
        
        # Mostrar resultados
        self.stdout.write('\n🔍 VALIDAÇÕES DO SVG:')
        for validacao in validacoes:
            self.stdout.write(f'   {validacao}')

    def _mostrar_preview_svg(self, svg_content):
        """Mostra preview do SVG gerado"""
        linhas = svg_content.split('\n')
        
        self.stdout.write('\n👀 PREVIEW DO SVG:')
        self.stdout.write('   === INÍCIO ===')
        
        # Primeiras 10 linhas
        for i, linha in enumerate(linhas[:10]):
            self.stdout.write(f'   {i+1:2d}: {linha}')
        
        if len(linhas) > 10:
            self.stdout.write('   ...')
            # Últimas 3 linhas
            for i, linha in enumerate(linhas[-3:]):
                linha_num = len(linhas) - 3 + i + 1
                self.stdout.write(f'   {linha_num:2d}: {linha}')
        
        self.stdout.write('   === FIM ===')
        
        # Estatísticas
        self.stdout.write(f'\n📊 ESTATÍSTICAS:')
        self.stdout.write(f'   - Total de linhas: {len(linhas)}')
        self.stdout.write(f'   - Caracteres: {len(svg_content)}')
        self.stdout.write(f'   - Tags <rect>: {svg_content.count("<rect")}')
        self.stdout.write(f'   - Tags <text>: {svg_content.count("<text")}')
        self.stdout.write(f'   - Tags <svg>: {svg_content.count("<svg")}')