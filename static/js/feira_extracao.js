// static/js/feira_extracao.js

document.addEventListener('DOMContentLoaded', function() {
    const extractDataBtn = document.getElementById('extractDataBtn');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    if (extractDataBtn) {
        extractDataBtn.addEventListener('click', function() {
            // Obter ID da feira do atributo data
            const feiraId = document.getElementById('feiraForm').dataset.feiraId;
            
            if (!feiraId) {
                console.error('ID da feira não encontrado');
                showAlert('Erro', 'ID da feira não encontrado.', 'danger');
                return;
            }
            
            // Mostrar modal de extração
            const modal = new bootstrap.Modal(document.getElementById('ragExtractionModal'));
            modal.show();
            
            // Atualizar status
            updateExtractionStatus('Consultando as perguntas e respostas...', 10);
            
            // Fazer requisição para extrair dados
            fetch(`/gestor/feiras/${feiraId}/extrair-dados/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                // Atualizar status
                updateExtractionStatus('Processando resultados...', 50);
                
                if (data.status === 'success') {
                    // Mostrar resultados após um breve delay
                    setTimeout(() => {
                        updateExtractionStatus('Extração concluída com sucesso!', 100, 'success');
                        showExtractionResults(data.data);
                    }, 500);
                } else {
                    // Mostrar erro
                    showExtractionError(data.message || 'Erro ao extrair dados.');
                }
            })
            .catch(error => {
                console.error('Erro na extração:', error);
                showExtractionError('Erro ao comunicar com o servidor.');
            });
        });
        
        // Evento para o botão de aplicar resultados
        document.getElementById('applyRagResultsBtn').addEventListener('click', function() {
            const feiraId = document.getElementById('feiraForm').dataset.feiraId;
            const selectedData = getSelectedExtractionData();
            
            if (Object.keys(selectedData).length === 0) {
                showAlert('Aviso', 'Nenhum campo selecionado para aplicação.', 'warning');
                return;
            }
            
            // Atualizar status
            updateExtractionStatus('Aplicando dados ao formulário...', 60);
            
            // Enviar dados selecionados para aplicação
            fetch(`/gestor/feiras/${feiraId}/aplicar-dados/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    campos: selectedData
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Aplicar valores diretamente aos campos do formulário
                    updateFormFields(selectedData);
                    
                    updateExtractionStatus('Dados aplicados com sucesso!', 100, 'success');
                    
                    // Fechar modal após breve delay
                    setTimeout(() => {
                        bootstrap.Modal.getInstance(document.getElementById('ragExtractionModal')).hide();
                        showAlert('Sucesso', data.message, 'success');
                    }, 1500);
                } else {
                    showExtractionError(data.message || 'Erro ao aplicar dados.');
                }
            })
            .catch(error => {
                console.error('Erro ao aplicar dados:', error);
                showExtractionError('Erro ao comunicar com o servidor.');
            });
        });
    }
    
    // Funções auxiliares
    
    function updateExtractionStatus(message, progress, type = 'info') {
        const statusText = document.getElementById('ragStatusText');
        const progressBar = document.getElementById('ragProgressBar');
        const statusDiv = document.getElementById('ragExtractionStatus');
        
        // Atualizar mensagem e progresso
        statusText.textContent = message;
        progressBar.style.width = `${progress}%`;
        
        // Atualizar tipo de alerta
        statusDiv.className = `alert alert-${type}`;
    }
    
    function showExtractionResults(data) {
        const resultsDiv = document.getElementById('ragExtractionResults');
        const resultsTable = document.getElementById('ragResultsTable');
        const applyBtn = document.getElementById('applyRagResultsBtn');
        
        // Limpar tabela
        resultsTable.innerHTML = '';
        
        // Adicionar resultados à tabela
        for (const [campo, info] of Object.entries(data)) {
            const row = document.createElement('tr');
            
            // Criar célula para checkbox e nome do campo
            const cellField = document.createElement('td');
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'form-check';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'form-check-input me-2 extraction-field-checkbox';
            checkbox.dataset.field = campo;
            checkbox.checked = true;
            checkbox.id = `check-${campo}`;
            
            const fieldLabel = document.createElement('label');
            fieldLabel.className = 'form-check-label';
            fieldLabel.htmlFor = `check-${campo}`;
            fieldLabel.appendChild(document.createTextNode(formatFieldName(campo)));
            
            checkboxDiv.appendChild(checkbox);
            checkboxDiv.appendChild(fieldLabel);
            
            cellField.appendChild(checkboxDiv);
            
            // Criar célula para valor extraído
            const cellValue = document.createElement('td');
            cellValue.innerHTML = `
                <div class="mb-1">${info.valor}</div>
                <div class="small text-muted">
                    <i class="fas fa-question-circle me-1"></i> Pergunta: ${info.pergunta || ''}
                </div>
                <div class="small">
                    <div class="progress" style="height: 5px;">
                        <div class="progress-bar ${getConfidenceColorClass(info.confianca)}" 
                             role="progressbar" 
                             style="width: ${Math.round(info.confianca * 100)}%;" 
                             aria-valuenow="${Math.round(info.confianca * 100)}" 
                             aria-valuemin="0" 
                             aria-valuemax="100"></div>
                    </div>
                    <span class="small ${getConfidenceTextClass(info.confianca)}">
                        Confiança: ${Math.round(info.confianca * 100)}%
                    </span>
                </div>
            `;
            
            // Adicionar células à linha
            row.appendChild(cellField);
            row.appendChild(cellValue);
            
            // Adicionar linha à tabela
            resultsTable.appendChild(row);
        }
        
        // Mostrar resultados e botão de aplicar
        resultsDiv.classList.remove('d-none');
        applyBtn.classList.remove('d-none');
    }
    
    function showExtractionError(message) {
        const errorDiv = document.getElementById('ragExtractionError');
        
        // Mostrar mensagem de erro
        errorDiv.textContent = message;
        errorDiv.classList.remove('d-none');
        
        // Esconder resultados se estiverem visíveis
        document.getElementById('ragExtractionResults').classList.add('d-none');
        
        // Esconder botão de aplicar
        document.getElementById('applyRagResultsBtn').classList.add('d-none');
        
        // Atualizar status
        updateExtractionStatus('Ocorreu um erro na extração.', 100, 'danger');
    }
    
    function getSelectedExtractionData() {
        const selectedData = {};
        const checkboxes = document.querySelectorAll('.extraction-field-checkbox:checked');
        
        // Para cada checkbox selecionado, obter campo e valor
        checkboxes.forEach(checkbox => {
            const campo = checkbox.dataset.field;
            const row = checkbox.closest('tr');
            const valorCell = row.querySelector('td:nth-child(2)');
            // Obter apenas o texto principal, não os detalhes
            const valor = valorCell.querySelector('div:first-child').textContent;
            
            selectedData[campo] = valor;
        });
        
        return selectedData;
    }
    
    function updateFormFields(data) {
        // Para cada campo selecionado, atualizar o valor no formulário
        for (const [campo, valor] of Object.entries(data)) {
            const input = document.querySelector(`#id_${campo}`);
            
            if (input) {
                if (input.type === 'checkbox') {
                    // Converter valor para booleano
                    input.checked = ['true', 'sim', 'yes', '1'].includes(valor.toLowerCase());
                } else {
                    input.value = valor;
                }
            }
        }
    }

    function formatFieldName(campo) {
        // Mapeamento de nomes de campos
        const fieldMap = {
            'nome': 'Nome da Feira',
            'descricao': 'Descrição do Evento',
            'website': 'Site da Feira',
            'local': 'Local/Endereço',
            'data_horario': 'Data e Horário',
            'publico_alvo': 'Público-alvo',
            'eventos_simultaneos': 'Eventos Simultâneos',
            'promotora': 'Promotora/Organizadora',
            'periodo_montagem': 'Período Montagem',
            'portao_acesso': 'Portão de Acesso',
            'periodo_desmontagem': 'Período Desmontagem',
            'altura_estande': 'Altura Estande',
            'palcos': 'Regras para Palcos',
            'piso_elevado': 'Regras para Piso Elevado',
            'mezanino': 'Regras para Mezanino',
            'iluminacao': 'Regras para Iluminação',
            'materiais_permitidos_proibidos': 'Materiais Permitidos/Proibidos',
            'visibilidade_obrigatoria': 'Visibilidade Obrigatória',
            'paredes_vidro': 'Paredes de Vidro',
            'estrutura_aerea': 'Estrutura Aérea',
            'documentos': 'Documentos para Credenciamento',
            'credenciamento': 'Datas Credenciamento'
        };
        
        return fieldMap[campo] || campo.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    function getConfidenceColorClass(confianca) {
        if (confianca >= 0.8) return 'bg-success';
        if (confianca >= 0.6) return 'bg-info';
        if (confianca >= 0.4) return 'bg-warning';
        return 'bg-danger';
    }
    
    function getConfidenceTextClass(confianca) {
        if (confianca >= 0.8) return 'text-success';
        if (confianca >= 0.6) return 'text-info';
        if (confianca >= 0.4) return 'text-warning';
        return 'text-danger';
    }
    
    function showAlert(title, message, type) {
        // Criar elemento toast
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            const newContainer = document.createElement('div');
            newContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(newContainer);
        }
        
        // Use a variável já existente ou a recém-criada sem declarar novamente
        const toastId = 'toast-' + Date.now();
        
        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header bg-${type} text-white">
                    <strong class="me-auto">${title}</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        // Use document.querySelector novamente ou a variável já existente
        document.querySelector('.toast-container').insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
        toast.show();
        
        // Remover toast após fechamento
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });
    }
});