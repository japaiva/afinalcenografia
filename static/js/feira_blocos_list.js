document.addEventListener("DOMContentLoaded", function() {
  // Obter ID da feira
  const feiraId = document.querySelector('[data-feira-id]').dataset.feiraId;
  
  // Elementos do modal de edição
  const editChunkModal = document.getElementById('editChunkModal');
  const editChunkForm = document.getElementById('editChunkForm');
  const editChunkId = document.getElementById('editChunkId');
  const editTexto = document.getElementById('editTexto');
  const editPagina = document.getElementById('editPagina');
  const editPosicao = document.getElementById('editPosicao');
  const saveChunkBtn = document.getElementById('saveChunkBtn');
  
  // Elementos do modal de adição
  const addBlocoModal = document.getElementById('addBlocoModal');
  const addBlocoForm = document.getElementById('addBlocoForm');
  const addTexto = document.getElementById('addTexto');
  const addPagina = document.getElementById('addPagina');
  const addPosicao = document.getElementById('addPosicao');
  const saveNewChunkBtn = document.getElementById('saveNewChunkBtn');
  
  // Elementos do modal de exclusão
  const deleteChunkModal = document.getElementById('deleteChunkModal');
  const confirmDeleteChunkBtn = document.getElementById('confirmDeleteChunkBtn');
  let chunkIdToDelete = null;
  
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
  
  // Botões de edição de chunk
  const editChunkButtons = document.querySelectorAll('.edit-chunk');
  editChunkButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      const chunkId = this.getAttribute('data-id');
      
      // Buscar dados do chunk via AJAX
      fetch(`/gestor/feiras/chunk/get/?id=${chunkId}`)
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Preencher o modal
            editChunkId.value = chunkId;
            editTexto.value = data.chunk.texto;
            editPagina.value = data.chunk.pagina || '';
            editPosicao.value = data.chunk.posicao;
            
            // Abrir o modal
            const modal = new bootstrap.Modal(editChunkModal);
            modal.show();
          } else {
            alert('Erro ao carregar dados: ' + data.message);
          }
        })
        .catch(error => {
          console.error('Erro na requisição:', error);
          alert('Erro ao carregar dados do chunk.');
        });
    });
  });
  
  // Botão de salvar edição
  if (saveChunkBtn) {
    saveChunkBtn.addEventListener('click', function() {
      const chunkId = editChunkId.value;
      const texto = editTexto.value.trim();
      const pagina = editPagina.value ? parseInt(editPagina.value) : null;
      const posicao = parseInt(editPosicao.value);
      const regenerateVector = document.getElementById('regenerateVector').checked;
      
      // Validar campos obrigatórios
      if (!texto || isNaN(posicao)) {
        alert('Texto e posição são campos obrigatórios.');
        return;
      }
      
      // Obter token CSRF
      const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
      
      // Enviar dados via AJAX
      fetch('/gestor/feiras/chunk/update/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrftoken,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          chunk_id: chunkId,
          texto: texto,
          pagina: pagina,
          posicao: posicao,
          regenerate_vector: regenerateVector
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // Fechar modal e recarregar a página
          bootstrap.Modal.getInstance(editChunkModal).hide();
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
  
  // Botão para adicionar novo chunk
  if (saveNewChunkBtn) {
    saveNewChunkBtn.addEventListener('click', function() {
      const texto = addTexto.value.trim();
      const pagina = addPagina.value ? parseInt(addPagina.value) : null;
      const posicao = parseInt(addPosicao.value);
      
      // Validar campos obrigatórios
      if (!texto || isNaN(posicao)) {
        alert('Texto e posição são campos obrigatórios.');
        return;
      }
      
      // Obter token CSRF
      const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
      
      // Enviar dados via AJAX
      fetch(`/gestor/feiras/${feiraId}/chunk/add/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrftoken,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          texto: texto,
          pagina: pagina,
          posicao: posicao
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // Fechar modal e recarregar a página
          bootstrap.Modal.getInstance(addBlocoModal).hide();
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
  
  // Botões de exclusão
  const deleteChunkButtons = document.querySelectorAll('.delete-chunk');
  deleteChunkButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      chunkIdToDelete = this.getAttribute('data-id');
      
      // Abrir modal de confirmação
      const modal = new bootstrap.Modal(deleteChunkModal);
      modal.show();
    });
  });
  
  // Botão de confirmar exclusão
  if (confirmDeleteChunkBtn) {
    confirmDeleteChunkBtn.addEventListener('click', function() {
      if (!chunkIdToDelete) return;
      
      // Obter token CSRF
      const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
      
      // Enviar requisição para excluir
      fetch('/gestor/feiras/chunk/delete/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrftoken,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          chunk_id: chunkIdToDelete
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // Fechar modal e recarregar a página
          bootstrap.Modal.getInstance(deleteChunkModal).hide();
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
  
  // Botões para regenerar vetor
  const regenerateVectorButtons = document.querySelectorAll('.regenerate-vector');
  regenerateVectorButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      const chunkId = this.getAttribute('data-id');
      
      if (confirm('Deseja regenerar o vetor deste bloco no banco vetorial?')) {
        // Obter token CSRF
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // Enviar requisição para regenerar vetor
        fetch('/gestor/feiras/chunk/regenerate-vector/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            chunk_id: chunkId
          })
        })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            alert('Vetor regenerado com sucesso!');
          } else {
            alert('Erro ao regenerar vetor: ' + data.message);
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