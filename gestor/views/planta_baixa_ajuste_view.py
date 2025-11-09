"""
Views para ajuste conversacional de dimensões da planta baixa
"""
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
import json
import re


class AjusteConversacionalView(LoginRequiredMixin, View):
    """
    Processa comandos conversacionais para ajustar dimensões das áreas
    """

    def post(self, request, projeto_id):
        try:
            data = json.loads(request.body)
            comando = data.get('comando', '').lower()
            layout_atual = data.get('layout_atual')

            if not layout_atual:
                return JsonResponse({
                    'sucesso': False,
                    'erro': 'Layout não encontrado. Execute as etapas primeiro.'
                })

            # Interpretar comando
            ajuste = self._interpretar_comando(comando, layout_atual)

            if ajuste:
                return JsonResponse({
                    'sucesso': True,
                    'resposta': ajuste['resposta'],
                    'ajuste': ajuste['dados']
                })
            else:
                return JsonResponse({
                    'sucesso': False,
                    'erro': 'Não entendi o comando. Tente: "deposito e workshop mesmo tamanho"'
                })

        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': str(e)})

    def _interpretar_comando(self, comando, layout):
        """
        Interpreta comandos naturais e gera ajustes

        Padrões suportados:
        - "deposito e workshop mesmo tamanho"
        - "deposito 40% workshop 50%"
        - "corredor mais largo"
        - "corredor 15%"
        """

        # Padrão 1: "X e Y mesmo tamanho"
        if 'mesmo' in comando or 'igual' in comando or 'similar' in comando:
            # Extrair nomes das áreas
            match = re.search(r'(\w+)\s+e\s+(\w+)', comando)
            if match:
                area1, area2 = match.groups()

                # Calcular percentual (assumindo 10% de corredor)
                percentual = 0.45  # 45% cada

                return {
                    'resposta': f'✅ Entendi! Vou ajustar:\n• {area1.title()}: 45% (~5m)\n• {area2.title()}: 45% (~5m)\n• Corredor mantém 10% (~1m)',
                    'dados': {
                        'tipo': 'mesmo_tamanho',
                        'areas': [area1, area2],
                        'percentual': percentual
                    }
                }

        # Padrão 2: "deposito 40% workshop 50%"
        percentuais = re.findall(r'(\w+)\s+(\d+)%', comando)
        if percentuais:
            ajustes = []
            resposta_partes = []
            total = 0

            for area, percent in percentuais:
                valor = int(percent) / 100
                ajustes.append({'area': area, 'w': valor})
                resposta_partes.append(f'• {area.title()}: {percent}%')
                total += valor

            # Verificar se soma ~100%
            aviso = ''
            if total < 0.95 or total > 1.05:
                aviso = f'\n⚠️ Soma {int(total*100)}% - vou ajustar para 100%'

            return {
                'resposta': f'✅ Entendi! Vou ajustar:\n' + '\n'.join(resposta_partes) + aviso,
                'dados': {
                    'tipo': 'percentuais',
                    'ajustes': ajustes
                }
            }

        # Padrão 3: "corredor mais largo/maior"
        if 'corredor' in comando:
            if 'largo' in comando or 'maior' in comando or 'amplo' in comando:
                return {
                    'resposta': '✅ Vou aumentar o corredor:\n• Corredor: 10% → 15% (~1.65m)',
                    'dados': {
                        'tipo': 'percentuais',
                        'ajustes': [{'area': 'corredor', 'w': 0.15}]
                    }
                }
            elif 'estreito' in comando or 'menor' in comando:
                return {
                    'resposta': '✅ Vou diminuir o corredor:\n• Corredor: 10% → 7% (~0.8m)',
                    'dados': {
                        'tipo': 'percentuais',
                        'ajustes': [{'area': 'corredor', 'w': 0.07}]
                    }
                }
            # Percentual específico para corredor
            match = re.search(r'(\d+)%', comando)
            if match:
                percent = int(match.group(1))
                return {
                    'resposta': f'✅ Vou ajustar:\n• Corredor: {percent}%',
                    'dados': {
                        'tipo': 'percentuais',
                        'ajustes': [{'area': 'corredor', 'w': percent / 100}]
                    }
                }

        # Padrão 4: Ajustar uma área específica
        match = re.search(r'(\w+)\s+(?:para\s+)?(\d+)%', comando)
        if match:
            area, percent = match.groups()
            return {
                'resposta': f'✅ Vou ajustar:\n• {area.title()}: {percent}%',
                'dados': {
                    'tipo': 'percentuais',
                    'ajustes': [{'area': area, 'w': int(percent) / 100}]
                }
            }

        return None


class AplicarAjustesView(LoginRequiredMixin, View):
    """
    Aplica ajustes ao layout e retorna layout modificado
    """

    def post(self, request, projeto_id):
        try:
            data = json.loads(request.body)
            ajustes = data.get('ajustes', [])
            layout = data.get('layout_atual')

            if not layout:
                return JsonResponse({
                    'sucesso': False,
                    'erro': 'Layout não encontrado'
                })

            # Debug: verificar estrutura do layout
            print(f"\n🔍 DEBUG - Estrutura do layout recebido:")
            print(f"Chaves do layout: {layout.keys()}")
            if 'areas' in layout and len(layout['areas']) > 0:
                print(f"Primeira área: {layout['areas'][0].keys()}")
                print(f"Conteúdo da primeira área: {layout['areas'][0]}")

            # Aplicar cada ajuste
            for ajuste in ajustes:
                layout = self._aplicar_ajuste(layout, ajuste)

            # Normalizar para 100%
            layout = self._normalizar_100porcento(layout)

            # Recalcular coordenadas absolutas (m)
            layout = self._recalcular_metros(layout, projeto_id)

            # Salvar layout ajustado no banco
            from projetos.models import Projeto
            try:
                projeto = Projeto.objects.get(id=projeto_id)
                projeto.planta_baixa_json = layout
                projeto.save(update_fields=['planta_baixa_json'])
                print(f"✅ Layout ajustado salvo no projeto {projeto_id}")
            except Exception as e:
                print(f"⚠️ Erro ao salvar layout no banco: {e}")

            return JsonResponse({
                'sucesso': True,
                'layout_ajustado': layout,
                'salvo': True
            })

        except Exception as e:
            import traceback
            print(f"\n❌ ERRO ao aplicar ajustes:")
            traceback.print_exc()
            return JsonResponse({
                'sucesso': False,
                'erro': f'Erro ao aplicar ajustes: {str(e)}'
            })

    def _aplicar_ajuste(self, layout, ajuste):
        """Aplica um ajuste específico ao layout"""

        # Tentar diferentes estruturas possíveis
        areas = layout.get('areas', [])
        if not areas:
            # Tentar estrutura alternativa
            areas = layout.get('layout', {}).get('areas', [])

        if not areas:
            raise ValueError("Nenhuma área encontrada no layout")

        if ajuste['tipo'] == 'mesmo_tamanho':
            # Ajustar áreas para mesmo tamanho
            nomes_areas = ajuste['areas']
            percentual = ajuste['percentual']

            areas_ajustadas = 0
            for area in areas:
                area_id = area.get('id', area.get('nome', area.get('tipo', ''))).lower()

                if any(nome.lower() in area_id for nome in nomes_areas):
                    # Tentar diferentes campos para bbox
                    if 'bbox_norm' in area:
                        area['bbox_norm']['w'] = percentual
                        areas_ajustadas += 1
                    elif 'geometria_norm' in area:
                        area['geometria_norm']['w'] = percentual
                        areas_ajustadas += 1
                    elif 'bbox' in area:
                        area['bbox']['w'] = percentual
                        areas_ajustadas += 1
                    else:
                        print(f"⚠️ Área {area_id} não tem campo de geometria reconhecido. Campos: {list(area.keys())}")

            if areas_ajustadas == 0:
                raise ValueError(f"Nenhuma área foi ajustada. Áreas procuradas: {nomes_areas}")

        elif ajuste['tipo'] == 'percentuais':
            # Ajustar percentuais específicos
            for item in ajuste['ajustes']:
                area_nome = item['area'].lower()
                novo_w = item['w']
                ajustado = False

                for area in areas:
                    area_id = area.get('id', area.get('nome', area.get('tipo', ''))).lower()

                    if area_nome in area_id:
                        # Tentar diferentes campos para bbox
                        if 'bbox_norm' in area:
                            area['bbox_norm']['w'] = novo_w
                            ajustado = True
                        elif 'geometria_norm' in area:
                            area['geometria_norm']['w'] = novo_w
                            ajustado = True
                        elif 'bbox' in area:
                            area['bbox']['w'] = novo_w
                            ajustado = True
                        else:
                            print(f"⚠️ Área {area_id} não tem campo de geometria reconhecido. Campos: {list(area.keys())}")
                        break

                if not ajustado:
                    print(f"⚠️ Área '{area_nome}' não foi encontrada para ajuste")

        return layout

    def _normalizar_100porcento(self, layout):
        """
        Garante que áreas na mesma linha horizontal somem 100%
        Recalcula coordenadas X sequencialmente
        """
        areas = layout.get('areas', [])
        if not areas:
            areas = layout.get('layout', {}).get('areas', [])

        if not areas:
            return layout

        # Detectar qual campo de geometria está sendo usado
        campo_geom = None
        for area in areas:
            if 'bbox_norm' in area:
                campo_geom = 'bbox_norm'
                break
            elif 'geometria_norm' in area:
                campo_geom = 'geometria_norm'
                break
            elif 'bbox' in area:
                campo_geom = 'bbox'
                break

        if not campo_geom:
            print("⚠️ Nenhum campo de geometria encontrado para normalizar")
            return layout

        # Separar por linha (y)
        linhas = {}
        for area in areas:
            if campo_geom not in area:
                continue
            y = area[campo_geom]['y']
            if y not in linhas:
                linhas[y] = []
            linhas[y].append(area)

        # Para cada linha horizontal
        for y, areas_linha in linhas.items():
            # Ordenar por X
            areas_linha.sort(key=lambda a: a[campo_geom]['x'])

            # Calcular soma atual
            soma_w = sum(a[campo_geom]['w'] for a in areas_linha)

            # Se não soma 100%, ajustar última área
            if abs(soma_w - 1.0) > 0.01:
                # Ajustar última área para fechar em 100%
                if areas_linha:
                    diferenca = 1.0 - (soma_w - areas_linha[-1][campo_geom]['w'])
                    areas_linha[-1][campo_geom]['w'] = max(0.1, diferenca)

            # Recalcular coordenadas X sequenciais
            x_atual = 0.0
            for area in areas_linha:
                area[campo_geom]['x'] = round(x_atual, 3)
                x_atual += area[campo_geom]['w']

        return layout

    def _recalcular_metros(self, layout, projeto_id):
        """
        Recalcula coordenadas em metros baseado nas dimensões do stand
        """
        from projetos.models import Projeto

        try:
            projeto = Projeto.objects.get(id=projeto_id)
            briefing = projeto.briefing

            # Obter dimensões do briefing
            largura_m = float(briefing.medida_frente or briefing.medida_frente_m or 11.0)
            lateral_esq = briefing.medida_lateral_esquerda if hasattr(briefing, 'medida_lateral_esquerda') else None
            lateral_dir = briefing.medida_lateral_direita if hasattr(briefing, 'medida_lateral_direita') else None
            profundidade_m = float(lateral_esq or lateral_dir or briefing.medida_lateral_m or 8.0)
            altura_m = float(briefing.altura_m or briefing.altura or 3.0)

            # Adicionar dimensões totais
            layout['dimensoes_totais'] = {
                'largura': largura_m,
                'profundidade': profundidade_m,
                'altura': altura_m,
                'area_total': largura_m * profundidade_m
            }

            # Obter áreas
            areas = layout.get('areas', [])
            if not areas:
                areas = layout.get('layout', {}).get('areas', [])

            # Detectar campo de geometria normalizada
            campo_geom = None
            for area in areas:
                if 'bbox_norm' in area:
                    campo_geom = 'bbox_norm'
                    break
                elif 'geometria_norm' in area:
                    campo_geom = 'geometria_norm'
                    break
                elif 'bbox' in area:
                    campo_geom = 'bbox'
                    break

            if not campo_geom:
                print("⚠️ Nenhum campo de geometria encontrado para recalcular metros")
                return layout

            # Recalcular geometria de cada área
            for area in areas:
                if campo_geom not in area:
                    continue

                bbox = area[campo_geom]

                geometria = {
                    'x': round(bbox['x'] * largura_m, 2),
                    'y': round(bbox['y'] * profundidade_m, 2),
                    'largura': round(bbox['w'] * largura_m, 2),
                    'profundidade': round(bbox['h'] * profundidade_m, 2),
                    'altura': altura_m
                }
                geometria['area'] = round(geometria['largura'] * geometria['profundidade'], 2)

                area['geometria'] = geometria

            return layout

        except Exception as e:
            import traceback
            print(f"❌ Erro ao recalcular metros: {e}")
            traceback.print_exc()
            return layout
