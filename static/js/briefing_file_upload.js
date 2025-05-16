// briefing-file-upload.js
// Sistema unificado de uploads para todas as etapas do briefing

/**
 * Classe para gerenciar uploads de arquivos no briefing
 * Oferece funcionalidades consistentes para todas as etapas
 */
class BriefingFileUploader {
    /**
     * Inicializa o gerenciador de uploads
     * @param {Object} config - Configuração do uploader
     * @param {string} config.csrfToken - Token CSRF para requisições POST
     * @param {string} config.uploadUrl - URL base para upload de arquivos
     * @param {number} config.projetoId - ID do projeto atual
     */
    constructor(config) {
        this.csrfToken = config.csrfToken;
        this.uploadUrl = config.uploadUrl;
        this.projetoId = config.projetoId;
        this.uploadForms = [];
        this.fileTypes = {
            'mapa': { icon: 'fa-map', name: 'Mapa do Estande', allowMultiple: false },
            'planta': { icon: 'fa-drafting-compass', name: 'Planta/Esboço', allowMultiple: false },
            'referencia': { icon: 'fa-image', name: 'Referência Visual', allowMultiple: true },
            'campanha': { icon: 'fa-ad', name: 'Material de Campanha', allowMultiple: true },
            'logo': { icon: 'fa-trademark', name: 'Logotipo', allowMultiple: true },
            'imagem': { icon: 'fa-image', name: 'Imagem', allowMultiple: true },
            'outro': { icon: 'fa-file', name: 'Outro Material', allowMultiple: true }
        };
    }

    /**
     * Adiciona um formulário de upload para ser gerenciado
     * @param {Object} form - Configuração do formulário
     * @param {string} form.formId - ID do elemento form ou container
     * @param {string} form.fileInputId - ID do input type=file
     * @param {string} form.uploadBtnId - ID do botão de upload
     * @param {string} form.previewContainerId - ID do container para preview
     * @param {string} form.fileType - Tipo de arquivo (mapa, planta, referencia, etc)
     * @param {string} form.observacoesValue - Valor padrão para observações (opcional)
     */
    addUploadForm(form) {
        this.uploadForms.push(form);
        this.initUploadForm(form);
    }

    /**
     * Inicializa os eventos para um formulário de upload
     * @param {Object} form - Configuração do formulário
     */
    initUploadForm(form) {
        const fileInput = document.getElementById(form.fileInputId);
        const uploadBtn = document.getElementById(form.uploadBtnId);
        const previewContainer = document.getElementById(form.previewContainerId);
        const fileType = form.fileType;

        if (!fileInput || !uploadBtn) {
            console.error(`Elementos não encontrados para o formulário ${form.formId}`);
            return;
        }

        // Adiciona evento para preview do arquivo antes do upload
        fileInput.addEventListener('change', (e) => {
            this.handleFileInputChange(e, form);
        });

        // Adiciona evento para o botão de upload
        uploadBtn.addEventListener('click', () => {
            this.handleUpload(form);
        });

        // Adiciona evento para exclusão de arquivos (delegado ao container)
        if (previewContainer) {
            previewContainer.addEventListener('click', (e) => {
                const deleteBtn = e.target.closest('.excluir-arquivo');
                if (deleteBtn) {
                    const arquivoId = deleteBtn.dataset.id;
                    const url = deleteBtn.dataset.url;
                    this.handleDeleteFile(url, arquivoId, deleteBtn.closest('.arquivo-item'));
                }
            });
        }
    }

    /**
     * Manipula a mudança no input de arquivo para mostrar preview
     * @param {Event} e - Evento de change
     * @param {Object} form - Configuração do formulário
     */
    handleFileInputChange(e, form) {
        const fileInput = e.target;
        const previewContainer = document.getElementById(form.previewContainerId + '-temp') || 
                               document.getElementById(form.previewContainerId);
        
        // Se não existir container de preview temporário, criar um
        if (!document.getElementById(form.previewContainerId + '-temp')) {
            const tempPreview = document.createElement('div');
            tempPreview.id = form.previewContainerId + '-temp';
            tempPreview.className = 'file-preview-temp mt-2 border p-2 rounded';
            document.getElementById(form.formId).appendChild(tempPreview);
        }

        const tempPreviewContainer = document.getElementById(form.previewContainerId + '-temp');
        
        // Verificar se um arquivo foi selecionado
        if (fileInput.files && fileInput.files[0]) {
            const file = fileInput.files[0];
            const fileName = file.name;
            const fileSize = (file.size / 1024).toFixed(2) + ' KB';
            const fileType = form.fileType;
            const fileTypeInfo = this.fileTypes[fileType] || this.fileTypes.outro;
            
            // Estrutura base do preview
            let previewHTML = `
                <div class="d-flex align-items-center">
                    <i class="fas ${fileTypeInfo.icon} text-primary me-2"></i>
                    <span class="me-2">${fileName} (${fileSize})</span>
                    <span class="badge bg-info">Selecionado - Não salvo</span>
                </div>
            `;
            
            // Se for uma imagem, adicionar miniatura
            const fileExtension = fileName.split('.').pop().toLowerCase();
            if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(fileExtension)) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    tempPreviewContainer.innerHTML = previewHTML + `
                        <div class="mt-2">
                            <img src="${e.target.result}" alt="Miniatura" class="img-thumbnail" style="max-height: 150px;">
                        </div>
                    `;
                };
                reader.readAsDataURL(file);
            } else {
                tempPreviewContainer.innerHTML = previewHTML;
            }
        }
    }

    /**
     * Realiza o upload do arquivo
     * @param {Object} form - Configuração do formulário
     */
    handleUpload(form) {
        const fileInput = document.getElementById(form.fileInputId);
        const fileType = form.fileType;
        const previewContainer = document.getElementById(form.previewContainerId);
        
        if (fileInput.files.length === 0) {
            alert('Selecione um arquivo para upload');
            return;
        }


        const formData = new FormData();
        formData.append('arquivo', fileInput.files[0]);
        formData.append('tipo', fileType);
        formData.append('nome', fileInput.files[0].name);
        formData.append('observacoes', form.observacoesValue || `Arquivo ${this.fileTypes[fileType].name}`);
        formData.append('csrfmiddlewaretoken', this.csrfToken);

        console.log('📤 Upload de arquivo - conteúdo do FormData:');
        for (let pair of formData.entries()) {
            console.log(`🧾 ${pair[0]}:`, pair[1]);
        }
        
        // URL do endpoint de upload
        const url = this.uploadUrl.replace('0', this.projetoId);
        
        // Mostrar indicador de carregamento
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'text-center my-2';
        loadingIndicator.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Carregando...</span></div>';
        document.getElementById(form.formId).appendChild(loadingIndicator);
        
        fetch(url, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            // Remover indicador de carregamento
            loadingIndicator.remove();
            
            if (data.success) {
                // Limpar preview temporário
                const tempPreview = document.getElementById(form.previewContainerId + '-temp');
                if (tempPreview) {
                    tempPreview.remove();
                }
                
                // Se não permitir múltiplos, limpar container primeiro
                const fileTypeInfo = this.fileTypes[fileType] || this.fileTypes.outro;
                if (!fileTypeInfo.allowMultiple) {
                    // Remover arquivos existentes do mesmo tipo
                    const existingFiles = previewContainer.querySelectorAll(`.arquivo-item[data-tipo="${fileType}"]`);
                    existingFiles.forEach(el => el.remove());
                }
                
                // Adicionar arquivo para o container
                this.addFilePreview(previewContainer, data.arquivo, fileType);
                
                // Limpar input de arquivo
                fileInput.value = '';
                
                // Notificar usuário
                this.showNotification('Arquivo enviado com sucesso!', 'success');
            } else {
                // Exibir erro
                this.showNotification(`Erro ao enviar arquivo: ${data.message || 'Erro desconhecido'}`, 'danger');
            }
        })
        .catch(error => {
            // Remover indicador de carregamento
            loadingIndicator.remove();
            
            // Exibir erro
            this.showNotification(`Erro ao enviar arquivo: ${error}`, 'danger');
        });
    }

    /**
     * Adiciona o preview de um arquivo ao container
     * @param {HTMLElement} container - Container para adicionar o preview
     * @param {Object} arquivo - Dados do arquivo
     * @param {string} fileType - Tipo de arquivo
     */
    addFilePreview(container, arquivo, fileType) {
        const fileExtension = arquivo.nome.split('.').pop().toLowerCase();
        const isImage = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(fileExtension);
        const fileTypeInfo = this.fileTypes[fileType] || this.fileTypes.outro;
        
        const arquivoItem = document.createElement('div');
        arquivoItem.className = 'position-relative arquivo-item me-2 mb-2';
        arquivoItem.dataset.id = arquivo.id;
        arquivoItem.dataset.tipo = fileType;
        
        // Se for imagem, mostrar thumbnail
        if (isImage) {
            arquivoItem.innerHTML = `
                <div class="card" style="width: 150px;">
                    <img src="${arquivo.url}" alt="${arquivo.nome}" class="card-img-top" style="height: 100px; object-fit: cover;">
                    <div class="card-body p-2">
                        <p class="card-text small text-truncate">${arquivo.nome}</p>
                        <div class="btn-group btn-group-sm">
                            <a href="${arquivo.url}" target="_blank" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-eye"></i>
                            </a>
                            <button type="button" class="btn btn-sm btn-outline-danger excluir-arquivo" data-id="${arquivo.id}" 
                                data-url="${this.getDeleteUrl(arquivo.id)}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        } else {
            // Para outros tipos de arquivo, mostrar ícone
            arquivoItem.innerHTML = `
                <div class="card" style="width: 150px;">
                    <div class="text-center pt-3" style="height: 100px;">
                        <i class="fas ${fileTypeInfo.icon} fa-3x text-primary"></i>
                    </div>
                    <div class="card-body p-2">
                        <p class="card-text small text-truncate">${arquivo.nome}</p>
                        <div class="btn-group btn-group-sm">
                            <a href="${arquivo.url}" target="_blank" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-download"></i>
                            </a>
                            <button type="button" class="btn btn-sm btn-outline-danger excluir-arquivo" data-id="${arquivo.id}"
                                data-url="${this.getDeleteUrl(arquivo.id)}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }
        
        container.appendChild(arquivoItem);
    }

    /**
     * Manipula a exclusão de um arquivo
     * @param {string} url - URL para excluir o arquivo
     * @param {number} arquivoId - ID do arquivo
     * @param {HTMLElement} element - Elemento a ser removido após exclusão
     */
    handleDeleteFile(url, arquivoId, element) {
        if (confirm('Tem certeza que deseja excluir este arquivo?')) {
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Remover elemento da UI
                    element.remove();
                    this.showNotification('Arquivo excluído com sucesso!', 'success');
                } else {
                    this.showNotification(`Erro ao excluir arquivo: ${data.message || 'Erro desconhecido'}`, 'danger');
                }
            })
            .catch(error => {
                this.showNotification(`Erro ao excluir arquivo: ${error}`, 'danger');
            });
        }
    }

    /**
     * Obtém a URL para exclusão de um arquivo
     * @param {number} arquivoId - ID do arquivo
     * @returns {string} URL para exclusão
     */
    getDeleteUrl(arquivoId) {
        // Adaptar conforme a estrutura de URLs da sua aplicação
        return `/briefing/excluir-arquivo/${arquivoId}/`;
    }

    /**
     * Exibe uma notificação temporária ao usuário
     * @param {string} message - Mensagem a ser exibida
     * @param {string} type - Tipo de notificação (success, danger, warning, info)
     */
    showNotification(message, type = 'info') {
        // Verificar se já existe um container de notificações
        let notificationContainer = document.getElementById('notification-container');
        
        // Se não existir, criar um
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.id = 'notification-container';
            notificationContainer.className = 'position-fixed bottom-0 end-0 p-3';
            notificationContainer.style.zIndex = '9999';
            document.body.appendChild(notificationContainer);
        }
        
        // Criar notificação
        const notification = document.createElement('div');
        notification.className = `toast align-items-center text-white bg-${type} border-0`;
        notification.role = 'alert';
        notification.ariaLive = 'assertive';
        notification.ariaAtomic = 'true';
        
        notification.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
            </div>
        `;
        
        notificationContainer.appendChild(notification);
        
        // Inicializar o toast do Bootstrap
        const toast = new bootstrap.Toast(notification, {
            delay: 3000,
            autohide: true
        });
        
        // Mostrar notificação
        toast.show();
        
        // Remover após fechar
        notification.addEventListener('hidden.bs.toast', function() {
            notification.remove();
        });
    }
}

// Exportar para uso em outros arquivos
window.BriefingFileUploader = BriefingFileUploader;