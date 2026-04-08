// =============================================================================
// VARIÁVEIS GLOBAIS
// =============================================================================

let productsData = [];
let currentProdutoId = null;
let categoriasChart = null;
let topProdutosChart = null;

let chamadasUsuarioStatus = {};
let chamadasUsuarioPrimeiroLoad = true;

const API_BASE = window.location.origin + '/api';

// =============================================================================
// INICIALIZAÇÃO
// =============================================================================

document.addEventListener('DOMContentLoaded', function () {
    carregarDados();
    configurarEventos();

    // Exibição inicial conforme permissão de usuário
    if (window.USUARIO_IS_ADMIN === 'true' || window.USUARIO_IS_ADMIN === true) {
        showSection('dashboard');
    } else {
        showSection('chamadas');
    }

    // Recarregar dados a cada 1 minuto e 30 segundos
    setInterval(carregarDados, 90000);

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

function showSection(section) {
    // Ocultar todas as seções
    document.querySelectorAll('.section').forEach(el => {
        el.style.display = 'none';
    });
    
    // Mostrar seção selecionada
    const sectionId = section + '-section';
    document.getElementById(sectionId).style.display = 'block';
    
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

// =============================================================================
// CARREGAR DADOS
// =============================================================================

function carregarDados() {
    if (window.USUARIO_IS_ADMIN === 'true' || window.USUARIO_IS_ADMIN === true) {
        Promise.all([
            fetch(`${API_BASE}/produtos`).then(r => r.json()),
            fetch(`${API_BASE}/relatorios/resumo`).then(r => r.json())
        ])
        .then(([produtos, resumo]) => {
            productsData = produtos;
            atualizarKPIs(resumo);
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
        .catch(error => mostrarErro('Erro ao carregar dados', error));
    } else {
        atualizarEstoqueBaixo();
        carregarChamadasUsuario();
    }
}

function atualizarKPIs(resumo) {
    const totalProdutosEl = document.getElementById('kpi-total-produtos');
    if (!totalProdutosEl) return;

    document.getElementById('kpi-total-produtos').textContent = resumo.total_produtos;
    document.getElementById('kpi-quantidade').textContent = resumo.total_quantidades;
    document.getElementById('kpi-valor').textContent = 'R$ ' + formatarMoeda(resumo.valor_total);
    document.getElementById('kpi-baixo').textContent = resumo.produtos_estoque_baixo;
}

function atualizarEstoqueBaixo() {
    const tbody = document.getElementById('estoque-baixo-table');
    if (!tbody) return;

    fetch(`${API_BASE}/relatorios/estoque-baixo`)
        .then(r => r.json())
        .then(datos => {
            
            if (datos.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-success">✓ Todos os produtos estão acima do estoque mínimo!</td></tr>';
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
                        <button class="btn btn-sm btn-success" onclick="abrirMovimentacao('${escapeHtml(prod.id)}')">
                            <i class="fas fa-arrow-up"></i> Entrada
                        </button>
                    </td>
                </tr>
            `).join('');
        })
        .catch(error => console.error('Erro ao carregar estoque baixo:', error));
}

async function carregarChamadasUsuario() {
    const container = document.getElementById('lista-chamadas-usuario');
    if (!container) return;

    container.innerHTML = '<p class="text-muted">Carregando chamadas...</p>';

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
                if (anterior && anterior !== chamada.status) {
                    mostrarAlerta(`Atualização: a chamada "${escapeHtml(chamada.mensagem.substring(0, 40))}" foi alterada de ${statusLabelMap[anterior] || anterior} para ${statusLabel}.`, 'info');
                }
            }

            chamadasUsuarioStatus[chamada.id] = chamada.status;
            
            return `
                <div class="border rounded p-3 mb-3 ${chamada.status === 'concluida' ? 'bg-success-subtle' : chamada.lida ? 'bg-light' : 'bg-warning-subtle'}">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <strong>${escapeHtml(chamada.data_criacao)}</strong>
                        <span class="badge ${chamada.status === 'concluida' ? 'bg-success' : chamada.lida ? 'bg-secondary' : 'bg-danger'}">${statusLabel}</span>
                    </div>
                    <p class="mb-0">${escapeHtml(chamada.mensagem)}</p>
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
    atualizarGraficoCategorias();
    atualizarGraficoTopProdutos();
}

function atualizarGraficoCategorias() {
    fetch(`${API_BASE}/relatorios/por-categoria`)
        .then(r => r.json())
        .then(categorias => {
            const labels = categorias.map(c => c.categoria);
            const valores = categorias.map(c => c.valor_total);
            const cores = gerarCores(categorias.length);
            
            if (categoriasChart) {
                categoriasChart.destroy();
            }
            
            const ctx = document.getElementById('categoriasChart').getContext('2d');
            categoriasChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: valores,
                        backgroundColor: cores,
                        borderColor: '#fff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                font: { size: 12 },
                                padding: 15
                            }
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Erro ao carregar categorias:', error));
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
    
    if (productsData.length === 0) {
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
    .then(r => r.json())
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
        .then(r => r.json())
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



function mostrarAlerta(mensagem, tipo = 'info') {
    const alertaHtml = `
        <div class="alert alert-${tipo} alert-dismissible fade show" role="alert">
            ${mensagem}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const container = document.createElement('div');
    container.innerHTML = alertaHtml;
    document.querySelector('.container-fluid').insertBefore(
        container.firstElementChild, 
        document.querySelector('.container-fluid').firstElementChild
    );
    
    setTimeout(() => {
        const alert = document.querySelector('.alert');
        if (alert) alert.remove();
    }, 5000);
}

function mostrarErro(mensagem, error) {
    console.error(mensagem, error);
    mostrarAlerta(mensagem + ': ' + error.message, 'danger');
}

function enviarChamada() {
    const tipo = document.getElementById('chamadaTipo').value;
    const subtipo = document.getElementById('chamadaSubtipo').value;
    const mensagem = document.getElementById('chamadaMensagem').value.trim();

    if (!tipo) {
        mostrarAlerta('Por favor, selecione o tipo de chamada.', 'warning');
        return;
    }

    if (tipo !== 'Outros' && !subtipo) {
        mostrarAlerta('Por favor, selecione o problema específico.', 'warning');
        return;
    }

    if (!mensagem) {
        mostrarAlerta('Por favor, digite uma mensagem.', 'warning');
        return;
    }

    fetch(`${API_BASE}/chamadas`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            tipo: tipo,
            subtipo: subtipo,
            mensagem: mensagem
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.mensagem) {
            mostrarAlerta('Chamada enviada com sucesso! Os administradores foram notificados.', 'success');
            const form = document.getElementById('formChamada');
            if (form) {
                form.reset();
                // Ocultar sub-tipo após reset
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
            mostrarAlerta('Erro ao enviar chamada: ' + (data.erro || 'Erro desconhecido'), 'danger');
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
