// =============================================================================
// VARIÁVEIS GLOBAIS
// =============================================================================

let productsData = [];
let currentProdutoId = null;
let categoriasChart = null;
let topProdutosChart = null;
let tipoChamadoSelecionado = 'Todos';

let chamadasUsuarioStatus = {};
let chamadasUsuarioPrimeiroLoad = true;

const API_BASE = window.location.origin + '/api';

// =============================================================================
// SISTEMA DE NOTIFICAÇÕES (TOAST)
// =============================================================================

/**
 * Exibe uma notificação toast
 * @param {string} mensagem - Texto da notificação
 * @param {string} tipo - 'success', 'danger', 'warning', 'info' (padrão)
 * @param {number} duracao - Tempo em ms antes de desaparecer (0 = manual)
 */
function mostrarNotificacao(mensagem, tipo = 'info', duracao = 4000) {
    const container = document.getElementById('toast-container') || criarToastContainer();
    
    const icons = {
        success: 'fas fa-check-circle',
        danger: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${tipo}`;
    toast.innerHTML = `
        <div class="toast-header">
            <i class="${icons[tipo] || icons.info} toast-header-icon"></i>
            <div style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                <span style="font-weight: 600; color: #212529;">${escapeHtml(mensagem)}</span>
            </div>
            <button class="toast-close" onclick="this.parentElement.parentElement.classList.add('hide'); setTimeout(() => this.parentElement.parentElement.remove(), 300);">&times;</button>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Auto-remover após duração
    if (duracao > 0) {
        setTimeout(() => {
            toast.classList.add('hide');
            setTimeout(() => toast.remove(), 300);
        }, duracao);
    }
    
    return toast;
}

/**
 * Cria o container para toast notifications
 */
function criarToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

/**
 * Atalho para notificação de sucesso
 */
function mostrarSucesso(mensagem, duracao = 3000) {
    mostrarNotificacao(mensagem, 'success', duracao);
}

/**
 * Atalho para notificação de erro
 */
function mostrarErro(mensagem, erro = null, duracao = 5000) {
    if (erro instanceof Error) {
        console.error(mensagem, erro);
        mostrarNotificacao(`${mensagem}: ${erro.message}`, 'danger', duracao);
    } else if (erro) {
        console.error(mensagem, erro);
        mostrarNotificacao(mensagem, 'danger', duracao);
    } else {
        mostrarNotificacao(mensagem, 'danger', duracao);
    }
}

/**
 * Atalho para notificação de aviso
 */
function mostrarAviso(mensagem, duracao = 4000) {
    mostrarNotificacao(mensagem, 'warning', duracao);
}

// =============================================================================
// CARREGAMENTO E VALIDAÇÃO DE FORMS
// =============================================================================

/**
 * Configura feedback de validação para um formulário
 */
function configurarValidacaoForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', function(e) {
        if (!form.checkValidity() === false) {
            e.preventDefault();
            e.stopPropagation();
        }
        form.classList.add('was-validated');
    }, false);
}

/**
 * Aplica validação em tempo real para inputs
 */
function configurarValidacaoRealTime(inputSelector) {
    document.querySelectorAll(inputSelector).forEach(input => {
        input.addEventListener('blur', function() {
            this.classList.add('touched');
            if (!this.checkValidity()) {
                this.classList.add('is-invalid');
                this.classList.remove('is-valid');
            } else {
                this.classList.add('is-valid');
                this.classList.remove('is-invalid');
            }
        });

        input.addEventListener('input', function() {
            if (this.classList.contains('touched')) {
                if (!this.checkValidity()) {
                    this.classList.add('is-invalid');
                    this.classList.remove('is-valid');
                } else {
                    this.classList.add('is-valid');
                    this.classList.remove('is-invalid');
                }
            }
        });
    });
}

/**
 * Mostra loading state em um botão
 */
function setarLoadingBtn(btnSelector, isLoading = true) {
    const btn = document.querySelector(btnSelector);
    if (!btn) return;
    
    if (isLoading) {
        btn.disabled = true;
        btn.classList.add('btn-loading');
        btn.dataset.originalText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner spinner-sm"></span> Processando...';
    } else {
        btn.disabled = false;
        btn.classList.remove('btn-loading');
        btn.innerHTML = btn.dataset.originalText || btn.innerHTML;
    }
}

/**
 * Wrapper para requisições com melhor tratamento de erros
 */
async function fetchAPI(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.erro || data.message || `Erro HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// =============================================================================
// INICIALIZAÇÃO
// =============================================================================

document.addEventListener('DOMContentLoaded', function () {
    carregarDados();
    configurarEventos();

    const appShell = document.querySelector('.app-shell');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    if (window.matchMedia('(max-width: 992px)').matches && appShell) {
        appShell.classList.add('sidebar-collapsed');
        document.body.classList.add('sidebar-is-collapsed');
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', () => {
            if (appShell && !appShell.classList.contains('sidebar-collapsed')) {
                toggleSidebar();
            }
        });
    }

    const requestedSection = getQueryParam('section');
    if (requestedSection) {
        showSection(requestedSection);
    } else {
        // Exibição inicial conforme permissão de usuário
        if (window.USUARIO_IS_ADMIN === 'true' || window.USUARIO_IS_ADMIN === true) {
            showSection('dashboard');
        } else {
            showSection('chamadas');
        }
    }

    // Recarregar dados a cada 1 minuto e 30 segundos
    setInterval(carregarDados, 90000);

    // Para administradores, atualizar badge de chamadas não lidas
    if (window.USUARIO_IS_ADMIN === 'true' || window.USUARIO_IS_ADMIN === true) {
        carregarBadgeAdminChamadas();
        setInterval(carregarBadgeAdminChamadas, 30000);
    }

    // Para usuários, atualizar chamadas frequentemente (quase em tempo real)
    if (window.USUARIO_IS_ADMIN !== 'true' && window.USUARIO_IS_ADMIN !== true) {
        setInterval(carregarChamadasUsuario, 10000);
    }
});

// =============================================================================
// FUNÇÕES AUXILIARES
// =============================================================================

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/\'/g, '&#39;');
}

function parseDataChamada(dataTexto) {
    if (!dataTexto) return null;
    const partes = dataTexto.split(' ');
    if (partes.length < 2) return null;
    const [dia, mes, ano] = partes[0].split('/').map(Number);
    const [hora, minuto, segundo] = partes[1].split(':').map(Number);
    return new Date(ano, mes - 1, dia, hora || 0, minuto || 0, segundo || 0);
}

function obterStatusLabel(status) {
    const mapa = {
        nova: 'Nova',
        lida: 'Lida',
        analise: 'Em Análise',
        execucao: 'Em Execução',
        concluida: 'Concluída'
    };
    return mapa[status] || 'Desconhecido';
}

function abrirDetalhesChamadas(tipo) {
    const titulos = {
        analise: 'Chamados em Análise',
        execucao: 'Chamados em Execução',
        abertas: 'Chamados em Aberto',
        novas: 'Chamados Novos',
        finalizadas: 'Finalizados (7 dias)'
    };
    const titulo = titulos[tipo] || 'Detalhes dos Chamados';
    document.getElementById('modalDetalhesChamadasLabel').textContent = titulo;
    document.getElementById('modalDetalhesChamadasContainer').innerHTML = '<p class="text-muted">Carregando...</p>';

    const modal = new bootstrap.Modal(document.getElementById('modalDetalhesChamadas'));
    modal.show();
    carregarDetalhesChamadas(tipo);
}

function filtrarChamadasPorTipo(tipo, chamadas) {
    const seteDiasAtras = new Date();
    seteDiasAtras.setDate(seteDiasAtras.getDate() - 7);

    return chamadas.filter(chamada => {
        if (!chamada || !chamada.status) return false;

        if (tipo === 'analise') {
            return chamada.status === 'analise';
        }
        if (tipo === 'execucao') {
            return chamada.status === 'execucao';
        }
        if (tipo === 'abertas') {
            return ['nova', 'analise', 'execucao', 'lida'].includes(chamada.status);
        }
        if (tipo === 'novas') {
            return chamada.status === 'nova';
        }
        if (tipo === 'finalizadas') {
            if (chamada.status !== 'concluida') return false;
            const data = parseDataChamada(chamada.data_criacao);
            return data ? data >= seteDiasAtras : false;
        }
        return false;
    });
}

function carregarDetalhesChamadas(tipo) {
    fetch(`${API_BASE}/chamadas?limit=200`)
        .then(r => r.json())
        .then(chamadas => {
            const detalhes = filtrarChamadasPorTipo(tipo, chamadas);
            const container = document.getElementById('modalDetalhesChamadasContainer');

            if (!Array.isArray(detalhes) || detalhes.length === 0) {
                container.innerHTML = '<p class="text-muted">Nenhum chamado encontrado para esta categoria.</p>';
                return;
            }

            container.innerHTML = detalhes.map(chamada => {
                const statusLabel = obterStatusLabel(chamada.status);
                const avatarHtml = chamada.usuario_foto_url
                    ? `<img src="${escapeHtml(chamada.usuario_foto_url)}" alt="Foto de ${escapeHtml(chamada.usuario || 'Usuário')}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 1px solid #d1d5db;">`
                    : '<div style="width: 40px; height: 40px; border-radius: 50%; background: #e5e7eb; display: inline-flex; align-items: center; justify-content: center; color: #4b5563;"><i class="fas fa-user"></i></div>';

                const fotoAnexoHtml = chamada.foto_url
                    ? `
                        <div class="mb-2">
                            <strong>Imagem enviada:</strong><br>
                            <a href="${escapeHtml(chamada.foto_url)}" target="_blank" rel="noopener noreferrer">
                                <img src="${escapeHtml(chamada.foto_url)}" alt="Imagem do chamado" class="img-fluid rounded border mt-1" style="max-width: 300px; max-height: 220px; object-fit: cover;">
                            </a>
                        </div>
                    `
                    : '';

                return `
                    <div class="card mb-3 shadow-sm">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    ${avatarHtml}
                                    <div>
                                        <h6 class="mb-1">${escapeHtml(chamada.usuario || 'Usuário desconhecido')}</h6>
                                        <small class="text-muted">${escapeHtml(chamada.usuario_area || '')}${chamada.usuario_localizacao ? ' • ' + escapeHtml(chamada.usuario_localizacao) : ''}</small>
                                    </div>
                                </div>
                                <span class="badge bg-secondary">${escapeHtml(statusLabel)}</span>
                            </div>
                            <p class="mb-1"><strong>Data:</strong> ${escapeHtml(chamada.data_criacao || '')}</p>
                            <p class="mb-1"><strong>Mensagem:</strong> ${escapeHtml(chamada.mensagem)}</p>
                            ${fotoAnexoHtml}
                            <p class="mb-0"><strong>ID da chamada:</strong> ${escapeHtml(chamada.id)}</p>
                        </div>
                    </div>
                `;
            }).join('');
        })
        .catch(error => {
            console.error('Erro ao carregar detalhes dos chamados:', error);
            document.getElementById('modalDetalhesChamadasContainer').innerHTML = '<p class="text-danger">Erro ao carregar detalhes dos chamados.</p>';
        });
}

function updateDashboardSubtabActive(section) {
    const buttons = document.querySelectorAll('.dashboard-subtab');
    buttons.forEach(button => {
        button.classList.toggle('active', button.dataset.section === section);
    });
}

function navigateToSection(section, url) {
    const currentPath = window.location.pathname;
    if (currentPath === url) {
        showSection(section);
        return;
    }
    const separator = url.includes('?') ? '&' : '?';
    window.location.href = `${url}${separator}section=${section}`;
}

function getQueryParam(name) {
    return new URLSearchParams(window.location.search).get(name);
}

function toggleSidebar() {
    const appShell = document.querySelector('.app-shell');
    if (!appShell) return;
    appShell.classList.toggle('sidebar-collapsed');

    // Adiciona/remove classe no body para compatibilidade com botão flutuante
    if (appShell.classList.contains('sidebar-collapsed')) {
        document.body.classList.add('sidebar-is-collapsed');
    } else {
        document.body.classList.remove('sidebar-is-collapsed');
    }
}

const sidebarToggleButton = document.getElementById('sidebarToggle');
if (sidebarToggleButton) {
    sidebarToggleButton.addEventListener('click', toggleSidebar);
}

const sidebarToggleFloat = document.getElementById('sidebarToggleFloat');
if (sidebarToggleFloat) {
    sidebarToggleFloat.addEventListener('click', toggleSidebar);
}

function showSection(section) {
    // Ocultar todas as seções
    document.querySelectorAll('.section').forEach(el => {
        el.style.display = 'none';
    });

    // Mostrar subtabs do dashboard quando apropriado
    const dashboardSubtabs = document.getElementById('dashboard-subtabs');
    if (dashboardSubtabs) {
        dashboardSubtabs.style.display = ['dashboard', 'produtos', 'relatorios'].includes(section) ? 'block' : 'none';
    }
    
    // Mostrar seção selecionada
    const sectionId = section + '-section';
    document.getElementById(sectionId).style.display = 'block';
    
    // Atualizar subtab ativa
    updateDashboardSubtabActive(section);

    // Atualizar navegação lateral ativa
    document.querySelectorAll('.sidebar-link').forEach(link => {
        link.classList.toggle('active', link.dataset.section === section);
    });

    // Carregar dados específicos
    if (section === 'dashboard') {
        atualizarDashboard();
    } else if (section === 'produtos') {
        atualizarTabelaProdutos();
    } else if (section === 'relatorios') {
        atualizarRelatorios();
    } else if (section === 'chamadas') {
        carregarChamadasUsuario();
    }
}

function carregarBadgeAdminChamadas() {
    const badges = [
        document.getElementById('badge-admin-chamadas'),
        document.getElementById('badge-admin-chamados-sidebar')
    ].filter(Boolean);

    if (badges.length === 0) return;

    fetch(`${API_BASE}/chamadas/nao-lidas`)
        .then(response => response.json())
        .then(data => {
            if (data && typeof data.nao_lidas === 'number') {
                badges.forEach(badge => {
                    badge.textContent = data.nao_lidas;
                    badge.classList.toggle('d-none', data.nao_lidas <= 0);
                });
            }
        })
        .catch(error => {
            console.error('Erro ao carregar badge de chamadas:', error);
        });
}

// =============================================================================
// CARREGAR DADOS
// =============================================================================

function carregarDados() {
    if (window.USUARIO_IS_ADMIN === 'true' || window.USUARIO_IS_ADMIN === true) {
        Promise.all([
            fetch(`${API_BASE}/produtos`).then(async r => {
                const data = await r.json().catch(() => null);
                if (!r.ok) {
                    const mensagem = data && (data.erro || data.message) ? (data.erro || data.message) : r.statusText;
                    throw new Error(`Falha ao carregar produtos: ${mensagem}`);
                }
                return data;
            }),
            fetch(`${API_BASE}/relatorios/resumo`).then(async r => {
                const data = await r.json().catch(() => null);
                if (!r.ok) {
                    const mensagem = data && (data.erro || data.message) ? (data.erro || data.message) : r.statusText;
                    throw new Error(`Falha ao carregar resumo: ${mensagem}`);
                }
                return data;
            })
        ])
        .then(([produtos, resumo]) => {
            productsData = Array.isArray(produtos) ? produtos : [];
            if (!Array.isArray(produtos)) {
                console.warn('Resposta de produtos não é um array:', produtos);
            }
            atualizarKPIs(resumo || {});
            atualizarEstoqueBaixo();

            // Atualiza a tabela e gráficos conforme seção ativa (auto-refresh)
            if (document.getElementById('produtos-section') && document.getElementById('produtos-section').style.display !== 'none') {
                atualizarTabelaProdutos();
            }
            if (document.getElementById('dashboard-section') && document.getElementById('dashboard-section').style.display !== 'none') {
                atualizarDashboard();
            }
            if (document.getElementById('relatorios-section') && document.getElementById('relatorios-section').style.display !== 'none') {
                atualizarRelatorios();
            }
        })
        .catch(error => {
            productsData = [];
            atualizarTabelaProdutos();
            mostrarErro('Erro ao carregar dados', error);
        });
    } else {
        atualizarEstoqueBaixo();
        carregarChamadasUsuario();
    }
}

function atualizarKPIs(resumo) {
    try {
        // Verificar se os elementos existem antes de tentar atualizar
        const elementos = {
            'kpi-chamadas-analise': resumo.chamadas_analise,
            'kpi-chamadas-execucao': resumo.chamadas_execucao,
            'kpi-chamadas-abertas': resumo.chamadas_abertas,
            'kpi-chamadas-novas': resumo.chamadas_novas,
            'kpi-chamadas-finalizadas-7dias': resumo.chamadas_finalizadas_7dias,
            'kpi-baixo': resumo.produtos_estoque_baixo
        };

        for (const [elementId, valor] of Object.entries(elementos)) {
            const elemento = document.getElementById(elementId);
            if (elemento && valor !== undefined && valor !== null) {
                elemento.textContent = valor;
            }
        }
    } catch (error) {
        console.error('Erro ao atualizar KPIs:', error);
    }
}

function atualizarEstoqueBaixo() {
    const tbody = document.getElementById('estoque-baixo-table');
    if (!tbody) return;

    // Mostrar loading skeleton
    tbody.innerHTML = '<tr><td colspan="7"><div class="skeleton skeleton-text"></div></td></tr>';

    fetch(`${API_BASE}/relatorios/estoque-baixo`)
        .then(r => r.json())
        .then(datos => {
            if (datos.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7">
                            <div class="empty-state">
                                <div class="empty-state-icon"><i class="fas fa-check"></i></div>
                                <div class="empty-state-title">Tudo em ordem!</div>
                                <div class="empty-state-text">Todos os produtos estão acima do estoque mínimo.</div>
                            </div>
                        </td>
                    </tr>
                `;
                return;
            }
            
            tbody.innerHTML = datos.map(prod => `
                <tr>
                    <td><strong>${escapeHtml(prod.id)}</strong></td>
                    <td>${escapeHtml(prod.nome)}</td>
                    <td><span class="badge bg-secondary">${escapeHtml(prod.categoria)}</span></td>
                    <td>${escapeHtml(prod.quantidade)}</td>
                    <td>${escapeHtml(prod.minimo)}</td>
                    <td><strong class="text-danger">-${escapeHtml(prod.faltam)}</strong></td>
                    <td>
                        <button class="btn btn-sm btn-success" onclick="abrirMovimentacao('${escapeHtml(prod.id)}')" title="Registrar entrada de estoque">
                            <i class="fas fa-arrow-up"></i> Entrada
                        </button>
                    </td>
                </tr>
            `).join('');
        })
        .catch(error => {
            console.error('Erro ao carregar estoque baixo:', error);
            tbody.innerHTML = `
                <tr>
                    <td colspan="7">
                        <div class="empty-state">
                            <div class="empty-state-icon"><i class="fas fa-exclamation"></i></div>
                            <div class="empty-state-title">Erro ao carregar</div>
                            <div class="empty-state-text">Não foi possível buscar dados de estoque.</div>
                        </div>
                    </td>
                </tr>
            `;
        });
}

async function carregarChamadasUsuario() {
    const container = document.getElementById('lista-chamadas-usuario');
    if (!container) return;

                container.innerHTML = '<p class="text-muted">Carregando chamados...</p>';

    try {
        const response = await fetch(`${API_BASE}/chamadas`);
        if (!response.ok) {
            throw new Error('Falha ao buscar chamadas');
        }

        const chamadas = await response.json();

        if (!Array.isArray(chamadas) || chamadas.length === 0) {
            container.innerHTML = '<p class="text-muted">Nenhuma chamada enviada ainda.</p>';
            chamadasUsuarioPrimeiroLoad = false;
            return;
        }

        const rows = chamadas.map(chamada => {
            const statusLabelMap = {
                'nova': 'Nova',
                'lida': 'Lida',
                'analise': 'Em Análise',
                'execucao': 'Em Execução',
                'concluida': 'Concluída'
            };
            const statusLabel = statusLabelMap[chamada.status] || 'Desconhecido';
            
            if (!chamadasUsuarioPrimeiroLoad) {
                const anterior = chamadasUsuarioStatus[chamada.id];
                if (anterior && anterior !== chamada.status && chamada.status !== 'lida') {
                    mostrarAlerta(`Atualização: a chamada "${escapeHtml(chamada.mensagem.substring(0, 40))}" foi alterada de ${statusLabelMap[anterior] || anterior} para ${statusLabel}.`, 'info');
                }
            }

            chamadasUsuarioStatus[chamada.id] = chamada.status;
            const fotoHtml = chamada.foto_url
                ? `
                    <div class="mt-2">
                        <a href="${escapeHtml(chamada.foto_url)}" target="_blank" rel="noopener noreferrer">
                            <img src="${escapeHtml(chamada.foto_url)}" alt="Foto do problema" class="img-fluid rounded border" style="max-width: 260px; max-height: 200px; object-fit: cover;">
                        </a>
                    </div>
                `
                : '';
            
            return `
                <div class="border rounded p-3 mb-3 ${chamada.status === 'concluida' ? 'bg-success-subtle' : chamada.lida ? 'bg-light' : 'bg-warning-subtle'}">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <strong>${escapeHtml(chamada.data_criacao)}</strong>
                        <span class="badge ${chamada.status === 'concluida' ? 'bg-success' : chamada.lida ? 'bg-secondary' : 'bg-danger'}">${statusLabel}</span>
                    </div>
                    <p class="mb-0">${escapeHtml(chamada.mensagem)}</p>
                    ${fotoHtml}
                </div>
            `;
        }).join('');
        chamadasUsuarioPrimeiroLoad = false;

        container.innerHTML = rows;
    } catch (error) {
        console.error('Erro ao carregar chamadas de usuário:', error);
        container.innerHTML = '<p class="text-danger">Erro ao carregar chamadas.</p>';
    }
}

// =============================================================================
// DASHBOARD
// =============================================================================

function atualizarDashboard() {
    atualizarGraficoTiposChamadas();
    atualizarGraficoTopProdutos();
}

function extrairTipoChamado(mensagem) {
    const match = mensagem.match(/^\[(.*?)\]/);
    if (!match) return 'Outros';
    const conteudo = match[1].trim();
    return conteudo.split(' - ')[0].trim() || 'Outros';
}

function extrairSubtipoChamado(mensagem) {
    const match = mensagem.match(/^\[(.*?)\]/);
    if (!match) return 'Outros';
    const conteudo = match[1].trim();
    const partes = conteudo.split(' - ');
    return partes[1] ? partes[1].trim() : 'Outros';
}

function obterOpcoesDeTipos(chamadas) {
    const tipos = new Set();
    chamadas.forEach(chamada => {
        if (chamada && chamada.mensagem) {
            tipos.add(extrairTipoChamado(chamada.mensagem));
        }
    });
    return Array.from(tipos).sort();
}

function atualizarFiltroTiposChamados(chamadas) {
    const select = document.getElementById('tipoChamadoFiltro');
    if (!select) return;

    const tipos = obterOpcoesDeTipos(chamadas);
    const valorAtual = select.value || 'Todos';

    select.innerHTML = '<option value="Todos">Todos os tipos</option>' + tipos.map(tipo => `\n        <option value="${escapeHtml(tipo)}">${escapeHtml(tipo)}</option>`).join('');

    if (tipos.includes(valorAtual) || valorAtual === 'Todos') {
        select.value = valorAtual;
        tipoChamadoSelecionado = valorAtual;
    } else {
        select.value = 'Todos';
        tipoChamadoSelecionado = 'Todos';
    }
}

function agruparTiposChamadas(chamadas, tipoFiltro) {
    const contagem = {};
    chamadas.forEach(chamada => {
        if (!chamada || !chamada.mensagem) return;
        const tipoPrincipal = extrairTipoChamado(chamada.mensagem);
        const subtipo = extrairSubtipoChamado(chamada.mensagem);

        if (tipoFiltro && tipoFiltro !== 'Todos') {
            if (tipoPrincipal !== tipoFiltro) return;
            contagem[subtipo] = (contagem[subtipo] || 0) + 1;
        } else {
            contagem[tipoPrincipal] = (contagem[tipoPrincipal] || 0) + 1;
        }
    });

    return Object.entries(contagem)
        .sort((a, b) => b[1] - a[1])
        .map(([tipo, total]) => ({ tipo, total }));
}

function atualizarGraficoTiposChamadas() {
    fetch(`${API_BASE}/chamadas?limit=200`)
        .then(r => r.json())
        .then(chamadas => {
            atualizarFiltroTiposChamados(chamadas);
            const select = document.getElementById('tipoChamadoFiltro');
            if (select) {
                tipoChamadoSelecionado = select.value || 'Todos';
            }

            const tipoLabel = tipoChamadoSelecionado === 'Todos' ? 'Chamadas recentes por tipo' : `Chamadas recentes: ${tipoChamadoSelecionado}`;
            const tipos = agruparTiposChamadas(chamadas, tipoChamadoSelecionado);
            const labels = tipos.map(t => t.tipo);
            const valores = tipos.map(t => t.total);
            const cores = gerarCores(labels.length);

            if (categoriasChart) {
                categoriasChart.destroy();
            }

            const ctx = document.getElementById('categoriasChart').getContext('2d');
            categoriasChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: tipoLabel,
                        data: valores,
                        backgroundColor: cores,
                        borderColor: cores,
                        borderWidth: 1,
                        borderRadius: 6,
                        maxBarThickness: 48
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: context => `${context.parsed.y} chamada(s)`
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false
                            }
                        },
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.08)',
                                lineWidth: 1,
                                drawBorder: false
                            },
                            ticks: {
                                precision: 0
                            }
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Erro ao carregar tipos de chamadas:', error));
}

function atualizarGraficoTopProdutos() {
    fetch(`${API_BASE}/relatorios/top-produtos`)
        .then(r => r.json())
        .then(produtos => {
            const labels = produtos.map(p => p.nome.substring(0, 15));
            const valores = produtos.map(p => p.valor_total);
            
            if (topProdutosChart) {
                topProdutosChart.destroy();
            }
            
            const ctx = document.getElementById('topProdutosChart').getContext('2d');
            topProdutosChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Valor Total (R$)',
                        data: valores,
                        backgroundColor: 'rgba(13, 110, 253, 0.7)',
                        borderColor: 'rgba(13, 110, 253, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: true,
                            labels: { font: { size: 12 } }
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Erro ao carregar top produtos:', error));
}

// =============================================================================
// PRODUTOS
// =============================================================================

function atualizarTabelaProdutos() {
    const tbody = document.getElementById('produtos-table');
    
    if (!Array.isArray(productsData) || productsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Nenhum produto cadastrado</td></tr>';
        return;
    }
    
    tbody.innerHTML = productsData.map(prod => `
        <tr>
            <td><strong>${escapeHtml(prod.id)}</strong></td>
            <td>${escapeHtml(prod.nome)}</td>
            <td><span class="badge bg-secondary">${escapeHtml(prod.categoria)}</span></td>
            <td>R$ ${formatarMoeda(prod.preco)}</td>
            <td>${escapeHtml(prod.quantidade)}</td>
            <td>R$ ${formatarMoeda(prod.valor_total)}</td>            <td>${escapeHtml(prod.data_atualizacao || '-')}</td>            <td>
                ${prod.abaixo_minimo 
                    ? '<span class="badge badge-baixo">BAIXO</span>' 
                    : '<span class="badge badge-ok">OK</span>'
                }
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-info" onclick="editarProduto('${escapeHtml(prod.id)}')" title="Editar">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-success" onclick="abrirMovimentacao('${escapeHtml(prod.id)}')" title="Movimentar">
                        <i class="fas fa-arrows-alt-v"></i>
                    </button>
                    <button class="btn btn-danger" onclick="deletarProduto('${escapeHtml(prod.id)}')" title="Deletar">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function novoFormulario() {
    currentProdutoId = null;
    document.getElementById('formProduto').reset();
    document.getElementById('modalProdutoTitle').textContent = 'Novo Produto';
    document.getElementById('prodId').disabled = false;
}

function editarProduto(id) {
    const produto = productsData.find(p => p.id === id);
    
    if (!produto) return;
    
    currentProdutoId = id;
    document.getElementById('modalProdutoTitle').textContent = 'Editar Produto';
    document.getElementById('prodId').value = produto.id;
    document.getElementById('prodNome').value = produto.nome;
    document.getElementById('prodCategoria').value = produto.categoria;
    document.getElementById('prodPreco').value = produto.preco;
    document.getElementById('prodQuantidade').value = produto.quantidade;
    document.getElementById('prodMinimo').value = produto.minimo;
    document.getElementById('prodLocalizacao').value = produto.localizacao;
    document.getElementById('prodId').disabled = true;
    
    const modal = new bootstrap.Modal(document.getElementById('modalProduto'));
    modal.show();
}

function salvarProduto() {
    const id = document.getElementById('prodId').value.trim();
    const nome = document.getElementById('prodNome').value.trim();
    const categoria = document.getElementById('prodCategoria').value.trim();
    const preco = document.getElementById('prodPreco').value;
    const quantidade = document.getElementById('prodQuantidade').value;
    const minimo = document.getElementById('prodMinimo').value;
    const localizacao = document.getElementById('prodLocalizacao').value.trim();
    
    if (!id || !nome || !categoria || !preco || !quantidade || minimo === '') {
        mostrarAlerta('Todos os campos obrigatórios devem ser preenchidos!', 'warning');
        return;
    }
    
    const dados = { id, nome, categoria, preco, quantidade, minimo, localizacao };
    const url = currentProdutoId 
        ? `${API_BASE}/produtos/${currentProdutoId}` 
        : `${API_BASE}/produtos`;
    const metodo = currentProdutoId ? 'PUT' : 'POST';
    
    fetch(url, {
        method: metodo,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
    })
    .then(async response => {
        const data = await response.json().catch(() => null);
        if (!response.ok) {
            const mensagem = data && (data.erro || data.message) ? (data.erro || data.message) : response.statusText;
            throw new Error(mensagem || 'Falha ao salvar produto');
        }
        return data;
    })
    .then(resposta => {
        mostrarAlerta('Produto ' + (currentProdutoId ? 'atualizado' : 'criado') + ' com sucesso!', 'success');
        currentProdutoId = null;
        document.getElementById('prodId').disabled = false;
        bootstrap.Modal.getInstance(document.getElementById('modalProduto')).hide();
        document.getElementById('formProduto').reset();
        carregarDados();
        atualizarTabelaProdutos();
    })
    .catch(error => mostrarErro('Erro ao salvar produto', error));
}

function deletarProduto(id) {
    if (!confirm('Deseja realmente deletar este produto?')) return;
    
    fetch(`${API_BASE}/produtos/${id}`, { method: 'DELETE' })
        .then(async response => {
            const data = await response.json().catch(() => null);
            if (!response.ok) {
                const mensagem = data && (data.erro || data.message) ? (data.erro || data.message) : response.statusText;
                throw new Error(mensagem || 'Falha ao deletar produto');
            }
            return data;
        })
        .then(resposta => {
            mostrarAlerta('Produto deletado com sucesso!', 'success');
            carregarDados();
            atualizarTabelaProdutos();
        })
        .catch(error => mostrarErro('Erro ao deletar produto', error));
}

// =============================================================================
// MOVIMENTAÇÕES
// =============================================================================

function abrirMovimentacao(id) {
    currentProdutoId = id;
    document.getElementById('tipoMovimentacao').value = 'entrada';
    document.getElementById('movQuantidade').value = '';
    atualizarLabelMovimentacao();
    
    const modal = new bootstrap.Modal(document.getElementById('modalMovimentacao'));
    modal.show();
}

function atualizarLabelMovimentacao() {
    const tipo = document.getElementById('tipoMovimentacao').value;
    document.getElementById('modalMovimentacaoTitle').textContent = 
        tipo === 'entrada' ? 'Entrada de Estoque' : 'Saída de Estoque';
}

function salvarMovimentacao() {
    const tipo = document.getElementById('tipoMovimentacao').value;
    const quantidade = parseInt(document.getElementById('movQuantidade').value);
    
    if (!quantidade || quantidade <= 0) {
        mostrarAlerta('Quantidade deve ser maior que zero!', 'warning');
        return;
    }
    
    const endpoint = tipo === 'entrada' ? 'entrada' : 'saida';
    const dados = { id: currentProdutoId, quantidade };
    
    fetch(`${API_BASE}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
    })
    .then(r => r.json())
    .then(resposta => {
        mostrarAlerta(resposta.mensagem || 'Movimentação realizada com sucesso!', 'success');
        bootstrap.Modal.getInstance(document.getElementById('modalMovimentacao')).hide();
        carregarDados();
        atualizarTabelaProdutos();
    })
    .catch(error => mostrarErro('Erro ao realizar movimentação', error));
}

// =============================================================================
// RELATÓRIOS
// =============================================================================

function atualizarRelatorios() {
    atualizarRelatorioCategorias();
    atualizarRelatorioTopProdutos();
}

function atualizarRelatorioCategorias() {
    fetch(`${API_BASE}/relatorios/por-categoria`)
        .then(r => r.json())
        .then(categorias => {
            const tbody = document.getElementById('relatorio-categoria-table');
            tbody.innerHTML = categorias.map(cat => `
                <tr>
                    <td><strong>${escapeHtml(cat.categoria)}</strong></td>
                    <td>${escapeHtml(cat.produtos)}</td>
                    <td>${escapeHtml(cat.quantidade)}</td>
                    <td>R$ ${formatarMoeda(cat.valor_total)}</td>
                </tr>
            `).join('');
        })
        .catch(error => console.error('Erro ao carregar categoria:', error));
}

function atualizarRelatorioTopProdutos() {
    fetch(`${API_BASE}/relatorios/top-produtos`)
        .then(r => r.json())
        .then(produtos => {
            const tbody = document.getElementById('relatorio-top-table');
            tbody.innerHTML = produtos.map(prod => `
                <tr>
                    <td>${escapeHtml(prod.id)}</td>
                    <td>${escapeHtml(prod.nome)}</td>
                    <td>${escapeHtml(prod.quantidade)}</td>
                    <td>R$ ${formatarMoeda(prod.preco)}</td>
                    <td>R$ ${formatarMoeda(prod.valor_total)}</td>
                </tr>
            `).join('');
        })
        .catch(error => console.error('Erro ao carregar top produtos:', error));
}

// =============================================================================
// FUNÇÕES AUXILIARES
// =============================================================================

function configurarEventos() {
    // Buscar produtos
    const searchProdutoInput = document.getElementById('searchProduto');
    if (searchProdutoInput) {
        searchProdutoInput.addEventListener('keyup', function (e) {
        const termo = e.target.value.toLowerCase();
        const tbody = document.getElementById('produtos-table');
        
        if (!termo) {
            atualizarTabelaProdutos();
            return;
        }
        
        const filtrados = productsData.filter(p => 
            p.id.toLowerCase().includes(termo) ||
            p.nome.toLowerCase().includes(termo) ||
            p.categoria.toLowerCase().includes(termo)
        );
        
        tbody.innerHTML = filtrados.map(prod => `
            <tr>
                <td><strong>${prod.id}</strong></td>
                <td>${prod.nome}</td>
                <td><span class="badge bg-secondary">${prod.categoria}</span></td>
                <td>R$ ${formatarMoeda(prod.preco)}</td>
                <td>${prod.quantidade}</td>
                <td>R$ ${formatarMoeda(prod.valor_total)}</td>
                <td>
                    ${prod.abaixo_minimo 
                        ? '<span class="badge badge-baixo">BAIXO</span>' 
                        : '<span class="badge badge-ok">OK</span>'
                    }
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-info" onclick="editarProduto('${prod.id}')" title="Editar">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-success" onclick="abrirMovimentacao('${prod.id}')" title="Movimentar">
                            <i class="fas fa-arrows-alt-v"></i>
                        </button>
                        <button class="btn btn-danger" onclick="deletarProduto('${prod.id}')" title="Deletar">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    });
    }
    
    // Modal novo produto
    const modalProduto = document.getElementById('modalProduto');
    if (modalProduto) {
        modalProduto.addEventListener('show.bs.modal', function () {
            if (!currentProdutoId) {
                novoFormulario();
            }
        });
    }

    // Formulário de chamadas
    const formChamada = document.getElementById('formChamada');
    if (formChamada) {
        formChamada.addEventListener('submit', function (e) {
            e.preventDefault();
            enviarChamada();
        });
    }

    // Filtro de tipo de chamado no dashboard
    const tipoChamadoFiltro = document.getElementById('tipoChamadoFiltro');
    if (tipoChamadoFiltro) {
        tipoChamadoFiltro.addEventListener('change', function () {
            tipoChamadoSelecionado = this.value || 'Todos';
            atualizarGraficoTiposChamadas();
        });
    }

    // Manipulação do sub-tipo baseado no tipo selecionado
    const chamadaTipo = document.getElementById('chamadaTipo');
    const subtipoContainer = document.getElementById('subtipoContainer');
    const chamadaSubtipo = document.getElementById('chamadaSubtipo');

    if (chamadaTipo) {
        chamadaTipo.addEventListener('change', function() {
            const tipo = this.value;
            const subtipoSelect = chamadaSubtipo;
            subtipoSelect.innerHTML = '<option value="" disabled selected>Selecione o problema específico</option>';

            if (tipo === 'Outros') {
                subtipoContainer.style.display = 'none';
                chamadaSubtipo.required = false;
            } else {
                subtipoContainer.style.display = 'block';
                chamadaSubtipo.required = true;

                const opcoes = {
                    'Equipamento defeituoso': ['Mouse', 'Teclado', 'Fone de ouvido', 'Webcam', 'Monitor'],
                    'Computador com erro': ['Computador travado', 'Tela azul', 'Aplicativo não abre'],
                    'Conexão com a internet': ['Carregamento lento', 'Desconexão', 'VPN'],
                    'Impressora': ['Obstrução de papel', 'Desligada', 'Falta de tinta', 'Não conecta', 'Imprime com falhas']
                };

                if (opcoes[tipo]) {
                    opcoes[tipo].forEach(opcao => {
                        const option = document.createElement('option');
                        option.value = opcao;
                        option.textContent = opcao;
                        subtipoSelect.appendChild(option);
                    });
                }
            }
        });
    }
}

function gerarCores(quantidade) {
    const cores = [
        '#0d6efd', '#198754', '#dc3545', '#ffc107', '#0dcaf0',
        '#6f42c1', '#e83e8c', '#fd7e14', '#20c997', '#6c757d'
    ];
    
    const resultado = [];
    for (let i = 0; i < quantidade; i++) {
        resultado.push(cores[i % cores.length]);
    }
    return resultado;
}

function formatarMoeda(valor) {
    return parseFloat(valor).toFixed(2).replace('.', ',');
}

// =============================================================================
// ADMIN (PANORAMA NO DASHBOARD)
// =============================================================================



// =============================================================================
// CONFIGURAÇÃO DE EVENTOS DE FORMS
// =============================================================================

function enviarChamada() {
    const tipo = document.getElementById('chamadaTipo').value;
    const subtipo = document.getElementById('chamadaSubtipo').value;
    const mensagem = document.getElementById('chamadaMensagem').value.trim();
    const fotoInput = document.getElementById('chamadaFoto');
    const foto = fotoInput && fotoInput.files ? fotoInput.files[0] : null;

    if (!tipo) {
        mostrarAviso('Por favor, selecione o tipo de chamada.');
        return;
    }

    if (tipo !== 'Outros' && !subtipo) {
        mostrarAviso('Por favor, selecione o problema específico.');
        return;
    }

    if (!mensagem) {
        mostrarAlerta('Por favor, digite uma mensagem.', 'warning');
        return;
    }

    if (foto) {
        const formatosPermitidos = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
        if (!formatosPermitidos.includes(foto.type)) {
            mostrarAlerta('Formato de imagem inválido. Use PNG, JPG, JPEG, GIF ou WEBP.', 'warning');
            return;
        }
        if (foto.size > 5 * 1024 * 1024) {
            mostrarAlerta('A foto deve ter no máximo 5MB.', 'warning');
            return;
        }
    }

    const formData = new FormData();
    formData.append('tipo', tipo);
    formData.append('subtipo', subtipo || '');
    formData.append('mensagem', mensagem);
    if (foto) {
        formData.append('foto_chamada', foto);
    }

    fetch(`${API_BASE}/chamadas`, {
        method: 'POST',
        body: formData
    })
    .then(async response => {
        const contentType = response.headers.get('Content-Type') || '';
        let data = {};

        if (contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            console.warn('Resposta não JSON ao enviar chamada:', text);
            throw new Error(text || 'Resposta inválida do servidor');
        }

        if (response.ok && data.mensagem) {
            mostrarSucesso('Chamada enviada com sucesso! Os administradores foram notificados.');
            const form = document.getElementById('formChamada');
            if (form) {
                form.reset();
                const subtipoContainer = document.getElementById('subtipoContainer');
                if (subtipoContainer) {
                    subtipoContainer.style.display = 'none';
                }
                const chamadaSubtipo = document.getElementById('chamadaSubtipo');
                if (chamadaSubtipo) {
                    chamadaSubtipo.required = false;
                }
            }
            carregarChamadasUsuario();
        } else {
            mostrarErro('Erro ao enviar chamada', new Error(data.erro || data.message || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        mostrarErro('Erro ao enviar chamada', error);
    });
}

// Autenticar e carregar dados iniciais
window.addEventListener('load', function () {
    if (window.USUARIO_IS_ADMIN === 'true' || window.USUARIO_IS_ADMIN === true) {
        showSection('dashboard');
    } else {
        showSection('chamadas');
    }
});
