from django.http import HttpResponse
from core.models import ParametroIndexacao, Feira
from core.services.rag.embedding_service import EmbeddingService
from core.utils.pinecone_utils import query_vectors, get_namespace_stats, get_index

def debug_search_view(request):
    output = []
    output.append("<h1>Diagnóstico de Busca Semântica</h1>")
    
    # 1. Verificar parâmetros de threshold
    output.append("<h2>Parâmetros de Threshold</h2>")
    try:
        params = ParametroIndexacao.objects.filter(nome__contains='THRESHOLD')
        if params:
            output.append("<ul>")
            for param in params:
                valor_original = param.valor
                valor_convertido = param.valor_convertido()
                output.append(f"<li><strong>{param.nome}</strong> (em {param.categoria}): {valor_original} (convertido: {valor_convertido})</li>")
            output.append("</ul>")
        else:
            output.append("<p>Nenhum parâmetro de threshold encontrado</p>")
    except Exception as e:
        output.append(f"<p>Erro ao verificar parâmetros: {str(e)}</p>")
    
    # 2. Testar busca com threshold forçado
    query = request.GET.get('q', 'altura')
    feira_id = request.GET.get('feira_id', '1')
    threshold = float(request.GET.get('threshold', '0.4'))
    
    output.append(f"<h2>Teste de Busca: '{query}'</h2>")
    output.append(f"<p>Feira ID: {feira_id}, Threshold forçado: {threshold}</p>")
    
    try:
        # Gerar embedding
        embedding_service = EmbeddingService()
        embedding = embedding_service.gerar_embedding_consulta(query)
        
        if embedding:
            output.append(f"<p>✓ Embedding gerado com {len(embedding)} dimensões</p>")
            
            # Obter namespace
            try:
                feira = Feira.objects.get(pk=feira_id)
                namespace = None
                
                # Tentar diferentes métodos para obter o namespace
                if hasattr(feira, 'get_chunks_namespace'):
                    namespace = feira.get_chunks_namespace()
                    output.append(f"<p>Usando namespace de chunks: '{namespace}'</p>")
                elif hasattr(feira, 'get_qa_namespace'):
                    namespace = feira.get_qa_namespace()
                    output.append(f"<p>Usando namespace de QA: '{namespace}'</p>")
                else:
                    # Tentar formato padrão
                    namespace = f"feira_chunks_{feira_id}"
                    output.append(f"<p>Usando namespace padrão: '{namespace}'</p>")
                
                if namespace:
                    # Verificar se namespace existe
                    stats = get_namespace_stats(namespace)
                    if stats and stats.get('exists'):
                        output.append(f"<p>✓ Namespace '{namespace}' contém {stats.get('vector_count')} vetores</p>")
                        
                        # Realizar consulta
                        filter_obj = {"feira_id": {"$eq": str(feira_id)}} if feira_id else None
                        output.append(f"<p>Filtro: {filter_obj}</p>")
                        
                        results = query_vectors(embedding, namespace, 5, filter_obj)
                        
                        if results:
                            output.append(f"<p>✓ Consulta retornou {len(results)} resultados</p>")
                            
                            # Tabela de resultados
                            output.append("<table border='1' style='width:100%; border-collapse: collapse;'>")
                            output.append("<tr><th>ID</th><th>Score</th><th>Passa com 0.7?</th><th>Passa com 0.4?</th><th>Metadados</th></tr>")
                            
                            for i, result in enumerate(results):
                                score = result['score']
                                
                                # Verificar se passaria com diferentes thresholds
                                passa_default = "✓" if score >= 0.7 else "✗"
                                passa_teste = "✓" if score >= threshold else "✗"
                                
                                # Limitar preview de metadados
                                metadata = result.get('metadata', {})
                                metadata_preview = str(metadata)[:100] + '...' if len(str(metadata)) > 100 else str(metadata)
                                
                                row_class = ""
                                if score >= 0.7:
                                    row_class = "style='background-color: #d4edda;'"  # Verde claro
                                elif score >= threshold:
                                    row_class = "style='background-color: #fff3cd;'"  # Amarelo claro
                                
                                output.append(f"<tr {row_class}><td>{result['id']}</td><td>{score:.4f}</td><td>{passa_default}</td><td>{passa_teste}</td><td>{metadata_preview}</td></tr>")
                            
                            output.append("</table>")
                            
                            # Resumo e recomendação
                            passed_0_7 = sum(1 for r in results if r['score'] >= 0.7)
                            passed_0_4 = sum(1 for r in results if r['score'] >= threshold)
                            
                            output.append(f"<p><strong>Resumo:</strong> {passed_0_7}/{len(results)} resultados passam com threshold 0.7, {passed_0_4}/{len(results)} passam com threshold {threshold}</p>")
                            
                            if passed_0_7 == 0 and passed_0_4 > 0:
                                output.append(f"<p><strong>Diagnóstico:</strong> O threshold atual (0.7) é muito alto para os scores obtidos. Recomendado: {threshold}</p>")
                            elif passed_0_7 > 0:
                                output.append("<p><strong>Diagnóstico:</strong> O threshold atual (0.7) permite alguns resultados. Verifique se são suficientes.</p>")
                            else:
                                output.append("<p><strong>Diagnóstico:</strong> Nenhum resultado passa pelos thresholds. Considere reduzir ainda mais ou verificar os dados.</p>")
                            
                        else:
                            output.append("<p>✗ Consulta não retornou resultados</p>")
                    else:
                        output.append(f"<p>✗ Namespace '{namespace}' não existe ou está vazio</p>")
                else:
                    output.append("<p>✗ Não foi possível determinar o namespace</p>")
                    
            except Exception as e:
                import traceback
                output.append(f"<p>Erro ao processar feira: {str(e)}</p>")
                output.append(f"<pre>{traceback.format_exc()}</pre>")
        else:
            output.append("<p>✗ Falha ao gerar embedding</p>")
            
    except Exception as e:
        import traceback
        output.append(f"<p>Erro no teste de busca: {str(e)}</p>")
        output.append(f"<pre>{traceback.format_exc()}</pre>")
    
    # Formulário para testes adicionais
    output.append("""
    <h2>Testar outra consulta</h2>
    <form method="get">
        <label>Query: <input type="text" name="q" value="{}"></label>
        <label>Feira ID: <input type="text" name="feira_id" value="{}"></label>
        <label>Threshold: <input type="text" name="threshold" value="{}"></label>
        <button type="submit">Testar</button>
    </form>
    """.format(query, feira_id, threshold))
    
    return HttpResponse("\n".join(output))