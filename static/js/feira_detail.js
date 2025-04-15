document.addEventListener('DOMContentLoaded', function() {
    // Elementos do formulário de processamento manual
    const processManualForm = document.getElementById('process-manual-form');
    const processManualButton = document.getElementById('process-manual-button');
    
    // Elementos do formulário de processamento QA
    const processQAForm = document.getElementById('process-qa-form');
    const processQAButton = document.getElementById('process-qa-button');
    
    // Elementos de status
    const manualStatus = document.getElementById('manual-status');
    const qaStatus = document.getElementById('qa-status');
    const qaCount = document.getElementById('qa-count');
    const progressText = document.getElementById('progress-text');
    const progressContainer = document.getElementById('progress-container');
    
    // Obter o ID da feira
    function getFeiraId() {
      // Primeiro tentar pegar do atributo data
      const feiraCard = document.querySelector('[data-feira-id]');
      if (feiraCard && feiraCard.dataset.feiraId) {
        return feiraCard.dataset.feiraId;
      }
      
      // Tentar obter da URL
      const url = window.location.pathname;
      const parts = url.split('/').filter(part => part !== '');
      if (parts.length >= 3 && (parts[1] === 'feiras' || parts[1] === 'feira')) {
        return parts[2];
      }
      
      return null;
    }
    
    const feiraId = getFeiraId();
    if (!feiraId) {
      console.error('Não foi possível determinar o ID da feira');
      return;
    }
    
    console.log(`Monitorando feira ID: ${feiraId}`);
    
    // Flags para controlar verificações
    let isCheckingManual = false;
    let isCheckingQA = false;
    let lastProgress = 0;
    
    // Função para verificar o status do processamento do manual
    function checkManualStatus() {
      if (isCheckingManual) return; // Evitar chamadas simultâneas
      
      isCheckingManual = true;
      fetch(`/gestor/feira/${feiraId}/progress/`, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(response => response.json())
      .then(data => {
        isCheckingManual = false;
        
        if (data.success) {
          // Atualizar status do manual
          updateManualStatus(data);
          
          // Atualizar contagem de QA se disponível
          if (qaCount && data.qa_count !== undefined) {
            qaCount.textContent = data.qa_count;
            
            // Se temos QAs, atualizar o status de QA para concluído
            if (data.qa_count > 0 && qaStatus) {
              qaStatus.className = 'badge bg-success';
              qaStatus.textContent = 'Concluído';
              
              // Habilitar botão de regenerar QA
              if (processQAButton) {
                processQAButton.disabled = false;
                processQAButton.innerHTML = '<i class="fas fa-comment-dots me-1"></i> Regenerar Q&A';
              }
            }
          }
          
          // Atualizar texto de progresso se mudou
          if (progressText && typeof data.progress !== 'undefined' && data.progress !== lastProgress) {
            lastProgress = data.progress;
            progressText.textContent = `Processando manual... (${data.progress}%)`;
            
            if (progressContainer) {
              progressContainer.classList.remove('d-none');
            }
          }
          
          // Se o manual ainda está em processamento, continuar verificando
          if (data.status === 'processando') {
            setTimeout(checkManualStatus, 3000);
          } 
          // Se o manual foi concluído
          else if (data.status === 'concluido' && data.processed) {
            console.log('Processamento do manual concluído');
            
            // Ocultar mensagem de progresso
            if (progressContainer) {
              progressContainer.classList.add('d-none');
            }
            
            // Habilitar botão do manual
            if (processManualButton) {
              processManualButton.disabled = false;
              processManualButton.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Reprocessar Manual';
            }
            
            // Habilitar botão de QA
            if (processQAButton) {
              processQAButton.disabled = false;
              processQAButton.innerHTML = '<i class="fas fa-comment-dots me-1"></i> Gerar Q&A';
            }
            
            // Recarregar a página para mostrar o card de consulta ao manual
            window.location.reload();
          } 
          // Se ocorreu erro ou está pendente
          else {
            // Habilitar botão do manual
            if (processManualButton) {
              processManualButton.disabled = false;
              processManualButton.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Processar Manual';
            }
          }
        } else {
          console.error('Erro ao verificar status do manual:', data.error);
          
          // Habilitar botão em caso de erro
          if (processManualButton) {
            processManualButton.disabled = false;
            processManualButton.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Processar Manual';
          }
        }
      })
      .catch(error => {
        isCheckingManual = false;
        console.error('Erro ao verificar status do manual:', error);
        
        // Habilitar botão em caso de erro
        if (processManualButton) {
          processManualButton.disabled = false;
          processManualButton.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Processar Manual';
        }
      });
    }
    
    // Função para verificar o status do processamento de QA
    function checkQAStatus() {
      if (isCheckingQA) return; // Evitar chamadas simultâneas
      
      isCheckingQA = true;
      fetch(`/gestor/feiras/${feiraId}/qa/progress/`, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(response => {
        // Verificar se a resposta é bem-sucedida
        if (!response.ok) {
          throw new Error('API de progresso de QA não disponível');
        }
        return response.json();
      })
      .then(data => {
        isCheckingQA = false;
        
        if (data.success) {
          console.log('Status QA:', data);
          
          // Atualizar contagem de QA se disponível
          if (qaCount && data.total_qa !== undefined) {
            qaCount.textContent = data.total_qa;
          }
          
          // Atualizar status de QA
          if (qaStatus) {
            if (data.status === 'processando') {
              qaStatus.className = 'badge bg-warning text-dark';
              qaStatus.textContent = 'Processando';
            } else if (data.processed || data.total_qa > 0) {
              qaStatus.className = 'badge bg-success';
              qaStatus.textContent = 'Concluído';
            } else if (data.status === 'erro') {
              qaStatus.className = 'badge bg-danger';
              qaStatus.textContent = 'Erro';
            } else {
              qaStatus.className = 'badge bg-secondary';
              qaStatus.textContent = 'Pendente';
            }
          }
          
          // Se ainda estiver processando, continuar verificando
          if (data.status === 'processando') {
            setTimeout(checkQAStatus, 3000);
          } else {
            // Processamento concluído ou erro, habilitar botão
            if (processQAButton) {
              processQAButton.disabled = false;
              processQAButton.innerHTML = '<i class="fas fa-comment-dots me-1"></i> Regenerar Q&A';
            }
            
            // Recarregar a página para mostrar o botão "Ver Q&A" se necessário
            if (data.total_qa > 0) {
              window.location.reload();
            }
          }
        } else {
          console.error('Erro ao verificar status QA:', data.error);
          
          // Erro na API, habilitar botão
          if (processQAButton) {
            processQAButton.disabled = false;
            processQAButton.innerHTML = '<i class="fas fa-comment-dots me-1"></i> Gerar Q&A';
          }
        }
      })
      .catch(error => {
        isCheckingQA = false;
        console.error('Erro ao verificar status QA:', error);
        
        // Erro na API, verificar o status manualmente via contagem de QA
        fetch(`/gestor/feira/${feiraId}/progress/`, {
          method: 'GET',
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
        .then(response => response.json())
        .then(data => {
          if (data.success && data.qa_count > 0) {
            // Temos QAs, então o processamento foi concluído
            if (qaStatus) {
              qaStatus.className = 'badge bg-success';
              qaStatus.textContent = 'Concluído';
            }
            
            if (qaCount) {
              qaCount.textContent = data.qa_count;
            }
            
            if (processQAButton) {
              processQAButton.disabled = false;
              processQAButton.innerHTML = '<i class="fas fa-comment-dots me-1"></i> Regenerar Q&A';
            }
            
            // Recarregar para mostrar o botão "Ver Q&A"
            window.location.reload();
          } else {
            // Nenhum QA, habilitar botão
            if (processQAButton) {
              processQAButton.disabled = false;
              processQAButton.innerHTML = '<i class="fas fa-comment-dots me-1"></i> Gerar Q&A';
            }
          }
        });
      });
    }
    
    // Funções auxiliares para atualizar a UI
    function updateManualStatus(data) {
      if (!manualStatus) return;
      
      // Atualizar classe e texto do badge
      if (data.status === 'processando') {
        manualStatus.className = 'badge bg-warning text-dark';
        manualStatus.textContent = 'Processando';
      } else if (data.status === 'concluido' && data.processed) {
        manualStatus.className = 'badge bg-success';
        manualStatus.textContent = 'Concluído';
        
        // Ocultar mensagem de progresso quando concluído
        if (progressContainer) {
          progressContainer.classList.add('d-none');
        }
      } else if (data.status === 'erro') {
        manualStatus.className = 'badge bg-danger';
        manualStatus.textContent = 'Erro';
        
        // Ocultar mensagem de progresso em caso de erro
        if (progressContainer) {
          progressContainer.classList.add('d-none');
        }
      } else {
        manualStatus.className = 'badge bg-secondary';
        manualStatus.textContent = 'Pendente';
      }
    }
    
    // Iniciar a verificação com base no status atual
    function startStatusChecking() {
      // Verificar ambos os status iniciais
      if (manualStatus && manualStatus.textContent.trim() === 'Processando') {
        console.log('Iniciando verificação: status do Manual em Processando');
        if (processManualButton) {
          processManualButton.disabled = true;
          processManualButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Processando...';
        }
        checkManualStatus();
      }
      
      if (qaStatus && qaStatus.textContent.trim() === 'Processando') {
        console.log('Iniciando verificação: status do QA em Processando');
        if (processQAButton) {
          processQAButton.disabled = true;
          processQAButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Processando...';
        }
        checkQAStatus();
      }
    }
    
    // Iniciar verificação ao carregar a página
    startStatusChecking();
    
    // Adicionar event listener para o formulário de processamento manual
    if (processManualForm) {
      processManualForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Desabilitar botão e atualizar UI
        if (processManualButton) {
          processManualButton.disabled = true;
          processManualButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Processando...';
        }
        
        if (manualStatus) {
          manualStatus.className = 'badge bg-warning text-dark';
          manualStatus.textContent = 'Processando';
        }
        
        // Enviar requisição para iniciar processamento
        fetch(this.action, {
          method: 'POST',
          body: new FormData(this),
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
        .then(response => {
          // Tentar analisar como JSON, mas lidar com respostas não-JSON também
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            return response.json().then(data => ({ isJson: true, data, status: response.status }));
          } else {
            return response.text().then(text => ({ isJson: false, text, status: response.status }));
          }
        })
        .then(result => {
          if ((result.isJson && result.data.success) || (!result.isJson && result.status >= 200 && result.status < 300)) {
            // Iniciar verificação de status
            console.log('Processamento do manual iniciado com sucesso, iniciando verificação de status');
            setTimeout(() => {
              checkManualStatus();
            }, 2000);
          } else {
            // Mostrar erro
            console.error('Erro ao iniciar processamento do manual:', result);
            if (processManualButton) {
              processManualButton.disabled = false;
              processManualButton.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Tentar Novamente';
            }
            
            if (manualStatus) {
              manualStatus.className = 'badge bg-danger';
              manualStatus.textContent = 'Erro';
            }
          }
        })
        .catch(error => {
          console.error('Erro:', error);
          
          if (processManualButton) {
            processManualButton.disabled = false;
            processManualButton.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Tentar Novamente';
          }
          
          if (manualStatus) {
            manualStatus.className = 'badge bg-danger';
            manualStatus.textContent = 'Erro';
          }
        });
      });
    }
    
    // Adicionar event listener para o formulário de processamento QA
    if (processQAForm) {
      processQAForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Desabilitar botão e atualizar UI
        if (processQAButton) {
          processQAButton.disabled = true;
          processQAButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Processando...';
        }
        
        if (qaStatus) {
          qaStatus.className = 'badge bg-warning text-dark';
          qaStatus.textContent = 'Processando';
        }
        
        // Enviar requisição para iniciar processamento de QA
        fetch(this.action, {
          method: 'POST',
          body: new FormData(this),
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
        .then(response => {
          // Tentar analisar como JSON, mas lidar com respostas não-JSON também
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            return response.json().then(data => ({ isJson: true, data, status: response.status }));
          } else {
            return response.text().then(text => ({ isJson: false, text, status: response.status }));
          }
        })
        .then(result => {
          if ((result.isJson && result.data.success) || (!result.isJson && result.status >= 200 && result.status < 300)) {
            // Iniciar verificação de status
            console.log('Processamento de QA iniciado com sucesso, iniciando verificação de status');
            setTimeout(() => {
              checkQAStatus();
            }, 2000);
          } else {
            // Mostrar erro
            console.error('Erro ao iniciar processamento de QA:', result);
            if (processQAButton) {
              processQAButton.disabled = false;
              processQAButton.innerHTML = '<i class="fas fa-comment-dots me-1"></i> Tentar Novamente';
            }
            
            if (qaStatus) {
              qaStatus.className = 'badge bg-danger';
              qaStatus.textContent = 'Erro';
            }
          }
        })
        .catch(error => {
          console.error('Erro:', error);
          
          if (processQAButton) {
            processQAButton.disabled = false;
            processQAButton.innerHTML = '<i class="fas fa-comment-dots me-1"></i> Tentar Novamente';
          }
          
          if (qaStatus) {
            qaStatus.className = 'badge bg-danger';
            qaStatus.textContent = 'Erro';
          }
        });
      });
    }
    
    // NOVO CÓDIGO: Formulário de busca no manual
    const manualSearchForm = document.getElementById('manualSearchForm');
    const manualSearchQuery = document.getElementById('manualSearchQuery');
    const manualSearchResults = document.getElementById('manualSearchResults');
    const manualSearchLoading = document.getElementById('manualSearchLoading');
    const manualSearchError = document.getElementById('manualSearchError');
    const searchResponseContainer = document.getElementById('searchResponseContainer');
    const searchContextsContainer = document.getElementById('searchContextsContainer');
    const searchContextsList = document.getElementById('searchContextsList');
    
    if (manualSearchForm) {
      manualSearchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const query = manualSearchQuery.value.trim();
        if (!query) {
          manualSearchError.textContent = "Por favor, digite uma pergunta para consultar o manual.";
          manualSearchError.classList.remove('d-none');
          return;
        }
        
        // Resetar a interface
        manualSearchError.classList.add('d-none');
        manualSearchResults.classList.add('d-none');
        manualSearchLoading.classList.remove('d-none');
        
        // Obter token CSRF
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // Fazer a requisição para a API
        fetch('/gestor/briefing/responder-pergunta/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
          },
          body: JSON.stringify({
            pergunta: query,
            feira_id: feiraId,
            agente_nome: 'Assistente RAG de Feiras'  // Nome do agente configurado
          })
        })
        .then(response => response.json())
        .then(data => {
          // Ocultar loading
          manualSearchLoading.classList.add('d-none');
          
          if (data.success) {
            // Mostrar resultados
            searchResponseContainer.innerHTML = data.resposta.replace(/\n/g, '<br>');
            
            // Exibir contextos se disponíveis
            if (data.contextos && data.contextos.length > 0) {
              searchContextsList.innerHTML = '';
              
              data.contextos.forEach((ctx, index) => {
                const contextDiv = document.createElement('div');
                contextDiv.className = 'mb-3 p-2 border-start border-info border-3 ps-3';
                
                const scoreSpan = document.createElement('span');
                scoreSpan.className = 'badge bg-info float-end';
                scoreSpan.textContent = `Relevância: ${(ctx.score * 100).toFixed(0)}%`;
                
                const questionHeader = document.createElement('p');
                questionHeader.className = 'mb-1 fw-bold';
                questionHeader.textContent = `${index + 1}. ${ctx.question}`;
                
                const answerContent = document.createElement('p');
                answerContent.className = 'text-muted small';
                answerContent.textContent = ctx.answer;
                
                contextDiv.appendChild(scoreSpan);
                contextDiv.appendChild(questionHeader);
                contextDiv.appendChild(answerContent);
                
                searchContextsList.appendChild(contextDiv);
              });
              
              searchContextsContainer.classList.remove('d-none');
            } else {
              searchContextsContainer.classList.add('d-none');
            }
            
            manualSearchResults.classList.remove('d-none');
          } else {
            // Mostrar erro
            manualSearchError.textContent = data.message || "Não foi possível processar a consulta.";
            manualSearchError.classList.remove('d-none');
          }
        })
        .catch(error => {
          console.error('Erro ao consultar:', error);
          manualSearchLoading.classList.add('d-none');
          manualSearchError.textContent = "Erro ao processar a requisição. Tente novamente.";
          manualSearchError.classList.remove('d-none');
        });
      });
    }
  });