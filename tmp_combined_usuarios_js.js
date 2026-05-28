
        // Variável para armazenar o ID do usuário selecionado
        let usuarioAtualSelecionado = null;

        // Abrir modal e preencher informações do usuário
        document.querySelectorAll('.btn-add-documento').forEach(btn => {
            btn.addEventListener('click', function() {
                usuarioAtualSelecionado = this.dataset.userId;
                const nomeUsuario = this.dataset.userName;
                
                document.getElementById('usuarioDocumento').value = nomeUsuario;
                document.getElementById('documentoNome').value = '';
                document.getElementById('documentoArquivo').value = '';
                document.getElementById('documentoDescricao').value = '';
                document.getElementById('progressContainer').style.display = 'none';
                document.getElementById('progressBar').style.width = '0%';
            });
        });

        // Ao selecionar arquivo, mostrar seu nome
        document.getElementById('documentoArquivo').addEventListener('change', function(e) {
            if (this.files.length > 0) {
                const arquivo = this.files[0];
                const tamanhoMB = (arquivo.size / (1024 * 1024)).toFixed(2);
                console.log(`Arquivo selecionado: ${arquivo.name} (${tamanhoMB}MB)`);
            }
        });

        // Função para obter CSRF token
        function getCsrfToken() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            return (meta && meta.getAttribute('content')) || '';
        }

        // Botão salvar documento
        document.getElementById('btnSalvarDocumento').addEventListener('click', async function() {
            const nome = document.getElementById('documentoNome').value.trim();
            const descricao = document.getElementById('documentoDescricao').value.trim();
            const arquivo = document.getElementById('documentoArquivo').files[0];

            // Validações
            if (!nome) {
                alert('Por favor, preencha o nome do documento.');
                return;
            }

            if (!arquivo) {
                alert('Por favor, selecione um arquivo.');
                return;
            }

            if (!usuarioAtualSelecionado) {
                alert('Erro: usuário não identificado.');
                return;
            }

            // Validar tamanho (10MB)
            const tamanhoMaxMB = 10;
            if (arquivo.size > tamanhoMaxMB * 1024 * 1024) {
                alert(`Arquivo muito grande. Máximo: ${tamanhoMaxMB}MB`);
                return;
            }

            // Desabilitar botão e mostrar progresso
            const btnSalvar = document.getElementById('btnSalvarDocumento');
            btnSalvar.disabled = true;
            document.getElementById('progressContainer').style.display = 'block';

            // Preparar FormData
            const formData = new FormData();
            formData.append('arquivo', arquivo);
            formData.append('nome', nome);
            formData.append('descricao', descricao);

            try {
                const response = await fetch(`/admin/usuarios/${usuarioAtualSelecionado}/documentos/upload`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    // Animar progresso
                    let progress = 0;
                    const interval = setInterval(() => {
                        progress += Math.random() * 30;
                        if (progress > 90) progress = 90;
                        document.getElementById('progressBar').style.width = progress + '%';
                    }, 200);

                    setTimeout(() => {
                        clearInterval(interval);
                        document.getElementById('progressBar').style.width = '100%';
                        
                        // Fechar modal após sucesso
                        setTimeout(() => {
                            const modal = bootstrap.Modal.getInstance(document.getElementById('documentoModal'));
                            if (modal) modal.hide();
                            
                            // Mostrar notificação
                            const alertDiv = document.createElement('div');
                            alertDiv.className = 'alert alert-success alert-dismissible fade show';
                            alertDiv.setAttribute('role', 'alert');
                            alertDiv.innerHTML = `
                                <i class="fas fa-check-circle"></i> <strong>Sucesso!</strong> ${data.message}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
                            `;
                            document.querySelector('.container-fluid').insertBefore(alertDiv, document.querySelector('.card'));
                            
                            // Remover alerta após 5 segundos
                            setTimeout(() => alertDiv.remove(), 5000);

                            // Atualizar a página para mostrar o botão de documentos quando for o primeiro upload
                            setTimeout(() => window.location.reload(), 1200);
                        }, 500);
                    }, 1500);
                } else {
                    alert('Erro: ' + data.message);
                    document.getElementById('progressContainer').style.display = 'none';
                    document.getElementById('progressBar').style.width = '0%';
                }
            } catch (error) {
                console.error('Erro ao enviar arquivo:', error);
                alert('Erro ao enviar arquivo: ' + error.message);
                document.getElementById('progressContainer').style.display = 'none';
                document.getElementById('progressBar').style.width = '0%';
            } finally {
                btnSalvar.disabled = false;
            }
        });
    


        let usuarioSelecionadoItens = null;
        let usuarioSelecionadoDocumentos = null;
        let previewDocumentoObjectUrl = null;

        // Abrir modal de itens recebidos
        document.querySelectorAll('.btn-itens-recebidos').forEach(btn => {
            btn.addEventListener('click', async function() {
                usuarioSelecionadoItens = this.dataset.userId;
                const nomeUsuario = this.dataset.userName;
                
                document.getElementById('itensRecebidosModalLabel').textContent = `Itens Recebidos - ${nomeUsuario}`;
                
                await carregarItensRecebidos(usuarioSelecionadoItens);
            });
        });

        document.getElementById('btnCriarRelatorioItens').addEventListener('click', function() {
            if (!usuarioSelecionadoItens) {
                alert('Selecione um usuário primeiro.');
                return;
            }

            window.open(`/admin/usuarios/${usuarioSelecionadoItens}/itens-recebidos/relatorio`, '_blank');
        });

        document.querySelectorAll('.btn-documentos').forEach(btn => {
            btn.addEventListener('click', async function() {
                usuarioSelecionadoDocumentos = this.dataset.userId;
                const nomeUsuario = this.dataset.userName;

                document.getElementById('documentosModalLabel').innerHTML = `<i class="fas fa-folder-open text-success"></i> Documentos do Usuário - ${nomeUsuario}`;

                await carregarDocumentos(usuarioSelecionadoDocumentos);
            });
        });

        async function carregarItensRecebidos(userId) {
            try {
                const response = await fetch(`/admin/usuarios/${userId}/itens-recebidos`);
                const data = await response.json();

                if (!data.success) {
                    document.getElementById('modalItensBody').innerHTML = `<div class="alert alert-danger">Erro ao carregar itens.</div>`;
                    return;
                }

                let html = '';


                // Itens recebidos na entrada
                html += '<h6 class="mt-4 mb-3"><i class="fas fa-sign-in-alt text-primary"></i> Itens Recebidos na Entrada</h6>';
                if (data.itens_entrada.length > 0) {
                    html += '<div class="list-group">';
                    data.itens_entrada.forEach(item => {
                        html += `
                            <div class="list-group-item d-flex justify-content-between align-items-center" data-item-id="${item.id}">
                                <div class="flex-grow-1">
                                    <p class="mb-1"><strong>${item.descricao_item}</strong></p>
                                    <small class="text-muted">${item.data_criacao}</small>
                                </div>
                                <div class="btn-group" role="group">
                                    <button type="button" class="btn btn-sm btn-outline-danger btn-deletar-item" data-item-id="${item.id}">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        `;
                    });
                    html += '</div>';
                } else {
                    html += '<p class="text-muted">Nenhum item nesta categoria.</p>';
                }

                // Itens recebidos posteriormente
                html += '<h6 class="mt-4 mb-3"><i class="fas fa-plus-circle text-success"></i> Itens Recebidos Posteriormente</h6>';
                if (data.itens_posteriormente.length > 0) {
                    html += '<div class="list-group">';
                    data.itens_posteriormente.forEach(item => {
                        html += `
                            <div class="list-group-item d-flex justify-content-between align-items-center" data-item-id="${item.id}">
                                <div class="flex-grow-1">
                                    <p class="mb-1"><strong>${item.descricao_item}</strong></p>
                                    <small class="text-muted">${item.data_criacao}</small>
                                </div>
                                <div class="btn-group" role="group">
                                    <button type="button" class="btn btn-sm btn-outline-danger btn-deletar-item" data-item-id="${item.id}">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        `;
                    });
                    html += '</div>';
                } else {
                    html += '<p class="text-muted">Nenhum item nesta categoria.</p>';
                }

                document.getElementById('modalItensBody').innerHTML = html;

                // Attach event listeners
                document.querySelectorAll('.btn-deletar-item').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const itemId = this.dataset.itemId;
                        if (confirm('Tem certeza que deseja deletar este item?')) {
                            deletarItem(itemId);
                        }
                    });
                });
            } catch (error) {
                console.error('Erro:', error);
                document.getElementById('modalItensBody').innerHTML = `<div class="alert alert-danger">Erro ao carregar itens: ${error.message}</div>`;
            }
        }

        async function carregarDocumentos(userId) {
            try {
                const response = await fetch(`/admin/usuarios/${userId}/documentos`);
                const data = await response.json();

                if (!data.success) {
                    document.getElementById('modalDocumentosBody').innerHTML = `<div class="alert alert-danger mb-0">Erro ao carregar documentos.</div>`;
                    return;
                }

                let html = '';

                if (data.documentos.length > 0) {
                    html += '<div class="list-group">';
                    data.documentos.forEach(documento => {
                        html += `
                            <div class="list-group-item d-flex justify-content-between align-items-center gap-3">
                                <div class="flex-grow-1">
                                    <p class="mb-1 fw-semibold">${documento.nome_documento}</p>
                                    <small class="text-muted d-block">${documento.data_criacao || ''}</small>
                                    ${documento.descricao ? `<small class="text-muted d-block">${documento.descricao}</small>` : ''}
                                </div>
                                <div class="d-flex flex-column align-items-end gap-2">
                                    <span class="badge bg-secondary text-uppercase">${documento.tipo_arquivo}</span>
                                    <div class="btn-group btn-group-sm" role="group">
                                        ${documento.pode_visualizar ? `<button type="button" class="btn btn-outline-primary btn-visualizar-documento" data-preview-url="${documento.preview_url}" data-download-url="${documento.download_url}" data-documento-nome="${documento.nome_documento}" data-documento-tipo="${documento.tipo_arquivo}"><i class="fas fa-eye"></i></button>` : ''}
                                        <a class="btn btn-outline-success" href="${documento.download_url}">
                                            <i class="fas fa-download"></i>
                                        </a>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    html += '</div>';
                } else {
                    html = '<div class="alert alert-info mb-0">Nenhum documento salvo para este usuário.</div>';
                }

                document.getElementById('modalDocumentosBody').innerHTML = html;

                document.querySelectorAll('.btn-visualizar-documento').forEach(btn => {
                    btn.addEventListener('click', function() {
                        abrirPreviewDocumento(
                            this.dataset.previewUrl,
                            this.dataset.downloadUrl,
                            this.dataset.documentoNome,
                            this.dataset.documentoTipo
                        );
                    });
                });
            } catch (error) {
                console.error('Erro ao carregar documentos:', error);
                document.getElementById('modalDocumentosBody').innerHTML = `<div class="alert alert-danger mb-0">Erro ao carregar documentos: ${error.message}</div>`;
            }
        }

        async function abrirPreviewDocumento(previewUrl, downloadUrl, nomeDocumento, tipoArquivo) {
            const corpo = document.getElementById('previewDocumentoBody');
            const titulo = document.getElementById('previewDocumentoModalLabel');
            const download = document.getElementById('previewDocumentoDownload');

            titulo.innerHTML = `<i class="fas fa-eye text-primary"></i> ${nomeDocumento} <small class="text-muted">(${tipoArquivo})</small>`;
            download.href = downloadUrl || previewUrl;
            corpo.innerHTML = `<div class="d-flex justify-content-center align-items-center p-5" style="min-height: 70vh;"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Carregando...</span></div></div>`;

            if (previewDocumentoObjectUrl) {
                URL.revokeObjectURL(previewDocumentoObjectUrl);
                previewDocumentoObjectUrl = null;
            }

            try {
                const response = await fetch(previewUrl, { credentials: 'same-origin' });
                if (!response.ok) {
                    throw new Error(`Falha ao carregar arquivo (${response.status})`);
                }

                const blob = await response.blob();
                previewDocumentoObjectUrl = URL.createObjectURL(blob);

                const tipo = (tipoArquivo || '').toLowerCase();
                if (['jpg', 'jpeg', 'png', 'gif'].includes(tipo)) {
                    corpo.innerHTML = `<div class="d-flex justify-content-center align-items-center p-3" style="min-height: 70vh;"><img src="${previewDocumentoObjectUrl}" alt="${nomeDocumento}" class="img-fluid" style="max-height: 70vh; object-fit: contain;"></div>`;
                } else if (tipo === 'pdf') {
                    corpo.innerHTML = `<iframe src="${previewDocumentoObjectUrl}" title="${nomeDocumento}" style="width: 100%; height: 70vh; border: 0;"></iframe>`;
                } else {
                    corpo.innerHTML = `<div class="p-4"><div class="alert alert-warning mb-0">Esse tipo de arquivo não tem visualização embutida. Use o botão de download.</div></div>`;
                }
            } catch (error) {
                corpo.innerHTML = `<div class="p-4"><div class="alert alert-danger mb-0">Não foi possível carregar o documento para visualização: ${error.message}</div></div>`;
            }

            const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('previewDocumentoModal'));
            modal.show();
        }

        document.getElementById('previewDocumentoModal').addEventListener('hidden.bs.modal', function() {
            if (previewDocumentoObjectUrl) {
                URL.revokeObjectURL(previewDocumentoObjectUrl);
                previewDocumentoObjectUrl = null;
            }
            document.getElementById('previewDocumentoBody').innerHTML = '';
        });

        async function deletarItem(itemId) {
            try {
                const response = await fetch(`/admin/usuarios/itens-recebidos/${itemId}/deletar`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    }
                });

                const data = await response.json();

                if (data.success) {
                    // Recarregar lista
                    await carregarItensRecebidos(usuarioSelecionadoItens);
                } else {
                    alert('Erro: ' + data.message);
                }
            } catch (error) {
                console.error('Erro:', error);
                alert('Erro ao deletar item: ' + error.message);
            }
        }

        // ==================== Modal de Detalhes do Usuário ====================
        document.querySelectorAll('.user-list-item').forEach(item => {
            item.addEventListener('click', async function(e) {
                const userId = this.dataset.userId;
                await abrirDetalhesUsuario(userId);
            });
        });

        async function abrirDetalhesUsuario(userId) {
            try {
                const response = await fetch(`/api/users/${userId}`);
                const usuario = await response.json();

                // Preencher modal com dados do usuário
                document.getElementById('detalheUsername').textContent = usuario.username;
                document.getElementById('detalheRole').innerHTML = usuario.role === 'admin' 
                    ? '<span class="badge bg-primary">ADMIN</span>' 
                    : '<span class="badge bg-secondary">USUÁRIO</span>';
                document.getElementById('detalheAtivo').innerHTML = usuario.ativo 
                    ? '<span class="badge bg-success">Ativo</span>' 
                    : '<span class="badge bg-danger">Bloqueado</span>';
                
                // Dados gerais
                document.getElementById('detalheArea').textContent = usuario.area || '—';
                document.getElementById('detalheLocalizacao').textContent = usuario.localizacao || '—';
                document.getElementById('detalheDataCriacao').textContent = usuario.data_criacao || '—';
                
                // Dados da empresa
                document.getElementById('detalheEmpresa').textContent = usuario.empresa || '—';
                document.getElementById('detalheCNPJ').textContent = usuario.cnpj || '—';
                document.getElementById('detalheEndereco').textContent = usuario.endereco || '—';
                document.getElementById('detalheCargo').textContent = usuario.cargo || '—';
                document.getElementById('detalheCPF').textContent = usuario.cpf || '—';
                document.getElementById('detalheDataAdmissao').textContent = usuario.data_admissao || '—';
                document.getElementById('detalheDepartamento').textContent = usuario.departamento || '—';
                document.getElementById('detalheLocalTrabalho').textContent = usuario.local_trabalho || '—';
                
                // Abrir modal
                const modal = new bootstrap.Modal(document.getElementById('detalheUsuarioModal'));
                modal.show();

            } catch (error) {
                console.error('Erro ao carregar detalhes:', error);
                alert('Erro ao carregar detalhes do usuário');
            }
        }
    


        // ==================== Modal Termo de Entrega ====================
        let usuarioSelecionadoTermo = null;

        document.querySelectorAll('.btn-termo-entrega').forEach(btn => {
            btn.addEventListener('click', async function() {
                usuarioSelecionadoTermo = this.dataset.userId;
                const nomeUsuario = this.dataset.userName;
                
                document.getElementById('termoEntregaModalLabel').innerHTML = `<i class="fas fa-file-contract"></i> Termo de Entrega - ${nomeUsuario}`;
                
                await carregarTermo(usuarioSelecionadoTermo);
            });
        });

        async function carregarTermo(userId) {
            try {
                const response = await fetch(`/admin/usuarios/${userId}/termo-entrega`);
                const data = await response.json();

                if (!data.success) {
                    document.getElementById('modalTermoBody').innerHTML = `<div class="alert alert-warning">Nenhum termo encontrado. Será criado ao atualizar.</div>`;
                    const btnSalvarTermo = document.getElementById('btnSalvarTermo');
                    const btnGerarAditivo = document.getElementById('btnGerarAditivo');
                    if (btnSalvarTermo) {
                        btnSalvarTermo.style.display = 'inline-block';
                        // If termo lacks PJ fields, try to fetch user to provide them
                        const termo = data.termo;
                        const termoHasPJ = (termo.pj_contratante && termo.pj_contratante.toString().trim() !== '') || (termo.pj_contratada && termo.pj_contratada.toString().trim() !== '');

                        if (!termoHasPJ) {
                            try {
                                const userResp = await fetch(`/api/users/${userId}`);
                                if (userResp.ok) {
                                    const userJson = await userResp.json();
                                    termo.pj_contratante = termo.pj_contratante || userJson.pj_contratante || '';
                                    termo.pj_contratante_cnpj = termo.pj_contratante_cnpj || userJson.pj_contratante_cnpj || '';
                                    termo.pj_contratante_endereco = termo.pj_contratante_endereco || userJson.pj_contratante_endereco || '';
                                    termo.pj_contratada = termo.pj_contratada || userJson.pj_contratada || '';
                                    termo.pj_contratada_cnpj = termo.pj_contratada_cnpj || userJson.pj_contratada_cnpj || '';
                                    termo.pj_data_contrato = termo.pj_data_contrato || userJson.pj_data_contrato || '';
                                    termo.tipo_contrato = termo.tipo_contrato || (userJson.tipo_contrato || '');
                                }
                            } catch (e) {
                                console.warn('Não foi possível buscar dados do usuário para campos PJ:', e);
                            }
                        }

                        const isPJ = ((termo.tipo_contrato || '').toString().toUpperCase() === 'PJ') || (termo.pj_contratante && termo.pj_contratante.toString().trim() !== '') || (termo.pj_contratada && termo.pj_contratada.toString().trim() !== '');

                        // helper para blocos de equipamentos
                        const equipamentosHtml = termo.equipamentos && termo.equipamentos.length > 0 ? `
                            <div class="list-group">
                                ${termo.equipamentos.map(eq => `
                                    <div class="list-group-item d-flex justify-content-between align-items-center" data-eq-id="${eq.id}">
                                        <div class="flex-grow-1">
                                            <p class="mb-1"><strong>${eq.descricao}</strong></p>
                                            <small class="text-muted">
                                                ${eq.marca ? 'Marca: ' + eq.marca : ''} 
                                                ${eq.modelo ? '| Modelo: ' + eq.modelo : ''}
                                                ${eq.estado ? '| Estado: ' + eq.estado : ''}
                                            </small>
                                            ${eq.fotos && eq.fotos.length ? `
                                                <div class="mt-2">
                                                    ${eq.fotos.map(f => `<img src="/static/uploads/termos/${f}" style="max-height:60px; margin-right:6px; border:1px solid #ddd; padding:2px;"/>`).join('')}
                                                </div>
                                            ` : ''}
                                        </div>
                                        <button type="button" class="btn btn-sm btn-outline-danger btn-deletar-equipamento" data-eq-id="${eq.id}">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </div>
                                `).join('')}
                            </div>
                        ` : `<p class="text-muted mb-0">Nenhum equipamento registrado.</p>`;

                        let html = '';

                        if (isPJ) {
                            html = `
                                <div class="card border-start border-primary border-4 mb-3">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0"><i class="fas fa-briefcase text-primary"></i> Informações PJ</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="row mb-3">
                                            <div class="col-md-6">
                                                <label for="pjContratante" class="form-label"><strong>Contratante</strong></label>
                                                <input type="text" class="form-control" id="pjContratante" value="${termo.pj_contratante || ''}" placeholder="Contratante">
                                            </div>
                                            <div class="col-md-6">
                                                <label for="pjContratanteCnpj" class="form-label"><strong>CNPJ do Contratante</strong></label>
                                                <input type="text" class="form-control" id="pjContratanteCnpj" value="${termo.pj_contratante_cnpj || ''}" placeholder="CNPJ do Contratante">
                                            </div>
                                        </div>
                                        <div class="row mb-3">
                                            <div class="col-12">
                                                <label for="pjContratanteEndereco" class="form-label"><strong>Endereço do Contratante</strong></label>
                                                <input type="text" class="form-control" id="pjContratanteEndereco" value="${termo.pj_contratante_endereco || ''}" placeholder="Endereço do Contratante">
                                            </div>
                                        </div>
                                        <div class="row mb-3">
                                            <div class="col-md-6">
                                                <label for="pjContratada" class="form-label"><strong>Contratada</strong></label>
                                                <input type="text" class="form-control" id="pjContratada" value="${termo.pj_contratada || ''}" placeholder="Contratada">
                                            </div>
                                            <div class="col-md-6">
                                                <label for="pjContratadaCnpj" class="form-label"><strong>CNPJ da Contratada</strong></label>
                                                <input type="text" class="form-control" id="pjContratadaCnpj" value="${termo.pj_contratada_cnpj || ''}" placeholder="CNPJ da Contratada">
                                            </div>
                                        </div>
                                        <div class="row">
                                            <div class="col-md-6">
                                                <label for="pjDataContrato" class="form-label"><strong>Data do Contrato</strong></label>
                                                <input type="date" class="form-control" id="pjDataContrato" value="${termo.pj_data_contrato || ''}">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="card border-start border-success border-4 mb-3">
                                    <div class="card-header bg-light d-flex justify-content-between align-items-center">
                                        <h6 class="mb-0"><i class="fas fa-laptop text-success"></i> Equipamentos Entregues</h6>
                                        <button type="button" class="btn btn-sm btn-success" id="btnAdicionarEquipamento">
                                            <i class="fas fa-plus"></i> Adicionar
                                        </button>
                                    </div>
                                    <div class="card-body" id="equipamentosContainer">
                                        ${equipamentosHtml}
                                    </div>
                                </div>

                                <div class="card border-start border-secondary border-4 mb-3">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0"><i class="fas fa-file-alt text-secondary"></i> Observações</h6>
                                    </div>
                                    <div class="card-body">
                                        <textarea class="form-control" id="termoObservacoes" rows="3" placeholder="Adicione observações ou comentários...">${termo.observacoes || ''}</textarea>
                                    </div>
                                </div>

                                <div class="alert ${termo.tem_termo_gerado ? 'alert-success' : 'alert-info'}" role="alert">
                                    <i class="fas ${termo.tem_termo_gerado ? 'fa-check-circle' : 'fa-info-circle'}"></i>
                                    <strong>Status:</strong> ${termo.tem_termo_gerado ? 'Termo já gerado' : 'Ainda não existe termo gerado'}
                                </div>
                            `;

                        } else {
                            html = `
                                <div class="card border-start border-warning border-4 mb-3">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0"><i class="fas fa-building text-warning"></i> Informações da Empresa</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="row mb-3">
                                            <div class="col-md-6">
                                                <label for="termoEmpresa" class="form-label"><strong>Empresa</strong></label>
                                                <input type="text" class="form-control" id="termoEmpresa" value="${termo.empresa || ''}" placeholder="Nome da Empresa">
                                            </div>
                                            <div class="col-md-6">
                                                <label for="termoCNPJ" class="form-label"><strong>CNPJ</strong></label>
                                                <input type="text" class="form-control" id="termoCNPJ" value="${termo.cnpj || ''}" placeholder="00.000.000/0000-00">
                                            </div>
                                        </div>
                                        <div class="row">
                                            <div class="col-12">
                                                <label for="termoEndereco" class="form-label"><strong>Endereço</strong></label>
                                                <input type="text" class="form-control" id="termoEndereco" value="${termo.endereco || ''}" placeholder="Rua, número, complemento...">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="card border-start border-info border-4 mb-3">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0"><i class="fas fa-user text-info"></i> Informações do Colaborador</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="row mb-3">
                                            <div class="col-md-6">
                                                <label for="termoNome" class="form-label"><strong>Nome</strong></label>
                                                <input type="text" class="form-control" id="termoNome" value="${termo.nome_colaborador || ''}" placeholder="Nome do Colaborador" readonly>
                                            </div>
                                            <div class="col-md-6">
                                                <label for="termoCPF" class="form-label"><strong>CPF</strong></label>
                                                <input type="text" class="form-control" id="termoCPF" value="${termo.cpf_cnpj || ''}" placeholder="000.000.000-00">
                                            </div>
                                        </div>
                                        <div class="row mb-3">
                                            <div class="col-md-6">
                                                <label for="termoCargo" class="form-label"><strong>Cargo/Função</strong></label>
                                                <input type="text" class="form-control" id="termoCargo" value="${termo.cargo_funcao || ''}" placeholder="Ex: Analista de TI">
                                            </div>
                                            <div class="col-md-6">
                                                <label for="termoDepartamento" class="form-label"><strong>Departamento</strong></label>
                                                <input type="text" class="form-control" id="termoDepartamento" value="${termo.departamento || ''}" placeholder="Ex: Tecnologia da Informação">
                                            </div>
                                        </div>
                                        <div class="row mb-3">
                                            <div class="col-md-6">
                                                <label for="termoLocal" class="form-label"><strong>Local de Trabalho</strong></label>
                                                <input type="text" class="form-control" id="termoLocal" value="${termo.local_trabalho || ''}" placeholder="Local">
                                            </div>
                                            <div class="col-md-6">
                                                <label for="termoDataAdmissao" class="form-label"><strong>Data de Admissão</strong></label>
                                                <input type="date" class="form-control" id="termoDataAdmissao" value="${termo.data_admissao || ''}">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="card border-start border-success border-4 mb-3">
                                    <div class="card-header bg-light d-flex justify-content-between align-items-center">
                                        <h6 class="mb-0"><i class="fas fa-laptop text-success"></i> Equipamentos Entregues</h6>
                                        <button type="button" class="btn btn-sm btn-success" id="btnAdicionarEquipamento">
                                            <i class="fas fa-plus"></i> Adicionar
                                        </button>
                                    </div>
                                    <div class="card-body" id="equipamentosContainer">
                                        ${equipamentosHtml}
                                    </div>
                                </div>

                                <div class="card border-start border-secondary border-4 mb-3">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0"><i class="fas fa-file-alt text-secondary"></i> Observações</h6>
                                    </div>
                                    <div class="card-body">
                                        <textarea class="form-control" id="termoObservacoes" rows="3" placeholder="Adicione observações ou comentários...">${termo.observacoes || ''}</textarea>
                                    </div>
                                </div>

                                <div class="alert ${termo.tem_termo_gerado ? 'alert-success' : 'alert-info'}" role="alert">
                                    <i class="fas ${termo.tem_termo_gerado ? 'fa-check-circle' : 'fa-info-circle'}"></i>
                                    <strong>Status:</strong> ${termo.tem_termo_gerado ? 'Termo já gerado' : 'Ainda não existe termo gerado'}
                                </div>
                            `;

                        }

                        document.getElementById('modalTermoBody').innerHTML = html;
                document.getElementById('btnSalvarTermo').style.display = 'inline-block';

                // Desabilitar campos se o termo já foi gerado
                const temTermoGerado = !!termo.tem_termo_gerado;
                if (temTermoGerado) {
                    document.querySelectorAll('#modalTermoBody input, #modalTermoBody textarea').forEach(el => {
                        el.disabled = true;
                    });
                    document.getElementById('btnAdicionarEquipamento').disabled = false;
                    document.getElementById('btnAdicionarEquipamento').title = 'Adicionar equipamento criará um aditivo ao termo';
                    document.getElementById('btnSalvarTermo').style.display = 'none';
                    document.getElementById('btnSalvarTermo').innerHTML = '<i class="fas fa-file-signature"></i> Gerar Termo';
                    document.getElementById('btnGerarAditivo').style.display = 'inline-block';
                    document.getElementById('btnGerarAditivo').innerHTML = '<i class="fas fa-file-invoice"></i> Gerar Aditivo';
                } else {
                    document.getElementById('btnSalvarTermo').style.display = 'inline-block';
                    document.getElementById('btnSalvarTermo').innerHTML = '<i class="fas fa-file-signature"></i> Gerar Termo';
                    document.getElementById('btnGerarAditivo').style.display = 'none';
                }

                // Event listeners
                document.getElementById('btnAdicionarEquipamento').addEventListener('click', abrirFormularioEquipamento);
                
                document.querySelectorAll('.btn-deletar-equipamento').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const eqId = this.dataset.eqId;
                        if (confirm('Tem certeza que deseja remover este equipamento?')) {
                            deletarEquipamento(usuarioSelecionadoTermo, eqId);
                        }
                    });
                });

                document.getElementById('btnSalvarTermo').onclick = gerarTermo;
                document.getElementById('btnGerarAditivo').onclick = gerarAditivo;
                document.getElementById('btnExportarTermo').onclick = exportarTermo;

            } catch (error) {
                console.error('Erro:', error);
                document.getElementById('modalTermoBody').innerHTML = `<div class="alert alert-danger">Erro ao carregar termo: ${error.message}</div>`;
            }
        }

        function abrirFormularioEquipamento() {
            const html = `
                <div class="card border-info mb-3" id="formEquipamento">
                    <div class="card-body">
                        <h6 class="card-title mb-3">Novo Equipamento</h6>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label for="eqDescricao" class="form-label">Descrição <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="eqDescricao" placeholder="Ex: Notebook" required>
                            </div>
                            <div class="col-md-6">
                                <label for="eqMarca" class="form-label">Marca</label>
                                <input type="text" class="form-control" id="eqMarca" placeholder="Ex: Dell">
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label for="eqModelo" class="form-label">Modelo</label>
                                <input type="text" class="form-control" id="eqModelo" placeholder="Ex: Inspiron 3000">
                            </div>
                            <div class="col-md-6">
                                <label for="eqEstado" class="form-label">Estado</label>
                                <select class="form-select" id="eqEstado">
                                    <option value="Novo">Novo</option>
                                    <option value="Seminovo">Seminovo</option>
                                </select>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label for="eqServiceTag" class="form-label">ServiceTag</label>
                                <input type="text" class="form-control" id="eqServiceTag" placeholder="Ex: ST123456">
                            </div>
                        </div>
                        <div class="row mb-3" id="eqFotosRow" style="display:none;">
                            <div class="col-12">
                                <label class="form-label">Fotos (apenas para itens "Seminovo")</label>
                                <small class="form-text text-muted d-block mb-2">Sequência dos títulos: Frente, Direita, Esquerda, Em Cima, Teclado, Inferior</small>
                                <div id="eqFotosContainer">
                                    <!-- file inputs with name="fotos" will be appended here dynamically -->
                                </div>
                                <small class="form-text text-muted">Após escolher uma foto, um novo campo será exibido para adicionar outra.</small>
                            </div>
                        </div>
                        <div class="btn-group" role="group">
                            <button type="button" class="btn btn-sm btn-success" id="btnConfirmarEquipamento">
                                <i class="fas fa-check"></i> Adicionar
                            </button>
                            <button type="button" class="btn btn-sm btn-secondary" id="btnCancelarEquipamento">
                                <i class="fas fa-times"></i> Cancelar
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.getElementById('equipamentosContainer').insertAdjacentHTML('beforeend', html);
            
            document.getElementById('btnConfirmarEquipamento').addEventListener('click', adicionarEquipamento);
            document.getElementById('btnCancelarEquipamento').addEventListener('click', () => {
                document.getElementById('formEquipamento').remove();
            });
            // show/hide fotos field based on estado
            const eqEstadoEl = document.getElementById('eqEstado');
            const fotosRow = document.getElementById('eqFotosRow');
            const fotosContainer = document.getElementById('eqFotosContainer');

            function ensureFileInputIfNeeded() {
                if (eqEstadoEl.value === 'Seminovo') {
                    fotosRow.style.display = 'block';
                    if (!fotosContainer.querySelector('input[name="fotos"]')) {
                        addFileInput();
                    }
                } else {
                    fotosRow.style.display = 'none';
                }
            }

            eqEstadoEl.addEventListener('change', ensureFileInputIfNeeded);
            ensureFileInputIfNeeded();

            function addFileInput() {
                const input = document.createElement('input');
                input.type = 'file';
                input.name = 'fotos';
                input.accept = 'image/*';
                input.className = 'form-control mb-2';

                const titles = ['Frente', 'Direita', 'Esquerda', 'Em Cima', 'Teclado', 'Inferior'];
                const currentIndex = fotosContainer.querySelectorAll('input[name="fotos"]').length;
                const titulo = titles[currentIndex] || `Laudo ${currentIndex - titles.length + 1}`;

                const wrapper = document.createElement('div');
                wrapper.className = 'mb-2';

                const label = document.createElement('small');
                label.className = 'd-block text-muted mb-1';
                label.textContent = titulo;

                input.dataset.titulo = titulo;
                input.addEventListener('change', function() {
                    // when a file is chosen, append another empty input to allow more
                    if (this.files && this.files.length > 0) {
                        // only add another if there isn't an empty one
                        const empty = Array.from(fotosContainer.querySelectorAll('input[name="fotos"]')).some(i => !i.files || i.files.length === 0);
                        if (!empty) addFileInput();
                    }
                });

                wrapper.appendChild(label);
                wrapper.appendChild(input);
                fotosContainer.appendChild(wrapper);
            }
        }

        async function adicionarEquipamento() {
            const descricao = document.getElementById('eqDescricao').value.trim();
            const marca = document.getElementById('eqMarca').value.trim();
            const modelo = document.getElementById('eqModelo').value.trim();
            const estado = document.getElementById('eqEstado').value;
            const serviceTag = document.getElementById('eqServiceTag').value.trim();

            if (!descricao) {
                alert('Descrição do equipamento é obrigatória.');
                return;
            }

            const formData = new FormData();
            formData.append('descricao', descricao);
            formData.append('marca', marca);
            formData.append('modelo', modelo);
            formData.append('estado', estado);
            formData.append('service_tag', serviceTag);

            // append fotos if present (inputs named 'fotos')
            const fotoInputs = document.querySelectorAll('#eqFotosContainer input[name="fotos"]');
            if (fotoInputs && fotoInputs.length) {
                fotoInputs.forEach(inp => {
                    if (inp.files && inp.files.length > 0) {
                        formData.append('fotos', inp.files[0]);
                        formData.append('fotos_titulos', inp.dataset.titulo || '');
                    }
                });
            }

            try {
                const response = await fetch(`/admin/usuarios/${usuarioSelecionadoTermo}/termo-entrega/equipamentos/adicionar`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: formData
                });
                const contentType = response.headers.get('content-type') || '';
                let data = null;

                if (contentType.includes('application/json')) {
                    data = await response.json();
                } else {
                    const responseText = await response.text();
                    throw new Error(responseText || 'Resposta inválida do servidor.');
                }

                if (data.success) {
                    if (data.criar_aditivo) {
                        alert('✓ Equipamento adicionado!\n\n⚠️ ' + data.message);
                    } else {
                        alert('✓ Equipamento adicionado!');
                    }
                    await carregarTermo(usuarioSelecionadoTermo);
                } else {
                    alert('Erro: ' + data.message);
                }
            } catch (error) {
                alert('Erro ao adicionar equipamento: ' + error.message);
            }
        }

        async function deletarEquipamento(userId, eqId) {
            try {
                const response = await fetch(`/admin/usuarios/${userId}/termo-entrega/equipamentos/${eqId}/deletar`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    }
                });
                const data = await response.json();

                if (data.success) {
                    await carregarTermo(userId);
                } else {
                    alert('Erro: ' + data.message);
                }
            } catch (error) {
                alert('Erro ao deletar equipamento: ' + error.message);
            }
        }

        function setButtonLoading(button, isLoading, loadingText) {
            if (!button) return;

            if (!button.dataset.originalHtml) {
                button.dataset.originalHtml = button.innerHTML;
            }

            if (isLoading) {
                button.disabled = true;
                button.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${loadingText}`;
            } else {
                button.disabled = false;
                button.innerHTML = button.dataset.originalHtml;
            }
        }

        function setTermoLoading(isLoading, action = 'gerar') {
            const btnGerar = document.getElementById('btnSalvarTermo');
            const btnExportar = document.getElementById('btnExportarTermo');
            const btnFechar = document.querySelector('#termoEntregaModal [data-bs-dismiss="modal"]');

            if (action === 'exportar') {
                setButtonLoading(btnExportar, isLoading, 'Exportando...');
                if (btnGerar) btnGerar.disabled = isLoading;
            } else {
                setButtonLoading(btnGerar, isLoading, 'Gerando...');
                if (btnExportar) btnExportar.disabled = isLoading;
            }

            if (btnFechar) {
                btnFechar.disabled = isLoading;
            }
        }

        async function gerarTermo() {
            const formData = new FormData();
            formData.append('empresa', document.getElementById('termoEmpresa').value);
            formData.append('cnpj', document.getElementById('termoCNPJ').value);
            formData.append('endereco', document.getElementById('termoEndereco').value);
            formData.append('cpf_cnpj', document.getElementById('termoCPF').value);
            formData.append('cargo_funcao', document.getElementById('termoCargo').value);
            formData.append('departamento', document.getElementById('termoDepartamento').value);
            formData.append('local_trabalho', document.getElementById('termoLocal').value);
            formData.append('data_admissao', document.getElementById('termoDataAdmissao').value);
            formData.append('observacoes', document.getElementById('termoObservacoes').value);

            // Campos PJ (se presentes no modal)
            const pjContratanteEl = document.getElementById('pjContratante');
            if (pjContratanteEl) {
                formData.append('pj_contratante', pjContratanteEl.value || '');
                formData.append('pj_contratante_cnpj', (document.getElementById('pjContratanteCnpj') ? document.getElementById('pjContratanteCnpj').value : '') || '');
                formData.append('pj_contratante_endereco', (document.getElementById('pjContratanteEndereco') ? document.getElementById('pjContratanteEndereco').value : '') || '');
                formData.append('pj_contratada', (document.getElementById('pjContratada') ? document.getElementById('pjContratada').value : '') || '');
                formData.append('pj_contratada_cnpj', (document.getElementById('pjContratadaCnpj') ? document.getElementById('pjContratadaCnpj').value : '') || '');
                formData.append('pj_data_contrato', (document.getElementById('pjDataContrato') ? document.getElementById('pjDataContrato').value : '') || '');
            }

            try {
                setTermoLoading(true, 'gerar');
                const salvarResponse = await fetch(`/admin/usuarios/${usuarioSelecionadoTermo}/termo-entrega/atualizar`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: formData
                });
                const salvarData = await salvarResponse.json();

                if (salvarData.success) {
                    const exportacao = await exportarTermoSilencioso();
                    if (!exportacao.success) {
                        alert('Termo salvo, mas houve erro ao gerar PDF: ' + (exportacao.message || 'Erro desconhecido'));
                        return;
                    }

                    alert('Termo gerado com sucesso e salvo nos Documentos do usuário.');
                    await carregarTermo(usuarioSelecionadoTermo);
                    setTimeout(() => window.location.reload(), 900);
                } else {
                    if (salvarData.termo_gerado) {
                        alert('⚠️ ' + salvarData.message + '\n\nOs novos equipamentos criarão um ADITIVO ao termo original.');
                        await carregarTermo(usuarioSelecionadoTermo);
                    } else {
                        alert('Erro ao salvar informações do termo: ' + salvarData.message);
                    }
                }
            } catch (error) {
                alert('Erro ao gerar termo: ' + error.message);
            } finally {
                setTermoLoading(false, 'gerar');
            }
        }

        async function exportarTermoSilencioso(aditivo = false) {
            try {
                const response = await fetch(`/admin/usuarios/${usuarioSelecionadoTermo}/termo-entrega/exportar`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ aditivo: aditivo })
                });

                return await response.json();
            } catch (error) {
                return { success: false, message: error.message };
            }
        }

        async function gerarAditivo() {
            // Gerar aditivo sem tentar editar campos
            try {
                setTermoLoading(true, 'exportar');
                const exportacao = await exportarTermoSilencioso(true);
                
                if (exportacao.success) {
                    alert('✓ Aditivo gerado com sucesso e salvo nos Documentos do usuário.');
                    await carregarTermo(usuarioSelecionadoTermo);
                    setTimeout(() => window.location.reload(), 900);
                } else {
                    alert('Erro ao gerar aditivo: ' + (exportacao.message || 'Erro desconhecido'));
                }
            } catch (error) {
                alert('Erro ao gerar aditivo: ' + error.message);
            } finally {
                setTermoLoading(false, 'exportar');
            }
        }

        async function exportarTermo() {
            try {
                setTermoLoading(true, 'exportar');
                const data = await exportarTermoSilencioso();
                if (data.success) {
                    alert('Documento exportado e salvo nos Documentos do usuário.');
                    setTimeout(() => window.location.reload(), 900);
                } else {
                    alert('Erro ao exportar: ' + (data.message || 'Erro desconhecido'));
                }
            } finally {
                setTermoLoading(false, 'exportar');
            }
        }
    