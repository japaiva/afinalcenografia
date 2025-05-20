// static/js/conceito_visual.js

// Função para gerar conceito textual - mantendo sua implementação existente
function gerarConceitoTextual(projetoId) {
    const loadingElement = document.getElementById('loading-conceito');
    const resultadoElement = document.getElementById('resultado-conceito');
    
    loadingElement.style.display = 'block';
    resultadoElement.style.display = 'none';
    
    fetch(`/projetista/conceito/${projetoId}/gerar-conceito-ia/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        loadingElement.style.display = 'none';
        
        if (data.success) {
            toastr.success('Conceito gerado com sucesso!');
            // Redirecionar ou atualizar a página
            window.location.reload();
        } else {
            toastr.error(`Erro: ${data.message}`);
        }
    })
    .catch(error => {
        loadingElement.style.display = 'none';
        toastr.error('Erro ao comunicar com o servidor');
        console.error('Erro:', error);
    });
}

// Função para gerar imagem principal - implementação completa
function gerarImagemPrincipal(conceitoId, anguloVista) {
    const loadingElement = document.getElementById('loading-imagem');
    const previewElement = document.getElementById('preview-imagem');
    
    // Definir ângulo padrão se não for especificado
    if (!anguloVista) {
        anguloVista = 'perspectiva';
    }
    
    loadingElement.style.display = 'block';
    if (previewElement) previewElement.style.display = 'none';
    
    // Desabilitar botão para evitar cliques múltiplos
    const botao = document.querySelector('button[onclick*="gerarImagemPrincipal"]');
    if (botao) botao.disabled = true;
    
    // Criar FormData para enviar parâmetros
    const formData = new FormData();
    formData.append('angulo_vista', anguloVista);
    
    // Obter instruções adicionais do campo de texto, se existir
    const instrucoesElement = document.getElementById('instrucoes_adicionais');
    if (instrucoesElement && instrucoesElement.value) {
        formData.append('instrucoes_adicionais', instrucoesElement.value);
    }
    
    fetch(`/projetista/conceito/${conceitoId}/gerar-imagem-ia/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        loadingElement.style.display = 'none';
        
        if (data.success) {
            toastr.success('Imagem gerada com sucesso!');
            
            // Mostrar preview se disponível
            if (data.image_url && previewElement) {
                previewElement.innerHTML = `<img src="${data.image_url}" class="img-fluid rounded shadow" alt="Imagem gerada">`;
                previewElement.style.display = 'block';
            }
            
            // Redirecionar ou recarregar após 2 segundos
            setTimeout(() => {
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    window.location.reload();
                }
            }, 2000);
        } else {
            if (botao) botao.disabled = false;
            toastr.error(`Erro: ${data.message || 'Não foi possível gerar a imagem.'}`);
        }
    })
    .catch(error => {
        loadingElement.style.display = 'none';
        if (botao) botao.disabled = false;
        toastr.error('Erro ao comunicar com o servidor');
        console.error('Erro:', error);
    });
}

// Função para gerar múltiplas vistas - implementação completa
function gerarMultiplasVistas(conceitoId) {
    const loadingElement = document.getElementById('loading-vistas');
    
    loadingElement.style.display = 'block';
    
    // Desabilitar botão para evitar cliques múltiplos
    const botao = document.querySelector('button[onclick*="gerarMultiplasVistas"]');
    if (botao) botao.disabled = true;
    
    // Obter ângulos selecionados
    const angulosSelecionados = [];
    document.querySelectorAll('input[name="vistas[]"]:checked').forEach(checkbox => {
        angulosSelecionados.push(checkbox.value);
    });
    
    // Se nenhum ângulo selecionado, selecionar padrões
    if (angulosSelecionados.length === 0) {
        angulosSelecionados.push('frontal', 'lateral_esquerda', 'interior');
    }
    
    // Criar FormData para enviar parâmetros
    const formData = new FormData();
    angulosSelecionados.forEach(angulo => {
        formData.append('vistas[]', angulo);
    });
    
    // Obter instruções adicionais do campo de texto, se existir
    const instrucoesElement = document.getElementById('instrucoes_adicionais_vistas');
    if (instrucoesElement && instrucoesElement.value) {
        formData.append('instrucoes_adicionais', instrucoesElement.value);
    }
    
    fetch(`/projetista/conceito/${conceitoId}/gerar-vistas-ia/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        loadingElement.style.display = 'none';
        
        if (data.success) {
            toastr.success('Vistas geradas com sucesso!');
            
            // Redirecionar ou recarregar após 2 segundos
            setTimeout(() => {
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    window.location.reload();
                }
            }, 2000);
        } else {
            if (botao) botao.disabled = false;
            toastr.error(`Erro: ${data.message || 'Não foi possível gerar as vistas.'}`);
        }
    })
    .catch(error => {
        loadingElement.style.display = 'none';
        if (botao) botao.disabled = false;
        toastr.error('Erro ao comunicar com o servidor');
        console.error('Erro:', error);
    });
}

// Função para modificar imagem existente - nova função
function modificarImagem(imagemId) {
    const loadingElement = document.getElementById('loading-modificacao');
    const previewElement = document.getElementById('preview-modificacao');
    
    // Obter texto de instruções
    const instrucoesElement = document.getElementById('instrucoes_modificacao');
    if (!instrucoesElement || !instrucoesElement.value.trim()) {
        toastr.warning('Por favor, descreva as modificações desejadas.');
        return;
    }
    
    loadingElement.style.display = 'block';
    if (previewElement) previewElement.style.display = 'none';
    
    // Desabilitar botão para evitar cliques múltiplos
    const botao = document.querySelector('button[onclick*="modificarImagem"]');
    if (botao) botao.disabled = true;
    
    // Criar FormData para enviar parâmetros
    const formData = new FormData();
    formData.append('instrucoes_modificacao', instrucoesElement.value);
    
    // Verificar se há um tipo de modificação selecionado
    const tipoModificacaoElement = document.querySelector('input[name="tipo_modificacao"]:checked');
    if (tipoModificacaoElement) {
        formData.append('tipo_modificacao', tipoModificacaoElement.value);
    }
    
    fetch(`/projetista/conceito/imagem/${imagemId}/modificar-ia/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        loadingElement.style.display = 'none';
        
        if (data.success) {
            toastr.success('Imagem modificada com sucesso!');
            
            // Mostrar preview se disponível
            if (data.image_url && previewElement) {
                previewElement.innerHTML = `
                    <div class="comparison-container">
                        <div class="comparison-item">
                            <h6>Imagem Original</h6>
                            <img src="${data.original_url}" class="img-fluid rounded shadow" alt="Imagem original">
                        </div>
                        <div class="comparison-item">
                            <h6>Imagem Modificada</h6>
                            <img src="${data.image_url}" class="img-fluid rounded shadow" alt="Imagem modificada">
                        </div>
                    </div>
                `;
                previewElement.style.display = 'block';
            }
            
            // Redirecionar ou recarregar após 3 segundos
            setTimeout(() => {
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    window.location.reload();
                }
            }, 3000);
        } else {
            if (botao) botao.disabled = false;
            toastr.error(`Erro: ${data.message || 'Não foi possível modificar a imagem.'}`);
        }
    })
    .catch(error => {
        loadingElement.style.display = 'none';
        if (botao) botao.disabled = false;
        toastr.error('Erro ao comunicar com o servidor');
        console.error('Erro:', error);
    });
}

// Função para visualizar imagem em tamanho completo - nova função útil
function visualizarImagemCompleta(url, titulo) {
    // Criar modal dinamicamente
    const modalId = 'modalVisualizacaoImagem';
    let modal = document.getElementById(modalId);
    
    // Se o modal não existir, criar
    if (!modal) {
        const modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="${modalId}Label">Visualização da Imagem</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                        </div>
                        <div class="modal-body text-center">
                            <img src="" class="img-fluid" alt="Visualização completa" id="${modalId}Img">
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Adicionar ao body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        modal = document.getElementById(modalId);
    }
    
    // Atualizar imagem e título
    const modalImg = document.getElementById(`${modalId}Img`);
    modalImg.src = url;
    
    const modalTitle = modal.querySelector('.modal-title');
    modalTitle.textContent = titulo || 'Visualização da Imagem';
    
    // Abrir modal
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// Função auxiliar para obter o token CSRF - mantendo sua implementação existente
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Função para marcar/desmarcar todos os checkboxes de vistas - nova função útil
function toggleCheckboxesVistas(marcar) {
    document.querySelectorAll('input[name="vistas[]"]').forEach(checkbox => {
        checkbox.checked = marcar;
    });
}

// Inicialização quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Inicializar configuração do Toastr
    if (typeof toastr !== 'undefined') {
        toastr.options = {
            "closeButton": true,
            "progressBar": true,
            "positionClass": "toast-top-right",
            "showDuration": "300",
            "hideDuration": "1000",
            "timeOut": "5000",
            "extendedTimeOut": "1000",
            "showEasing": "swing",
            "hideEasing": "linear",
            "showMethod": "fadeIn",
            "hideMethod": "fadeOut"
        };
    }
});