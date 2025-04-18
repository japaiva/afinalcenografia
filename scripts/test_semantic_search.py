"""
Script para diagnóstico específico de busca semântica
Salve este arquivo na raiz do seu projeto e execute:
python test_semantic_search.py
"""

import logging
import django
import os
import sys
import time
from typing import List, Dict, Any, Optional

# Configurar ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(asctime)s %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join('logs', 'semantic_test.log'))
    ]
)

logger = logging.getLogger(__name__)

# Importações do projeto
from core.models import Feira, FeiraManualQA, ParametroIndexacao
from core.utils.pinecone_utils import query_vectors, get_index, get_namespace_stats
from core.services.rag.embedding_service import EmbeddingService

def print_separator(title=""):
    """Imprime um separador visual no log"""
    separator = "=" * 80
    if title:
        logger.info(f"\n{separator}\n{title.center(80)}\n{separator}")
    else:
        logger.info(f"\n{separator}")

def check_parameters():
    """Verifica os parâmetros de threshold configurados no sistema"""
    print_separator("VERIFICAÇÃO DE PARÂMETROS")
    
    # Verificar parâmetros relacionados a threshold
    parameter_names = [
        ('SEARCH_THRESHOLD', 'search'),
        ('SEMANTIC_SCORE_THRESHOLD', 'search'),
        ('SIMILARITY_THRESHOLD', 'search'),
        ('VECTOR_SIMILARITY_THRESHOLD', 'search')
    ]
    
    found_parameters = []
    
    for param_name, category in parameter_names:
        try:
            param = ParametroIndexacao.objects.get(nome=param_name, categoria=category)
            value = param.valor_convertido()
            param_type = param.tipo
            logger.info(f"✓ Parâmetro encontrado: {param_name} = {value} (tipo: {param_type})")
            
            # Analisar o valor
            if isinstance(value, float) and param_name.endswith('THRESHOLD'):
                if value > 0.8:
                    logger.warning(f"⚠️ VALOR MUITO ALTO para threshold: {value} > 0.8")
                elif value < 0.3:
                    logger.warning(f"⚠️ VALOR MUITO BAIXO para threshold: {value} < 0.3")
                else:
                    logger.info(f"✓ Valor de threshold parece adequado: {value}")
            
            found_parameters.append((param_name, value))
        except ParametroIndexacao.DoesNotExist:
            logger.warning(f"✗ Parâmetro não encontrado: {param_name}")
        except Exception as e:
            logger.error(f"✗ Erro ao verificar parâmetro {param_name}: {str(e)}")
    
    return found_parameters

def check_namespaces():
    """Verifica os namespaces disponíveis no Pinecone"""
    print_separator("VERIFICAÇÃO DE NAMESPACES")
    
    try:
        # Verificar namespaces existentes
        index = get_index()
        if not index:
            logger.error("✗ Não foi possível obter o índice Pinecone")
            return []
            
        logger.info("Verificando namespaces no Pinecone...")
        stats = index.describe_index_stats()
        
        # Listar namespaces disponíveis
        namespaces = stats.namespaces
        if not namespaces:
            logger.warning("✗ Nenhum namespace encontrado no Pinecone")
            return []
            
        logger.info(f"✓ Encontrados {len(namespaces)} namespaces no Pinecone:")
        namespace_info = []
        
        for ns_name, ns_data in namespaces.items():
            vector_count = ns_data.vector_count
            logger.info(f"  - Namespace: '{ns_name}', Vetores: {vector_count}")
            namespace_info.append((ns_name, vector_count))
        
        return namespace_info
    
    except Exception as e:
        logger.error(f"✗ Erro ao verificar namespaces: {str(e)}")
        return []

def check_feira_namespaces():
    """Verifica namespaces das feiras cadastradas"""
    print_separator("VERIFICAÇÃO DE NAMESPACES DAS FEIRAS")
    
    try:
        # Verificar feiras cadastradas
        feiras = Feira.objects.all()
        if not feiras:
            logger.warning("✗ Nenhuma feira cadastrada no sistema")
            return []
            
        feira_namespaces = []
        logger.info(f"✓ Verificando namespaces de {feiras.count()} feiras:")
        
        for feira in feiras:
            try:
                # Verificar método get_qa_namespace
                if hasattr(feira, 'get_qa_namespace'):
                    namespace = feira.get_qa_namespace()
                    logger.info(f"  - Feira: {feira.nome} (ID: {feira.id}), Namespace QA: '{namespace}'")
                    feira_namespaces.append((feira.id, namespace))
                else:
                    logger.warning(f"✗ Feira {feira.id} não possui método get_qa_namespace")
            except Exception as e:
                logger.error(f"✗ Erro ao obter namespace da feira {feira.id}: {str(e)}")
        
        return feira_namespaces
    
    except Exception as e:
        logger.error(f"✗ Erro ao verificar feiras: {str(e)}")
        return []

def test_embedding_generation():
    """Testa a geração de embeddings"""
    print_separator("TESTE DE GERAÇÃO DE EMBEDDINGS")
    
    try:
        # Instanciar o serviço de embeddings
        embedding_service = EmbeddingService()
        logger.info("✓ Serviço de embeddings instanciado com sucesso")
        
        # Testar com consultas simples
        test_queries = [
            "Qual é a altura máxima permitida para estandes?",
            "Preciso de informações sobre montagem",
            "Horário de funcionamento da feira",
            "altura estande"  # Consulta mais curta
        ]
        
        embedding_results = []
        
        for query in test_queries:
            logger.info(f"Gerando embedding para: '{query}'")
            start_time = time.time()
            
            try:
                embedding = embedding_service.gerar_embedding_consulta(query)
                
                if embedding:
                    embedding_len = len(embedding)
                    elapsed_time = time.time() - start_time
                    logger.info(f"✓ Embedding gerado com sucesso: {embedding_len} dimensões em {elapsed_time:.2f}s")
                    logger.info(f"  Amostra: {embedding[:5]}...")
                    embedding_results.append((query, True, embedding_len))
                else:
                    logger.error(f"✗ Falha ao gerar embedding (retornou None ou vazio)")
                    embedding_results.append((query, False, 0))
            
            except Exception as e:
                logger.error(f"✗ Erro ao gerar embedding: {str(e)}")
                embedding_results.append((query, False, 0))
        
        return embedding_results
    
    except Exception as e:
        logger.error(f"✗ Erro ao testar geração de embeddings: {str(e)}")
        return []

def test_semantic_search(query_text, feira_id=None):
    """Testa a busca semântica diretamente, sem fallback para texto"""
    print_separator(f"TESTE DE BUSCA SEMÂNTICA: '{query_text}'")
    
    try:
        # Instanciar serviços necessários
        embedding_service = EmbeddingService()
        logger.info("✓ Serviço de embeddings instanciado com sucesso")
        
        # Obter parâmetros de busca
        try:
            search_threshold = ParametroIndexacao.objects.get(nome='SEARCH_THRESHOLD', categoria='search').valor_convertido()
            logger.info(f"✓ Threshold configurado: {search_threshold}")
        except:
            search_threshold = 0.7
            logger.warning(f"✗ Threshold não encontrado. Usando padrão: {search_threshold}")
        
        try:
            top_k = ParametroIndexacao.objects.get(nome='SEARCH_TOP_K', categoria='search').valor_convertido()
            logger.info(f"✓ Top K configurado: {top_k}")
        except:
            top_k = 3
            logger.warning(f"✗ Top K não encontrado. Usando padrão: {top_k}")
        
        # Gerar embedding para a consulta
        logger.info(f"Gerando embedding para query: '{query_text}'")
        query_embedding = embedding_service.gerar_embedding_consulta(query_text)
        
        if not query_embedding:
            logger.error("✗ Falha ao gerar embedding para a consulta")
            return False, []
            
        logger.info(f"✓ Embedding gerado com {len(query_embedding)} dimensões")
        logger.info(f"  Amostra: {query_embedding[:5]}...")
        
        # Obter o namespace específico para a feira
        if feira_id:
            try:
                feira = Feira.objects.get(pk=feira_id)
                namespace = feira.get_qa_namespace()
                logger.info(f"✓ Usando namespace específico para feira: '{namespace}'")
            except Feira.DoesNotExist:
                logger.error(f"✗ Feira ID {feira_id} não encontrada")
                return False, []
        else:
            # Usar o primeiro namespace de QA encontrado como teste
            try:
                index = get_index()
                stats = index.describe_index_stats()
                namespaces = stats.namespaces
                
                qa_namespaces = [ns for ns in namespaces.keys() if 'qa' in ns.lower()]
                if qa_namespaces:
                    namespace = qa_namespaces[0]
                    logger.info(f"✓ Usando primeiro namespace QA encontrado: '{namespace}'")
                else:
                    namespace = next(iter(namespaces.keys()))
                    logger.info(f"✓ Usando primeiro namespace disponível: '{namespace}'")
            except Exception as e:
                logger.error(f"✗ Erro ao determinar namespace: {str(e)}")
                return False, []
        
        # Verificar se o namespace existe e tem vetores
        try:
            stats = get_namespace_stats(namespace)
            if stats and stats['exists']:
                logger.info(f"✓ Namespace '{namespace}' encontrado com {stats['vector_count']} vetores")
            else:
                logger.error(f"✗ Namespace '{namespace}' não existe ou está vazio")
                return False, []
        except Exception as e:
            logger.error(f"✗ Erro ao verificar namespace: {str(e)}")
            return False, []
        
        # Preparar filtro (se aplicável)
        filter_obj = {"feira_id": {"$eq": str(feira_id)}} if feira_id else None
        logger.info(f"✓ Filtro: {filter_obj}")
        
        # Realizar consulta no Pinecone
        logger.info(f"Consultando Pinecone (namespace: '{namespace}', top_k: {top_k})")
        try:
            results = query_vectors(query_embedding, namespace, top_k, filter_obj)
            
            if not results:
                logger.warning("✗ Consulta não retornou resultados")
                return True, []
                
            logger.info(f"✓ Consulta retornou {len(results)} resultados")
            
            # Analisar resultados
            logger.info("\nResultados da consulta (antes do filtro por threshold):")
            for i, result in enumerate(results):
                score = result['score']
                above_threshold = score >= search_threshold
                symbol = "✓" if above_threshold else "✗"
                
                logger.info(f"  {symbol} Resultado {i+1}: ID={result['id']}, Score={score:.4f} {'≥' if above_threshold else '<'} {search_threshold}")
                
                # Mostrar metadados básicos
                metadata = result['metadata']
                if metadata:
                    question = metadata.get('q', '')[:50] + ('...' if len(metadata.get('q', '')) > 50 else '')
                    logger.info(f"    Pergunta: {question}")
            
            # Filtrar por threshold
            filtered_results = [r for r in results if r['score'] >= search_threshold]
            logger.info(f"\n✓ Resultados após filtro por threshold: {len(filtered_results)}/{len(results)}")
            
            if not filtered_results:
                logger.warning(f"⚠️ PROBLEMA DETECTADO: Todos os resultados foram filtrados pelo threshold ({search_threshold})")
                logger.warning(f"  Isso explica porque a busca semântica está caindo para busca textual!")
                logger.warning(f"  Recomendação: Reduza o threshold para um valor como 0.5")
            
            return True, results
            
        except Exception as e:
            logger.error(f"✗ Erro ao consultar Pinecone: {str(e)}")
            return False, []
    
    except Exception as e:
        logger.error(f"✗ Erro geral no teste de busca semântica: {str(e)}")
        return False, []

def verify_namespace_match():
    """Verifica se os namespaces das feiras correspondem aos namespaces no Pinecone"""
    print_separator("VERIFICAÇÃO DE CORRESPONDÊNCIA DE NAMESPACES")
    
    # Obter namespaces das feiras
    feira_namespaces = check_feira_namespaces()
    
    # Obter namespaces do Pinecone
    pinecone_namespaces = check_namespaces()
    pinecone_ns_names = [ns[0] for ns in pinecone_namespaces]
    
    # Verificar correspondência
    for feira_id, namespace in feira_namespaces:
        if namespace in pinecone_ns_names:
            logger.info(f"✓ Namespace da feira {feira_id} ('{namespace}') existe no Pinecone")
        else:
            logger.error(f"✗ PROBLEMA CRÍTICO: Namespace da feira {feira_id} ('{namespace}') NÃO existe no Pinecone")
            logger.error(f"  Isso explica porque a busca semântica está caindo para busca textual!")
            logger.error(f"  Namespaces disponíveis: {pinecone_ns_names}")

def run_all_tests():
    """Executa todos os testes de diagnóstico"""
    print_separator("INÍCIO DO DIAGNÓSTICO DE BUSCA SEMÂNTICA")
    
    # 1. Verificar parâmetros de threshold
    parameters = check_parameters()
    
    # 2. Verificar namespaces
    pinecone_namespaces = check_namespaces()
    
    # 3. Verificar namespaces das feiras
    feira_namespaces = check_feira_namespaces()
    
    # 4. Verificar correspondência de namespaces
    verify_namespace_match()
    
    # 5. Testar geração de embeddings
    embedding_results = test_embedding_generation()
    
    # 6. Testar busca semântica com queries específicas
    test_queries = [
        "altura máxima de estandes",
        "horário de funcionamento",
        "onde encontro informações sobre montagem",
        "preciso de ajuda com credenciamento"
    ]
    
    search_results = []
    for query in test_queries:
        # Testar com a primeira feira disponível ou sem feira
        feira_id = feira_namespaces[0][0] if feira_namespaces else None
        success, results = test_semantic_search(query, feira_id)
        search_results.append((query, success, len(results) if results else 0))
    
    # 7. Resumo dos testes
    print_separator("RESUMO DO DIAGNÓSTICO")
    
    logger.info("1. Parâmetros verificados:")
    for param_name, value in parameters:
        logger.info(f"  - {param_name} = {value}")
    
    logger.info("\n2. Namespaces no Pinecone:")
    for ns_name, count in pinecone_namespaces:
        logger.info(f"  - '{ns_name}': {count} vetores")
    
    logger.info("\n3. Namespaces das feiras:")
    for feira_id, namespace in feira_namespaces:
        in_pinecone = any(ns[0] == namespace for ns in pinecone_namespaces)
        symbol = "✓" if in_pinecone else "✗"
        logger.info(f"  - {symbol} Feira {feira_id}: '{namespace}'")
    
    logger.info("\n4. Geração de embeddings:")
    for query, success, dim in embedding_results:
        symbol = "✓" if success else "✗"
        logger.info(f"  - {symbol} '{query}': {dim} dimensões")
    
    logger.info("\n5. Busca semântica:")
    for query, success, count in search_results:
        symbol = "✓" if success and count > 0 else "✗"
        logger.info(f"  - {symbol} '{query}': {count} resultados")
    
    logger.info("\n6. Problemas detectados:")
    problems = []
    
    # Verificar threshold
    threshold_params = [p for p in parameters if 'THRESHOLD' in p[0]]
    if threshold_params:
        for param_name, value in threshold_params:
            if value > 0.75:
                problems.append(f"Threshold muito alto: {param_name} = {value} > 0.75")
            elif value < 0.3:
                problems.append(f"Threshold muito baixo: {param_name} = {value} < 0.3")
    else:
        problems.append("Nenhum parâmetro de threshold encontrado")
    
    # Verificar namespaces
    for feira_id, namespace in feira_namespaces:
        if not any(ns[0] == namespace for ns in pinecone_namespaces):
            problems.append(f"Namespace da feira {feira_id} ('{namespace}') não existe no Pinecone")
    
    # Verificar embeddings
    if not all(success for _, success, _ in embedding_results):
        problems.append("Falha na geração de embeddings para algumas consultas")
    
    # Verificar resultados de busca
    if not all(success for _, success, _ in search_results):
        problems.append("Falha na execução da busca semântica para algumas consultas")
    
    if not any(count > 0 for _, _, count in search_results):
        problems.append("Nenhuma consulta retornou resultados")
    
    # Exibir problemas
    if problems:
        for problem in problems:
            logger.warning(f"  - ⚠️ {problem}")
    else:
        logger.info("  ✓ Nenhum problema óbvio detectado")
    
    # 8. Recomendações
    print_separator("RECOMENDAÇÕES")
    
    if any(p.startswith("Namespace da feira") for p in problems):
        logger.info("1. Corrija os namespaces das feiras para corresponderem aos existentes no Pinecone")
        logger.info("   Namespaces disponíveis: " + ", ".join([f"'{ns[0]}'" for ns in pinecone_namespaces]))
    
    if any(p.startswith("Threshold muito alto") for p in problems):
        logger.info("2. Reduza o valor do threshold para 0.5 ou 0.6")
        logger.info("   Exemplo: UPDATE core_parametroindexacao SET valor='0.5' WHERE nome='SEARCH_THRESHOLD'")
    
    if "Falha na geração de embeddings" in "\n".join(problems):
        logger.info("3. Verifique a configuração do serviço de embeddings (provavelmente OpenAI API)")
    
    logger.info("\nPara testar novamente após as correções, execute:")
    logger.info("python test_semantic_search.py")
    
    print_separator("FIM DO DIAGNÓSTICO")

if __name__ == "__main__":
    run_all_tests()