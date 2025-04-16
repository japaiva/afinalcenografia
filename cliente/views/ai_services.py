# briefing/ai_services.py

import json
import logging
from django.conf import settings
from core.models import Agente
from core.services.rag.retrieval_service import RetrievalService
from core.services.rag.embedding_service import EmbeddingService
from core.services.rag_service import RAGService

logger = logging.getLogger(__name__)

def validar_briefing_com_ia(briefing):
    """
    Função para validar o briefing usando IA
    Retorna um dicionário com o resultado da validação
    """
    try:
        # Obtém o agente de validação de briefing
        agente = Agente.objects.get(nome="ValidadorBriefing", ativo=True)
        
        # Serializa o briefing para enviar à IA
        briefing_data = {
            # Informações básicas
            "categoria_projeto": briefing.categoria_projeto,
            "descricao_detalhada": briefing.descricao_detalhada,
            "objetivos": briefing.objetivos,
            "estilo_estande": briefing.estilo_estande,
            
            # Detalhes técnicos
            "dimensoes": briefing.dimensoes,
            "altura": briefing.altura,
            "paleta_cores": briefing.paleta_cores,
            "piso_elevado": briefing.get_piso_elevado_display() if briefing.piso_elevado else None,
            "testeira": briefing.get_testeira_display() if briefing.testeira else None,
            "venda_no_estande": briefing.venda_no_estande,
            
            # Materiais e acabamentos
            "materiais_preferidos": briefing.materiais_preferidos,
            "acabamentos": briefing.acabamentos,
            
            # Requisitos técnicos
            "iluminacao": briefing.iluminacao,
            "eletrica": briefing.eletrica,
            
            # Espaços
            "tem_sala_reuniao": briefing.tem_sala_reuniao,
            "tem_mesas_atendimento": briefing.tem_mesas_atendimento,
            "tem_lounge": briefing.tem_lounge,
            "tem_copa": briefing.tem_copa,
            "tem_deposito": briefing.tem_deposito,
            "tem_balcao_cafe": briefing.tem_balcao_cafe,
            "tem_vitrine": briefing.tem_vitrine,
            "tem_balcao_vitrine": briefing.tem_balcao_vitrine,
            "tem_balcao_recepcao": briefing.tem_balcao_recepcao,
            "tem_caixa": briefing.tem_caixa,
            "tem_ativacao": briefing.tem_ativacao,
            
            # Orçamento e datas (do projeto)
            "orcamento": float(briefing.projeto.orcamento),
            "data_inicio": str(briefing.projeto.data_inicio) if briefing.projeto.data_inicio else None,
            "data_termino": str(briefing.projeto.data_termino) if briefing.projeto.data_termino else None,
            
            # Feira
            "feira_nome": briefing.projeto.feira.nome if briefing.projeto.feira else None,
            "feira_local": briefing.projeto.feira.local if briefing.projeto.feira else None,
        }
        
        # Consulta o manual da feira se disponível usando o serviço RAG existente
        contexto_manual = ""
        if briefing.projeto.feira and briefing.projeto.feira.manual and briefing.projeto.feira.manual_processado:
            # Usar o RetrievalService existente
            retrieval_service = RetrievalService()
            
            # Criar uma consulta para o RAG relacionada ao briefing
            query = "Verifique se este briefing está de acordo com as regras da feira"
            
            # Buscar QAs relevantes para a consulta
            qa_results = retrieval_service.pesquisar_qa(
                query=query,
                feira_id=briefing.projeto.feira.id,
                top_k=5
            )
            
            # Adicionar os resultados relevantes ao contexto
            if qa_results:
                for result in qa_results:
                    if result['score'] > 0.7:  # Threshold de relevância
                        contexto_manual += f"Pergunta: {result['question']}\n"
                        contexto_manual += f"Resposta: {result['answer']}\n\n"
        
        # Monta o prompt para a IA
        prompt = f"""
        {agente.llm_system_prompt}
        
        Você está validando um briefing para um projeto de cenografia para feira/evento.
        
        INFORMAÇÕES DO BRIEFING:
        {json.dumps(briefing_data, indent=2)}
        
        {f"CONTEXTO DO MANUAL DA FEIRA: {contexto_manual}" if contexto_manual else ""}
        
        {agente.task_instructions}
        
        Valide este briefing e retorne um JSON com os seguintes campos:
        1. "is_valid": true/false - se o briefing está válido ou não
        2. "validacoes": um objeto com chaves para cada seção ("informacoes_basicas", "detalhes_tecnicos", "materiais_acabamentos", "requisitos_tecnicos") e para cada uma um objeto com:
           - "status": "aprovado", "atencao" ou "reprovado"
           - "mensagem": explicação da validação ou sugestões
        3. "sugestoes_gerais": lista de sugestões para melhorar o briefing
        """
        
        # Usar utility do sistema para obter cliente LLM
        from core.utils.llm_utils import get_llm_client
        client, model, temperature, system_prompt, task_instructions = get_llm_client(agente.nome)
        
        # Determinar o provider com base no cliente
        if hasattr(client, 'chat'):  # OpenAI
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
            )
            content = response.choices[0].message.content
            
        elif hasattr(client, 'messages'):  # Anthropic
            response = client.messages.create(
                model=model,
                max_tokens=4000,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            content = response.content[0].text
            
        elif hasattr(client, 'completion'):  # Groq
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
            )
            content = response.choices[0].message.content
        
        # Tenta encontrar um bloco JSON na resposta
        try:
            # Procura por blocos de código JSON
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', content)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                # Tenta interpretar toda a resposta como JSON
                result = json.loads(content)
        except json.JSONDecodeError:
            # Se falhar, tenta extrair apenas o necessário
            result = {
                "is_valid": "true" in content.lower() and "válido" in content.lower(),
                "validacoes": {
                    "informacoes_basicas": {"status": "aprovado", "mensagem": "Não foi possível validar automaticamente."},
                    "detalhes_tecnicos": {"status": "aprovado", "mensagem": "Não foi possível validar automaticamente."},
                    "materiais_acabamentos": {"status": "aprovado", "mensagem": "Não foi possível validar automaticamente."},
                    "requisitos_tecnicos": {"status": "aprovado", "mensagem": "Não foi possível validar automaticamente."}
                },
                "sugestoes_gerais": ["A validação automática não foi possível. Revise manualmente o briefing."]
            }
        
        # Atualiza as validações no banco
        for secao, validacao in result.get('validacoes', {}).items():
            briefing_validacao = briefing.validacoes.get(secao=secao)
            briefing_validacao.status = validacao.get('status', 'pendente')
            briefing_validacao.mensagem = validacao.get('mensagem', '')
            briefing_validacao.save()
        
        return {
            'success': True,
            'is_valid': result.get('is_valid', False),
            'validacoes': result.get('validacoes', {}),
            'sugestoes': result.get('sugestoes_gerais', [])
        }
    
    except Exception as e:
        # Log do erro
        logger.error(f"Erro na validação do briefing: {str(e)}")
        
        return {
            'success': False,
            'error': str(e)
        }

def processar_mensagem_ia(briefing, mensagem, etapa):
    """
    Processa uma mensagem do cliente para o assistente de IA
    """
    try:
        # Obtém o agente de assistente de briefing
        agente = Agente.objects.get(nome="AssistenteBriefing", ativo=True)
        
        # Determina o contexto baseado na etapa
        if etapa == 1:
            contexto = "informações básicas do projeto (categoria, descrição, objetivos, estilo)"
            campos_relevantes = {
                "categoria_projeto": briefing.categoria_projeto,
                "descricao_detalhada": briefing.descricao_detalhada,
                "objetivos": briefing.objetivos,
                "estilo_estande": briefing.estilo_estande
            }
        elif etapa == 2:
            contexto = "detalhes técnicos (dimensões, altura, cores, piso)"
            campos_relevantes = {
                "dimensoes": briefing.dimensoes,
                "altura": briefing.altura,
                "paleta_cores": briefing.paleta_cores,
                "piso_elevado": briefing.get_piso_elevado_display() if briefing.piso_elevado else None,
                "testeira": briefing.get_testeira_display() if briefing.testeira else None,
                "venda_no_estande": briefing.venda_no_estande
            }
        elif etapa == 3:
            contexto = "materiais e acabamentos"
            campos_relevantes = {
                "materiais_preferidos": briefing.materiais_preferidos,
                "acabamentos": briefing.acabamentos
            }
        else:  # etapa == 4
            contexto = "requisitos técnicos e espaços (iluminação, elétrica, sala de reunião, etc.)"
            campos_relevantes = {
                "iluminacao": briefing.iluminacao,
                "eletrica": briefing.eletrica,
                "tem_sala_reuniao": briefing.tem_sala_reuniao,
                "tem_mesas_atendimento": briefing.tem_mesas_atendimento,
                "tem_lounge": briefing.tem_lounge,
                "tem_copa": briefing.tem_copa,
                "tem_deposito": briefing.tem_deposito,
                "tem_balcao_cafe": briefing.tem_balcao_cafe,
                "tem_vitrine": briefing.tem_vitrine,
                "tem_balcao_vitrine": briefing.tem_balcao_vitrine,
                "tem_balcao_recepcao": briefing.tem_balcao_recepcao,
                "tem_caixa": briefing.tem_caixa,
                "tem_ativacao": briefing.tem_ativacao
            }
        
        # Consulta o manual da feira se disponível usando o sistema RAG existente
        contexto_manual = ""
        if briefing.projeto.feira and briefing.projeto.feira.manual and briefing.projeto.feira.manual_processado:
            # Inicializar o serviço RAG
            rag_service = RAGService()
            
            # Usar o sistema RAG para obter uma resposta baseada na mensagem do usuário
            rag_result = rag_service.gerar_resposta_rag(
                query=mensagem,
                feira_id=briefing.projeto.feira.id
            )
            
            # Se encontramos uma resposta, usar como contexto
            if rag_result['status'] == 'success':
                contexto_manual = rag_result['resposta']
                
                # Também incluir os contextos que foram usados para gerar a resposta
                if rag_result.get('contextos'):
                    contexto_manual += "\n\nBaseado nos seguintes contextos:\n"
                    for ctx in rag_result['contextos'][:2]:  # Limitar a 2 contextos para não ficar muito grande
                        contexto_manual += f"- {ctx['question']}\n"
        
        # Obtém o histórico de conversas recentes desta etapa
        conversas_recentes = briefing.conversas.filter(etapa=etapa).order_by('-timestamp')[:5]
        historico = []
        for conversa in reversed(list(conversas_recentes)):
            role = "user" if conversa.origem == "cliente" else "assistant"
            historico.append({"role": role, "content": conversa.mensagem})
        
        # Monta o prompt para a IA
        prompt = f"""
        Você é um assistente especializado em projetos cenográficos para feiras e eventos.
        
        Estamos na etapa {etapa} do briefing sobre {contexto}.
        
        Dados preenchidos nesta etapa:
        {json.dumps(campos_relevantes, indent=2)}
        
        Dados gerais do projeto:
        - Feira: {briefing.projeto.feira.nome if briefing.projeto.feira else 'Não definida'}
        - Orçamento: R$ {briefing.projeto.orcamento}
        
        {f"INFORMAÇÕES RELEVANTES DO MANUAL DA FEIRA: {contexto_manual}" if contexto_manual else ""}
        
        Pergunta do cliente: {mensagem}
        
        Responda de forma útil e concisa, oferecendo sugestões práticas e orientações sobre como preencher o briefing.
        """
        
        # Usar utility do sistema para obter cliente LLM
        from core.utils.llm_utils import get_llm_client
        client, model, temperature, system_prompt, task_instructions = get_llm_client(agente.nome)
        
        # Prepara mensagens para o formato da API
        messages = []
        
        # Adiciona o histórico de conversa se existir
        if historico:
            messages.extend(historico)
        
        # Adiciona a mensagem atual
        messages.append({"role": "user", "content": prompt})
        
        # Determinar o provider com base no cliente
        if hasattr(client, 'chat'):  # OpenAI
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                temperature=temperature,
            )
            resposta = response.choices[0].message.content
            
        elif hasattr(client, 'messages'):  # Anthropic
            # Ajustar formato para Anthropic
            anthropic_messages = []
            for msg in messages:
                anthropic_messages.append({"role": msg["role"], "content": msg["content"]})
            
            response = client.messages.create(
                model=model,
                max_tokens=1000,
                temperature=temperature,
                system=system_prompt,
                messages=anthropic_messages
            )
            resposta = response.content[0].text
            
        elif hasattr(client, 'completion'):  # Groq
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                temperature=temperature,
            )
            resposta = response.choices[0].message.content
        
        return {
            'success': True,
            'mensagem': resposta
        }
    
    except Exception as e:
        # Log do erro
        logger.error(f"Erro no processamento da mensagem: {str(e)}")
        
        return {
            'success': False,
            'mensagem': f"Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente mais tarde."
        }

# Não precisamos mais da função get_embedding pois já utilizamos os serviços do core