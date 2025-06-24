# core/services/planta_baixa_service.py

import json
import logging
from django.core.files.base import ContentFile
from django.conf import settings
from core.models import Agente
from projetista.models import PlantaBaixa
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw
import io

logger = logging.getLogger(__name__)


# =============================================================================
# MODELO 3D SERVICE
# =============================================================================

class Modelo3DService:
    """
    Serviço para geração de modelos 3D navegáveis
    """
    
    def __init__(self):
        self.biblioteca_componentes = self._carregar_biblioteca_componentes()
        
    def gerar_modelo_3d(self, briefing, planta_baixa, conceito_visual, **config):
        """
        Gera modelo 3D baseado na planta baixa e conceito visual
        """
        try:
            versao = config.get('versao', 1)
            modelo_anterior = config.get('modelo_anterior', None)
            
            # 1. Analisar planta baixa
            dados_layout = self._analisar_planta_baixa(planta_baixa)
            
            # 2. Extrair paleta de cores e materiais do conceito visual
            materiais_conceito = self._extrair_materiais_conceito(conceito_visual)
            
            # 3. Gerar cena 3D
            cena_3d = self._gerar_cena_3d(dados_layout, materiais_conceito)
            
            # 4. Posicionar componentes da biblioteca
            componentes_usados = self._posicionar_componentes(cena_3d, dados_layout)
            
            # 5. Configurar iluminação
            configuracao_luzes = self._configurar_iluminacao(conceito_visual.iluminacao)
            
            # 6. Gerar arquivos 3D
            arquivos_3d = self._gerar_arquivos_3d(cena_3d)
            
            # 7. Criar preview
            preview_imagem = self._gerar_preview_3d(cena_3d)
            
            # Importar modelo aqui para evitar imports circulares
            from projetista.models import Modelo3D
            
            # 8. Criar objeto Modelo3D
            modelo = Modelo3D(
                projeto=briefing.projeto,
                briefing=briefing,
                planta_baixa=planta_baixa,
                conceito_visual=conceito_visual,
                projetista=briefing.projeto.projetista,
                dados_cena={
                    'layout': dados_layout,
                    'materiais': materiais_conceito,
                    'componentes': componentes_usados,
                    'iluminacao': configuracao_luzes,
                    'estatisticas': self._calcular_estatisticas(cena_3d)
                },
                componentes_usados=componentes_usados,
                camera_inicial=self._definir_camera_inicial(dados_layout),
                pontos_interesse=self._definir_pontos_interesse(dados_layout),
                versao=versao,
                modelo_anterior=modelo_anterior,
                status='pronto'
            )
            
            # 9. Salvar arquivos
            self._salvar_arquivos_modelo(modelo, arquivos_3d, preview_imagem)
            modelo.save()
            
            return {
                'success': True,
                'modelo': modelo,
                'arquivos_gerados': list(arquivos_3d.keys()),
                'componentes_usados': len(componentes_usados)
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar modelo 3D: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _carregar_biblioteca_componentes(self):
        """
        Carrega biblioteca de componentes 3D do MinIO
        """
        # Estrutura básica da biblioteca de componentes
        return {
            'mobiliario': {
                'balcao_recepcao': {
                    'arquivo': 'componentes/balcao_recepcao.glb',
                    'dimensoes': {'largura': 2.0, 'profundidade': 0.6, 'altura': 1.1},
                    'categoria': 'atendimento'
                },
                'mesa_reuniao': {
                    'arquivo': 'componentes/mesa_reuniao.glb',
                    'dimensoes': {'largura': 2.4, 'profundidade': 1.2, 'altura': 0.75},
                    'categoria': 'reuniao'
                },
                'poltrona': {
                    'arquivo': 'componentes/poltrona.glb',
                    'dimensoes': {'largura': 0.8, 'profundidade': 0.8, 'altura': 1.2},
                    'categoria': 'lounge'
                },
                'vitrine': {
                    'arquivo': 'componentes/vitrine.glb',
                    'dimensoes': {'largura': 1.0, 'profundidade': 0.4, 'altura': 2.0},
                    'categoria': 'exposicao'
                }
            },
            'estruturais': {
                'painel_parede': {
                    'arquivo': 'componentes/painel_parede.glb',
                    'dimensoes': {'largura': 1.0, 'profundidade': 0.1, 'altura': 3.0},
                    'categoria': 'estrutura'
                },
                'piso_elevado': {
                    'arquivo': 'componentes/piso_elevado.glb',
                    'dimensoes': {'largura': 1.0, 'profundidade': 1.0, 'altura': 0.1},
                    'categoria': 'piso'
                }
            },
            'iluminacao': {
                'spot_led': {
                    'arquivo': 'componentes/spot_led.glb',
                    'dimensoes': {'largura': 0.2, 'profundidade': 0.2, 'altura': 0.3},
                    'categoria': 'iluminacao'
                }
            }
        }
    
    def _analisar_planta_baixa(self, planta_baixa):
        """
        Analisa dados da planta baixa para extração 3D
        """
        dados = planta_baixa.dados_json or {}
        
        return {
            'dimensoes_estande': dados.get('dimensoes_estande', {}),
            'ambientes': dados.get('ambientes', []),
            'paredes': dados.get('paredes', {}),
            'area_total': dados.get('area_total', 0),
            'escala': dados.get('escala', 20)
        }
    
    def _extrair_materiais_conceito(self, conceito_visual):
        """
        Extrai materiais e cores do conceito visual
        """
        # Esta seria uma análise mais sofisticada da imagem
        # Por enquanto, usar valores padrão baseados no estilo
        
        estilos_materiais = {
            'fotorrealista': {
                'piso': 'vinyl_wood',
                'paredes': 'drywall_white',
                'estrutura': 'aluminum_anodized'
            },
            'moderno': {
                'piso': 'concrete_polished',
                'paredes': 'glass_frosted',
                'estrutura': 'steel_brushed'
            },
            'tradicional': {
                'piso': 'carpet_gray',
                'paredes': 'wood_panel',
                'estrutura': 'wood_dark'
            }
        }
        
        estilo = conceito_visual.estilo_visualizacao
        return estilos_materiais.get(estilo, estilos_materiais['fotorrealista'])
    
    def _gerar_cena_3d(self, dados_layout, materiais):
        """
        Gera estrutura básica da cena 3D
        """
        dimensoes = dados_layout['dimensoes_estande']
        
        cena = {
            'geometrias': [],
            'materiais': materiais,
            'objetos': [],
            'luzes': [],
            'cameras': []
        }
        
        # Gerar geometria base do estande
        # Piso
        cena['geometrias'].append({
            'tipo': 'plane',
            'id': 'piso_principal',
            'dimensoes': {
                'width': dimensoes.get('frente', 6),
                'height': dimensoes.get('fundo', 4)
            },
            'posicao': {'x': 0, 'y': 0, 'z': 0},
            'material': materiais['piso']
        })
        
        # Paredes
        altura_parede = 3.0
        
        # Parede frontal
        cena['geometrias'].append({
            'tipo': 'plane',
            'id': 'parede_frontal',
            'dimensoes': {
                'width': dimensoes.get('frente', 6),
                'height': altura_parede
            },
            'posicao': {'x': 0, 'y': altura_parede/2, 'z': -dimensoes.get('fundo', 4)/2},
            'rotacao': {'x': 0, 'y': 0, 'z': 0},
            'material': materiais['paredes']
        })
        
        # Paredes laterais...
        # (Adicionar outras paredes)
        
        return cena
    
    def _posicionar_componentes(self, cena_3d, dados_layout):
        """
        Posiciona componentes da biblioteca na cena
        """
        componentes_usados = []
        
        for ambiente in dados_layout['ambientes']:
            tipo_ambiente = ambiente['tipo']
            posicao = ambiente['posicao']
            dimensoes = ambiente['dimensoes']
            
            # Selecionar componentes baseado no tipo de ambiente
            if tipo_ambiente == 'exposicao':
                # Adicionar balcão de recepção
                if any(comp['tipo'] == 'balcao_recepcao' for comp in ambiente.get('componentes', [])):
                    componente = {
                        'tipo': 'balcao_recepcao',
                        'posicao': {
                            'x': posicao['x'] + dimensoes['largura'] * 0.1,
                            'y': 0,
                            'z': posicao['y']
                        },
                        'arquivo_origem': self.biblioteca_componentes['mobiliario']['balcao_recepcao']['arquivo'],
                        'dimensoes': self.biblioteca_componentes['mobiliario']['balcao_recepcao']['dimensoes']
                    }
                    componentes_usados.append(componente)
            
            elif tipo_ambiente == 'reuniao':
                # Adicionar mesa de reunião
                componente = {
                    'tipo': 'mesa_reuniao',
                    'posicao': {
                        'x': posicao['x'] + dimensoes['largura'] / 2,
                        'y': 0,
                        'z': posicao['y'] + dimensoes['altura'] / 2
                    },
                    'arquivo_origem': self.biblioteca_componentes['mobiliario']['mesa_reuniao']['arquivo'],
                    'dimensoes': self.biblioteca_componentes['mobiliario']['mesa_reuniao']['dimensoes']
                }
                componentes_usados.append(componente)
        
        return componentes_usados
    
    def _configurar_iluminacao(self, tipo_iluminacao):
        """
        Configura iluminação baseada no tipo
        """
        configuracoes = {
            'diurna': {
                'ambiente': {'intensidade': 0.4, 'cor': '#ffffff'},
                'direcional': {'intensidade': 0.8, 'cor': '#ffffcc', 'posicao': [5, 10, 5]}
            },
            'noturna': {
                'ambiente': {'intensidade': 0.2, 'cor': '#4444ff'},
                'spots': [
                    {'intensidade': 1.0, 'cor': '#ffffff', 'posicao': [2, 3, 2]},
                    {'intensidade': 1.0, 'cor': '#ffffff', 'posicao': [-2, 3, 2]}
                ]
            },
            'feira': {
                'ambiente': {'intensidade': 0.6, 'cor': '#ffffff'},
                'spots': [
                    {'intensidade': 1.2, 'cor': '#ffffff', 'posicao': [1, 4, 1]},
                    {'intensidade': 1.2, 'cor': '#ffffff', 'posicao': [-1, 4, 1]},
                    {'intensidade': 0.8, 'cor': '#ffeeaa', 'posicao': [0, 3, -2]}
                ]
            }
        }
        
        return configuracoes.get(tipo_iluminacao, configuracoes['feira'])
    
    def _gerar_arquivos_3d(self, cena_3d):
        """
        Gera arquivos 3D em diferentes formatos
        """
        # Esta seria a lógica real de exportação 3D
        # Por enquanto, simular a geração de arquivos
        
        arquivos = {
            'gltf': b'',  # Dados do arquivo GLTF
            'obj': b'',   # Dados do arquivo OBJ
            'skp': b''    # Dados do arquivo SketchUp (se disponível)
        }
        
        # TODO: Implementar geração real dos arquivos usando bibliotecas como
        # - pygltflib para GLTF
        # - Blender Python API para múltiplos formatos
        # - FBX SDK para FBX
        
        return arquivos
    
    def _gerar_preview_3d(self, cena_3d):
        """
        Gera imagem de preview do modelo 3D
        """
        # Por enquanto, retornar uma imagem placeholder
        # TODO: Implementar renderização real usando Blender ou Three.js headless
        
        # Criar imagem placeholder
        img = Image.new('RGB', (800, 600), 'lightgray')
        draw = ImageDraw.Draw(img)
        draw.text((400, 300), "Preview 3D", anchor="mm", fill='black')
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _calcular_estatisticas(self, cena_3d):
        """
        Calcula estatísticas do modelo 3D
        """
        return {
            'total_vertices': len(cena_3d.get('geometrias', [])) * 1000,  # Estimativa
            'total_faces': len(cena_3d.get('geometrias', [])) * 500,
            'total_materiais': len(cena_3d.get('materiais', {})),
            'total_luzes': len(cena_3d.get('luzes', [])),
            'tamanho_arquivo_mb': 2.5  # Estimativa
        }
    
    def _definir_camera_inicial(self, dados_layout):
        """
        Define posição inicial da câmera
        """
        dimensoes = dados_layout['dimensoes_estande']
        
        return {
            'posicao': {
                'x': dimensoes.get('frente', 6) * 0.7,
                'y': 2.5,
                'z': dimensoes.get('fundo', 4) * 0.7
            },
            'target': {
                'x': 0,
                'y': 1,
                'z': 0
            },
            'fov': 60
        }
    
    def _definir_pontos_interesse(self, dados_layout):
        """
        Define pontos de interesse para navegação
        """
        pontos = []
        
        # Ponto de entrada
        pontos.append({
            'nome': 'Entrada Principal',
            'camera': {
                'posicao': {'x': 0, 'y': 1.7, 'z': dados_layout['dimensoes_estande'].get('fundo', 4) * 0.8},
                'target': {'x': 0, 'y': 1.5, 'z': 0}
            }
        })
        
        # Pontos para cada ambiente
        for ambiente in dados_layout['ambientes']:
            pos = ambiente['posicao']
            dim = ambiente['dimensoes']
            
            pontos.append({
                'nome': ambiente['nome'],
                'camera': {
                    'posicao': {
                        'x': pos['x'] + dim['largura'] / 2,
                        'y': 1.7,
                        'z': pos['y'] + dim['altura'] / 2
                    },
                    'target': {
                        'x': pos['x'] + dim['largura'] / 2,
                        'y': 1.0,
                        'z': pos['y']
                    }
                }
            })
        
        return pontos
    
    def _salvar_arquivos_modelo(self, modelo, arquivos_3d, preview_imagem):
        """
        Salva arquivos do modelo 3D
        """
        from django.core.files.base import ContentFile
        
        # Salvar arquivo GLTF principal
        if arquivos_3d.get('gltf'):
            filename_gltf = f"modelo_{modelo.projeto.id}_v{modelo.versao}.glb"
            modelo.arquivo_gltf.save(filename_gltf, ContentFile(arquivos_3d['gltf']), save=False)
        
        # Salvar arquivo OBJ (opcional)
        if arquivos_3d.get('obj'):
            filename_obj = f"modelo_{modelo.projeto.id}_v{modelo.versao}.obj"
            modelo.arquivo_obj.save(filename_obj, ContentFile(arquivos_3d['obj']), save=False)
        
        # Salvar arquivo SketchUp (opcional)
        if arquivos_3d.get('skp'):
            filename_skp = f"modelo_{modelo.projeto.id}_v{modelo.versao}.skp"
            modelo.arquivo_skp.save(filename_skp, ContentFile(arquivos_3d['skp']), save=False)
        
        # Salvar preview
        if preview_imagem:
            filename_preview = f"preview_{modelo.projeto.id}_v{modelo.versao}.png"
            modelo.imagem_preview.save(filename_preview, ContentFile(preview_imagem), save=False)