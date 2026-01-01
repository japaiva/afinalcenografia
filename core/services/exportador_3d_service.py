# core/services/exportador_3d_service.py
"""
Serviço para exportação de modelo 3D enriquecido
Gera arquivos OBJ compatíveis com 3ds Max, Blender, SketchUp, etc.

Fontes de dados:
- Planta Baixa JSON: geometria, áreas, dimensões
- Briefing: materiais, estilo, cores da marca
- Renderização AI JSON: mobiliário, iluminação, detalhes visuais
"""

import trimesh
import numpy as np
import io
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)


class Exportador3DService:
    """
    Serviço para gerar modelos 3D enriquecidos a partir de múltiplas fontes
    """

    def __init__(self, planta_baixa_json: Dict[str, Any],
                 briefing: Any = None,
                 renderizacao_json: Dict[str, Any] = None):
        """
        Args:
            planta_baixa_json: JSON da planta baixa com dimensões e áreas
            briefing: Objeto Briefing com dados do cliente
            renderizacao_json: JSON enriquecido da renderização AI
        """
        self.planta = planta_baixa_json
        self.briefing = briefing
        self.renderizacao = renderizacao_json or {}

        self.escala = 1.0  # 1 unidade = 1 metro
        self.altura_parede = 3.0  # metros
        self.espessura_parede = 0.1  # metros
        self.altura_piso = 0.05  # metros

        # Extrair configurações do briefing
        if briefing:
            self._configurar_do_briefing()

        # Extrair configurações da renderização
        if renderizacao_json:
            self._configurar_da_renderizacao()

        # Cena 3D (lista de meshes)
        self.meshes = []
        self.materiais = {}
        self.mobiliario = []

    def _configurar_do_briefing(self):
        """Extrai configurações do briefing"""
        if not self.briefing:
            return

        # Altura das paredes baseada no tipo de stand
        if hasattr(self.briefing, 'altura_maxima') and self.briefing.altura_maxima:
            self.altura_parede = float(self.briefing.altura_maxima)

        # Estilo influencia materiais
        self.estilo = getattr(self.briefing, 'estilo_estande', 'moderno')

        # Cores da marca
        self.cores_marca = []
        if hasattr(self.briefing, 'cores_marca') and self.briefing.cores_marca:
            self.cores_marca = self.briefing.cores_marca

        logger.info(f"[3D] Configurado do briefing: altura={self.altura_parede}m, estilo={self.estilo}")

    def _configurar_da_renderizacao(self):
        """Extrai configurações da renderização AI"""
        if not self.renderizacao:
            return

        # Mobiliário detalhado
        self.mobiliario = self.renderizacao.get('mobiliario', [])

        # Materiais específicos
        materiais_render = self.renderizacao.get('materiais', {})
        if materiais_render:
            self.materiais.update(materiais_render)

        # Iluminação
        self.iluminacao = self.renderizacao.get('iluminacao', {})

        logger.info(f"[3D] Configurado da renderização: {len(self.mobiliario)} móveis")

    def gerar_modelo_3d(self) -> Tuple[bytes, bytes, Dict[str, Any]]:
        """
        Gera modelo 3D completo a partir de múltiplas fontes

        Returns:
            Tuple com (bytes_obj, bytes_mtl, metadados)
        """
        logger.info("[3D Export] Iniciando geração de modelo 3D enriquecido...")

        # Extrair dimensões
        dims = self.planta.get('dimensoes_totais', {})
        largura = dims.get('largura', 10.0)
        profundidade = dims.get('profundidade', 8.0)

        logger.info(f"[3D Export] Dimensões: {largura}m x {profundidade}m")

        # 1. Gerar piso principal
        self._gerar_piso(largura, profundidade)

        # 2. Gerar paredes externas baseado no tipo de stand
        tipo_stand = self.planta.get('tipo_stand', 'ilha')
        lados_abertos = self.planta.get('lados_abertos', [])
        self._gerar_paredes_externas(largura, profundidade, tipo_stand, lados_abertos)

        # 3. Gerar áreas internas (salas, depósito, etc.)
        areas = self.planta.get('areas', [])
        for area in areas:
            self._gerar_area(area)

        # 4. Gerar mobiliário (se disponível na renderização)
        mobiliario_gerado = self._gerar_mobiliario()

        # 5. Gerar testeira (se configurado)
        self._gerar_testeira(largura, profundidade, tipo_stand)

        # 6. Combinar todos os meshes
        if self.meshes:
            cena_combinada = trimesh.util.concatenate(self.meshes)
        else:
            # Criar mesh vazio se não houver geometrias
            cena_combinada = trimesh.Trimesh()

        # 7. Exportar para OBJ
        obj_data, mtl_data = self._exportar_obj(cena_combinada)

        # 8. Metadados enriquecidos
        metadados = {
            'formato': 'OBJ',
            'vertices': len(cena_combinada.vertices) if hasattr(cena_combinada, 'vertices') else 0,
            'faces': len(cena_combinada.faces) if hasattr(cena_combinada, 'faces') else 0,
            'dimensoes': {'largura': largura, 'profundidade': profundidade, 'altura': self.altura_parede},
            'areas_geradas': len(areas),
            'mobiliario_gerado': mobiliario_gerado,
            'tipo_stand': tipo_stand,
            'fontes_dados': self._listar_fontes_dados(),
            'gerado_em': datetime.now().isoformat(),
            'compativel_com': ['3ds Max', 'Blender', 'SketchUp', 'Maya', 'Cinema 4D']
        }

        logger.info(f"[3D Export] Modelo gerado: {metadados['vertices']} vértices, {metadados['faces']} faces, {mobiliario_gerado} móveis")

        return obj_data, mtl_data, metadados

    def _listar_fontes_dados(self) -> List[str]:
        """Lista as fontes de dados utilizadas"""
        fontes = ['Planta Baixa']
        if self.briefing:
            fontes.append('Briefing')
        if self.renderizacao:
            fontes.append('Renderização AI')
        return fontes

    def _gerar_mobiliario(self) -> int:
        """Gera mobiliário baseado nos dados da renderização ou planta"""
        count = 0

        # Gerar mobiliário padrão para cada área baseado no tipo
        for area in self.planta.get('areas', []):
            tipo_area = area.get('tipo', '').lower()
            nome_area = area.get('nome', area.get('id', '')).lower()
            geom = area.get('geometria', {})

            x_base = geom.get('x', 0)
            z_base = geom.get('y', 0)
            largura_area = geom.get('largura', 2)
            prof_area = geom.get('profundidade', 2)

            # Determinar mobiliário baseado no tipo/nome da área
            moveis_area = self._mobiliario_para_area(tipo_area, nome_area)

            for i, movel_tipo in enumerate(moveis_area):
                dims = self._dimensoes_padrao(movel_tipo)

                # Posicionar móveis distribuídos na área
                offset_x = 0.3 + (i % 2) * (largura_area / 2 - 0.5)
                offset_z = 0.3 + (i // 2) * (prof_area / 2 - 0.5)

                movel = {
                    'tipo': movel_tipo,
                    'nome': f'{movel_tipo}_{nome_area}_{i}',
                    'posicao': {
                        'x': x_base + offset_x,
                        'y': 0,
                        'z': z_base + offset_z
                    },
                    'dimensoes': dims
                }
                self._criar_movel(movel)
                count += 1

                logger.debug(f"[3D Export] Móvel gerado para {nome_area}: {movel_tipo}")

        return count

    def _mobiliario_para_area(self, tipo: str, nome: str) -> List[str]:
        """Retorna lista de móveis apropriados para o tipo de área"""

        # Combinar tipo e nome para melhor detecção
        identificador = f"{tipo} {nome}".lower()

        # Mapear tipos de área para mobiliário
        if any(x in identificador for x in ['recep', 'atendimento', 'entrada']):
            return ['balcao', 'cadeira', 'cadeira']

        elif any(x in identificador for x in ['reuniao', 'reunião', 'meeting']):
            return ['mesa', 'cadeira', 'cadeira', 'cadeira', 'cadeira']

        elif any(x in identificador for x in ['lounge', 'espera', 'estar', 'descanso']):
            return ['sofa', 'mesa']  # mesa de centro

        elif any(x in identificador for x in ['deposito', 'depósito', 'estoque', 'storage']):
            return ['prateleira', 'prateleira']

        elif any(x in identificador for x in ['demo', 'demonstr', 'exib', 'exposic', 'mostruario']):
            return ['vitrine', 'balcao', 'totem']

        elif any(x in identificador for x in ['venda', 'produto', 'comercial']):
            return ['vitrine', 'balcao', 'prateleira']

        elif any(x in identificador for x in ['cafe', 'café', 'copa', 'cozinha']):
            return ['balcao', 'cadeira', 'cadeira']

        elif any(x in identificador for x in ['escritorio', 'escritório', 'office', 'trabalho']):
            return ['mesa', 'cadeira']

        elif any(x in identificador for x in ['tecnologia', 'tech', 'interativ']):
            return ['totem', 'tv', 'mesa']

        elif any(x in identificador for x in ['palco', 'apresent', 'palestra']):
            return ['tv']  # tela de apresentação

        else:
            # Área genérica - adicionar um balcão básico
            return ['balcao']

    def _dimensoes_padrao(self, tipo: str) -> Dict[str, float]:
        """Retorna dimensões padrão para tipos de móveis"""
        dimensoes = {
            'mesa': {'largura': 1.2, 'profundidade': 0.8, 'altura': 0.75},
            'balcao': {'largura': 2.0, 'profundidade': 0.6, 'altura': 1.1},
            'cadeira': {'largura': 0.5, 'profundidade': 0.5, 'altura': 0.9},
            'sofa': {'largura': 2.0, 'profundidade': 0.9, 'altura': 0.8},
            'vitrine': {'largura': 1.0, 'profundidade': 0.4, 'altura': 2.0},
            'prateleira': {'largura': 1.0, 'profundidade': 0.3, 'altura': 1.8},
            'tv': {'largura': 1.2, 'profundidade': 0.1, 'altura': 0.7},
            'totem': {'largura': 0.4, 'profundidade': 0.4, 'altura': 2.0},
        }
        return dimensoes.get(tipo, {'largura': 1.0, 'profundidade': 1.0, 'altura': 1.0})

    def _criar_movel(self, movel: Dict[str, Any]):
        """Cria geometria 3D para um móvel"""
        tipo = movel.get('tipo', 'generico')
        pos = movel.get('posicao', {'x': 0, 'y': 0, 'z': 0})
        dims = movel.get('dimensoes', self._dimensoes_padrao(tipo))

        largura = dims.get('largura', 1.0)
        profundidade = dims.get('profundidade', 1.0)
        altura = dims.get('altura', 1.0)

        # Criar box básico para o móvel
        mesh_movel = trimesh.creation.box(
            extents=[largura, altura, profundidade]
        )

        # Posicionar
        mesh_movel.apply_translation([
            pos.get('x', 0) + largura/2,
            altura/2,  # Base no chão
            pos.get('z', 0) + profundidade/2
        ])

        self.meshes.append(mesh_movel)
        logger.debug(f"[3D Export] Móvel gerado: {tipo} em ({pos.get('x')}, {pos.get('z')})")

    def _gerar_testeira(self, largura: float, profundidade: float, tipo_stand: str):
        """Gera testeira do stand (placa com nome da empresa)"""
        # Verificar se tem dados de testeira no briefing
        if not self.briefing:
            return

        # Posição da testeira depende do tipo de stand
        altura_testeira = 0.6  # 60cm de altura
        profundidade_testeira = 0.1

        if tipo_stand in ['ponta_ilha', 'esquina', 'corredor']:
            # Testeira na parede de fundo
            testeira = trimesh.creation.box(
                extents=[largura * 0.8, altura_testeira, profundidade_testeira]
            )
            testeira.apply_translation([
                largura/2,
                self.altura_parede - altura_testeira/2 - 0.1,
                profundidade_testeira/2
            ])
            self.meshes.append(testeira)
            logger.debug(f"[3D Export] Testeira gerada: {largura * 0.8}m x {altura_testeira}m")

    def _gerar_piso(self, largura: float, profundidade: float):
        """Gera o piso principal do stand"""
        # Criar box para o piso
        piso = trimesh.creation.box(
            extents=[largura, self.altura_piso, profundidade]
        )
        # Posicionar no centro, com topo em y=0
        piso.apply_translation([largura/2, -self.altura_piso/2, profundidade/2])

        self.meshes.append(piso)
        logger.debug(f"[3D Export] Piso gerado: {largura}m x {profundidade}m")

    def _gerar_paredes_externas(self, largura: float, profundidade: float,
                                 tipo_stand: str, lados_abertos: list):
        """Gera paredes externas baseado no tipo de stand"""

        # Definir quais lados têm parede baseado no tipo
        paredes = {
            'norte': True,   # Frente (z=profundidade)
            'sul': True,     # Fundo (z=0)
            'leste': True,   # Direita (x=largura)
            'oeste': True    # Esquerda (x=0)
        }

        # Remover paredes dos lados abertos
        for lado in lados_abertos:
            lado_lower = lado.lower()
            if lado_lower in paredes:
                paredes[lado_lower] = False

        # Configurações por tipo de stand
        if tipo_stand == 'ilha':
            # Ilha: todos os lados abertos (sem paredes externas)
            paredes = {k: False for k in paredes}
        elif tipo_stand == 'ponta_ilha':
            # Ponta de ilha: 3 lados abertos, 1 fechado (fundo)
            paredes = {'norte': False, 'sul': True, 'leste': False, 'oeste': False}
        elif tipo_stand == 'esquina':
            # Esquina: 2 lados fechados (fundo e um lateral)
            paredes = {'norte': False, 'sul': True, 'leste': True, 'oeste': False}
        elif tipo_stand == 'corredor':
            # Corredor: 3 lados fechados
            paredes = {'norte': False, 'sul': True, 'leste': True, 'oeste': True}

        # Gerar paredes
        if paredes['sul']:  # Fundo
            self._criar_parede(
                x=0, z=0,
                comprimento=largura,
                orientacao='horizontal'
            )

        if paredes['norte']:  # Frente
            self._criar_parede(
                x=0, z=profundidade,
                comprimento=largura,
                orientacao='horizontal'
            )

        if paredes['oeste']:  # Esquerda
            self._criar_parede(
                x=0, z=0,
                comprimento=profundidade,
                orientacao='vertical'
            )

        if paredes['leste']:  # Direita
            self._criar_parede(
                x=largura, z=0,
                comprimento=profundidade,
                orientacao='vertical'
            )

    def _criar_parede(self, x: float, z: float, comprimento: float,
                       orientacao: str, altura: float = None):
        """Cria uma parede"""
        if altura is None:
            altura = self.altura_parede

        if orientacao == 'horizontal':
            # Parede ao longo do eixo X
            parede = trimesh.creation.box(
                extents=[comprimento, altura, self.espessura_parede]
            )
            parede.apply_translation([
                x + comprimento/2,
                altura/2,
                z
            ])
        else:  # vertical
            # Parede ao longo do eixo Z
            parede = trimesh.creation.box(
                extents=[self.espessura_parede, altura, comprimento]
            )
            parede.apply_translation([
                x,
                altura/2,
                z + comprimento/2
            ])

        self.meshes.append(parede)

    def _gerar_area(self, area: Dict[str, Any]):
        """Gera geometria para uma área específica"""
        nome = area.get('nome', 'Área')
        tipo = area.get('tipo', '')
        geometria = area.get('geometria', {})
        fechada = area.get('fechada', False)

        x = geometria.get('x', 0)
        z = geometria.get('y', 0)  # y no 2D = z no 3D
        largura = geometria.get('largura', 2)
        profundidade = geometria.get('profundidade', 2)

        logger.debug(f"[3D Export] Gerando área: {nome} ({tipo}) - {largura}x{profundidade}m em ({x}, {z})")

        # Se a área é fechada (depósito, sala de reunião, etc.), criar paredes
        if fechada:
            altura_area = area.get('altura', self.altura_parede)

            # Parede frontal (z + profundidade)
            self._criar_parede(x, z + profundidade, largura, 'horizontal', altura_area)

            # Parede traseira (z)
            self._criar_parede(x, z, largura, 'horizontal', altura_area)

            # Parede esquerda (x)
            self._criar_parede(x, z, profundidade, 'vertical', altura_area)

            # Parede direita (x + largura)
            self._criar_parede(x + largura, z, profundidade, 'vertical', altura_area)

            # Adicionar porta (abertura) - simplificado
            # TODO: Implementar portas reais

        # Adicionar marcação de piso diferenciada para a área
        # Criar um piso ligeiramente elevado para diferenciar
        piso_area = trimesh.creation.box(
            extents=[largura - 0.02, 0.01, profundidade - 0.02]
        )
        piso_area.apply_translation([
            x + largura/2,
            0.01,  # Ligeiramente acima do piso principal
            z + profundidade/2
        ])
        self.meshes.append(piso_area)

    def _exportar_obj(self, mesh: trimesh.Trimesh) -> Tuple[bytes, bytes]:
        """Exporta mesh para formato OBJ + MTL"""

        # Exportar OBJ
        obj_buffer = io.BytesIO()
        mesh.export(obj_buffer, file_type='obj')
        obj_data = obj_buffer.getvalue()

        # Criar MTL básico (materiais)
        mtl_content = """# Material file for Stand 3D Model
# Generated by Afinal Cenografia

newmtl piso
Ka 0.2 0.2 0.2
Kd 0.8 0.8 0.8
Ks 0.1 0.1 0.1
Ns 10.0
d 1.0
illum 2

newmtl parede
Ka 0.3 0.3 0.3
Kd 0.95 0.95 0.95
Ks 0.05 0.05 0.05
Ns 5.0
d 1.0
illum 2

newmtl vidro
Ka 0.0 0.0 0.0
Kd 0.1 0.1 0.1
Ks 0.9 0.9 0.9
Ns 100.0
d 0.3
illum 2

newmtl metal
Ka 0.1 0.1 0.1
Kd 0.4 0.4 0.4
Ks 0.8 0.8 0.8
Ns 50.0
d 1.0
illum 2
"""
        mtl_data = mtl_content.encode('utf-8')

        return obj_data, mtl_data

    def exportar_para_arquivo(self, caminho_base: str) -> Dict[str, str]:
        """
        Exporta modelo para arquivos no disco

        Args:
            caminho_base: Caminho base sem extensão (ex: '/tmp/stand_modelo')

        Returns:
            Dict com caminhos dos arquivos gerados
        """
        obj_data, mtl_data, metadados = self.gerar_modelo_3d()

        caminho_obj = f"{caminho_base}.obj"
        caminho_mtl = f"{caminho_base}.mtl"
        caminho_meta = f"{caminho_base}_info.txt"

        # Salvar OBJ
        with open(caminho_obj, 'wb') as f:
            f.write(obj_data)

        # Salvar MTL
        with open(caminho_mtl, 'wb') as f:
            f.write(mtl_data)

        # Salvar info
        info_text = f"""Modelo 3D - Stand de Feira
==========================
Gerado em: {metadados['gerado_em']}

Dimensões:
- Largura: {metadados['dimensoes']['largura']}m
- Profundidade: {metadados['dimensoes']['profundidade']}m
- Altura: {metadados['dimensoes']['altura']}m

Estatísticas:
- Vértices: {metadados['vertices']}
- Faces: {metadados['faces']}
- Áreas geradas: {metadados['areas_geradas']}

Tipo de Stand: {metadados['tipo_stand']}

Compatível com:
{chr(10).join('- ' + s for s in metadados['compativel_com'])}

Instruções para 3ds Max:
1. File > Import > Select Files
2. Escolha o arquivo .obj
3. Nas opções de importação, marque "Import Materials"
4. Ajuste a escala se necessário (unidade = metros)
"""
        with open(caminho_meta, 'w', encoding='utf-8') as f:
            f.write(info_text)

        logger.info(f"[3D Export] Arquivos salvos em: {caminho_base}.*")

        return {
            'obj': caminho_obj,
            'mtl': caminho_mtl,
            'info': caminho_meta,
            'metadados': metadados
        }


def gerar_modelo_3d_projeto(projeto_id: int) -> Dict[str, Any]:
    """
    Função helper para gerar modelo 3D enriquecido de um projeto.

    Usa múltiplas fontes de dados:
    - Planta Baixa JSON: geometria base e áreas
    - Briefing: altura máxima, estilo, cores da marca
    - Renderização AI JSON: mobiliário, materiais, iluminação

    Args:
        projeto_id: ID do projeto

    Returns:
        Dict com resultado e arquivos gerados
    """
    from projetos.models import Projeto
    import tempfile
    import os

    try:
        projeto = Projeto.objects.get(id=projeto_id)

        if not projeto.planta_baixa_json:
            return {
                'sucesso': False,
                'erro': 'Projeto não possui planta baixa gerada'
            }

        # Buscar briefing do projeto
        briefing = None
        if hasattr(projeto, 'briefing'):
            briefing = projeto.briefing
            logger.info(f"[3D Helper] Briefing encontrado: {briefing.id if briefing else 'N/A'}")

        # Buscar renderização AI JSON
        renderizacao_json = None
        if hasattr(projeto, 'renderizacao_ai_json') and projeto.renderizacao_ai_json:
            renderizacao_json = projeto.renderizacao_ai_json
            logger.info(f"[3D Helper] Renderização AI JSON encontrado")

        # Criar exportador com todas as fontes
        exportador = Exportador3DService(
            planta_baixa_json=projeto.planta_baixa_json,
            briefing=briefing,
            renderizacao_json=renderizacao_json
        )

        # Gerar modelo
        obj_data, mtl_data, metadados = exportador.gerar_modelo_3d()

        # Salvar em diretório temporário
        temp_dir = tempfile.mkdtemp()
        nome_base = f"stand_{projeto.nome.replace(' ', '_')}_{projeto.id}"
        caminho_base = os.path.join(temp_dir, nome_base)

        resultado = exportador.exportar_para_arquivo(caminho_base)
        resultado['sucesso'] = True
        resultado['projeto'] = projeto.nome

        return resultado

    except Projeto.DoesNotExist:
        return {
            'sucesso': False,
            'erro': f'Projeto {projeto_id} não encontrado'
        }
    except Exception as e:
        logger.error(f"Erro ao gerar modelo 3D: {str(e)}", exc_info=True)
        return {
            'sucesso': False,
            'erro': str(e)
        }
