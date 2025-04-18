document.addEventListener("DOMContentLoaded", function() {
  // Função para preservar parâmetros de busca na paginação
  function updatePaginationLinks() {
    const queryParam = new URLSearchParams(window.location.search).get('q');
    const modeParam = new URLSearchParams(window.location.search).get('mode');
    
    document.querySelectorAll('.pagination .page-link').forEach(link => {
      if (link.href.includes('page=')) {
        // Preservar parâmetro de busca
        const url = new URL(link.href);
        if (queryParam) {
          url.searchParams.set('q', queryParam);
        }
        
        // Preservar modo de busca
        if (modeParam) {
          url.searchParams.set('mode', modeParam);
        }
        
        link.href = url.toString();
      }
    });
  }
  
  // Chamar a função quando a página carregar
  updatePaginationLinks();
  
  // Polling para atualização do progresso se estiver processando
  if (document.getElementById('progressBar')) {
    function atualizarProgresso() {
      const feiraId = document.querySelector('[data-feira-id]').dataset.feiraId;
      
      // CORRIGIDO: URL para o endpoint progress
      fetch(`/gestor/feiras/${feiraId}/qa/progress/`)
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Atualizar barra de progresso
            const progressBar = document.getElementById('progressBar');
            const progress = Math.round((data.total_qa / data.expected_qa) * 100);
            progressBar.style.width = progress + '%';
            progressBar.setAttribute('aria-valuenow', progress);
            progressBar.innerText = progress + '%';
            
            // Verificar se o processamento foi concluído
            if (data.processed || data.status === 'concluido') {
              // Recarregar a página quando concluir
              location.reload();
            } else {
              // Continuar atualizando se ainda estiver processando
              setTimeout(atualizarProgresso, 2000);
            }
          } else {
            console.error('Erro ao buscar progresso:', data.error);
            setTimeout(atualizarProgresso, 5000);
          }
        })
        .catch(error => {
          console.error('Erro na requisição:', error);
          setTimeout(atualizarProgresso, 5000);
        });
    }
    
    // Iniciar o monitoramento quando a página carregar
    setTimeout(atualizarProgresso, 1000);
  }
  
  // Botão de regenerar todas as perguntas e respostas
  const regenerateBtn = document.getElementById('regenerateBtn');
  if (regenerateBtn) {
    regenerateBtn.addEventListener('click', function() {
      const regenerateModal = new bootstrap.Modal(document.getElementById('regenerateAllModal'));
      regenerateModal.show();
    });
  }
  
  // Botão de confirmar regeneração
  const confirmRegenerateBtn = document.getElementById('confirmRegenerateBtn');
  if (confirmRegenerateBtn) {
    confirmRegenerateBtn.addEventListener('click', function() {
      // Fechar o modal
      bootstrap.Modal.getInstance(document.getElementById('regenerateAllModal')).hide();
      
      const feiraId = document.querySelector('[data-feira-id]').dataset.feiraId;
      
      // Enviar requisição para regenerar
      fetch(`/gestor/feiras/${feiraId}/qa/regenerate/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/json'
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // Recarregar a página após iniciar regeneração
          location.reload();
        } else {
          // Exibir erro
          alert('Erro ao iniciar regeneração: ' + data.message);
        }
      })
      .catch(error => {
        console.error('Erro na requisição:', error);
        alert('Erro ao processar requisição.');
      });
    });
  }
  
  // Botão para adicionar novo QA
  const saveNewQABtn = document.getElementById('saveNewQABtn');
  if (saveNewQABtn) {
    saveNewQABtn.addEventListener('click', function() {
      const question = document.getElementById('addQuestion').value.trim();
      const answer = document.getElementById('addAnswer').value.trim();
      const context = document.getElementById('addContext').value.trim();
      const similarQuestionsText = document.getElementById('addSimilarQuestions').value.trim();
      
      // Validar campos obrigatórios
      if (!question || !answer) {
        alert('Pergunta e resposta são campos obrigatórios.');
        return;
      }
      
      // Converter perguntas similares para array
      const similarQuestions = similarQuestionsText
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);
      
      const feiraId = document.querySelector('[data-feira-id]').dataset.feiraId;
      
      // CORRIGIDO: URL para o endpoint de adicionar QA
      fetch(`/gestor/feiras/${feiraId}/qa/add/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          question: question,
          answer: answer,
          context: context,
          similar_questions: similarQuestions
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // Fechar modal e recarregar página
          bootstrap.Modal.getInstance(document.getElementById('addQAModal')).hide();
          location.reload();
        } else {
          alert('Erro ao adicionar: ' + data.message);
        }
      })
      .catch(error => {
        console.error('Erro na requisição:', error);
        alert('Erro ao processar requisição.');
      });
    });
  }
  
  // Botões de edição
  const editButtons = document.querySelectorAll('.edit-qa');
  editButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      const qaId = this.getAttribute('data-id');
      
      // Buscar dados do QA via AJAX
      fetch(`/gestor/feiras/qa/get/?id=${qaId}`)
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Preencher o modal
            document.getElementById('editQAId').value = qaId;
            document.getElementById('editQuestion').value = data.qa.question;
            document.getElementById('editAnswer').value = data.qa.answer;
            document.getElementById('editContext').value = data.qa.context;
            
            // Preencher perguntas similares
            const similarQuestions = Array.isArray(data.qa.similar_questions) 
              ? data.qa.similar_questions.join('\n') 
              : '';
            document.getElementById('editSimilarQuestions').value = similarQuestions;
            
            // Abrir o modal
            const editModal = new bootstrap.Modal(document.getElementById('editQAModal'));
            editModal.show();
          } else {
            alert('Erro ao carregar dados: ' + data.message);
          }
        })
        .catch(error => {
          console.error('Erro na requisição:', error);
          alert('Erro ao carregar dados.');
        });
    });
  });
  
  // Botão de salvar edição
  const saveQABtn = document.getElementById('saveQABtn');
  if (saveQABtn) {
    saveQABtn.addEventListener('click', function() {
      const form = document.getElementById('editQAForm');
      const qaId = document.getElementById('editQAId').value;
      const question = document.getElementById('editQuestion').value;
      const answer = document.getElementById('editAnswer').value;
      const context = document.getElementById('editContext').value;
      const similarQuestionsText = document.getElementById('editSimilarQuestions').value;
      
      // Converter perguntas similares para array
      const similarQuestions = similarQuestionsText
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);
      
      // Enviar dados via AJAX
      fetch('/gestor/feiras/qa/update/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          qa_id: qaId,
          question: question,
          answer: answer,
          context: context,
          similar_questions: similarQuestions,
          atualizar_embedding: true // Adicionar opção para atualizar embedding sempre que editar
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // Fechar modal e recarregar a página
          bootstrap.Modal.getInstance(document.getElementById('editQAModal')).hide();
          location.reload();
        } else {
          alert('Erro ao salvar: ' + data.message);
        }
      })
      .catch(error => {
        console.error('Erro na requisição:', error);
        alert('Erro ao processar requisição.');
      });
    });
  }
  
  // Botões de exclusão
  const deleteButtons = document.querySelectorAll('.delete-qa');
  let qaIdToDelete = null;
  
  deleteButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      qaIdToDelete = this.getAttribute('data-id');
      
      // Abrir modal de confirmação
      const deleteModal = new bootstrap.Modal(document.getElementById('deleteQAModal'));
      deleteModal.show();
    });
  });
  
  // Botão de confirmar exclusão
  const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener('click', function() {
      if (!qaIdToDelete) return;
      
      // Enviar requisição para excluir
      fetch('/gestor/feiras/qa/delete/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          qa_id: qaIdToDelete
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // Fechar modal e recarregar a página
          bootstrap.Modal.getInstance(document.getElementById('deleteQAModal')).hide();
          location.reload();
        } else {
          alert('Erro ao excluir: ' + data.message);
        }
      })
      .catch(error => {
        console.error('Erro na requisição:', error);
        alert('Erro ao processar requisição.');
      });
    });
  }
  
  // Botões de regenerar QA individual
  const regenerateQAButtons = document.querySelectorAll('.regenerate-qa');
  regenerateQAButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      const qaId = this.getAttribute('data-id');
      
      if (confirm('Deseja regenerar esta pergunta e resposta?')) {
        // Enviar requisição para regenerar
        fetch('/gestor/feiras/qa/regenerate-single/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            qa_id: qaId
          })
        })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Recarregar a página
            location.reload();
          } else {
            alert('Erro ao regenerar: ' + data.message);
          }
        })
        .catch(error => {
          console.error('Erro na requisição:', error);
          alert('Erro ao processar requisição.');
        });
      }
    });
  });
});