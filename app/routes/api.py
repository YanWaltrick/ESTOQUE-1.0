from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import estoque
from app.utils import registrar_evento

api_bp = Blueprint('api', __name__)

def validar_dados_produto(dados, atualizar=False):
    erros = []

    if not dados:
        erros.append('JSON inválido ou vazio')
        return erros

    id_produto = dados.get('id') if not atualizar else None
    nome = dados.get('nome')
    categoria = dados.get('categoria')
    preco = dados.get('preco')
    quantidade = dados.get('quantidade')
    minimo = dados.get('minimo')

    if not atualizar:
        if not id_produto or not str(id_produto).strip():
            erros.append('ID do produto é obrigatório')

    if not nome or not str(nome).strip():
        erros.append('Nome é obrigatório')

    if not categoria or not str(categoria).strip():
        erros.append('Categoria é obrigatória')

    try:
        preco = float(preco)
        if preco < 0:
            erros.append('Preço não pode ser negativo')
    except Exception:
        erros.append('Preço inválido')

    try:
        quantidade = int(quantidade)
        if quantidade < 0:
            erros.append('Quantidade não pode ser negativa')
    except Exception:
        erros.append('Quantidade inválida')

    try:
        minimo = int(minimo)
        if minimo < 0:
            erros.append('Mínimo não pode ser negativo')
    except Exception:
        erros.append('Mínimo inválido')

    return erros

@api_bp.route('/produtos', methods=['GET'])
@login_required
def get_produtos():
    """Retorna lista de todos os produtos"""
    try:
        produtos = estoque.listar_produtos()
        return jsonify([prod.to_dict() for prod in produtos])
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@api_bp.route('/produtos/<id_produto>', methods=['GET'])
@login_required
def get_produto(id_produto):
    """Retorna um produto específico"""
    try:
        produto = estoque.buscar_produto(id_produto)
        if not produto:
            return jsonify({'erro': 'Produto não encontrado'}), 404

        return jsonify(produto.to_dict())
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@api_bp.route('/produtos', methods=['POST'])
@login_required
def criar_produto():
    """Cria um novo produto"""
    try:
        dados = request.get_json()
        erros = validar_dados_produto(dados, atualizar=False)
        if erros:
            return jsonify({'erro': ' | '.join(erros)}), 400

        sucesso = estoque.adicionar_produto(
            id_produto=str(dados['id']).strip(),
            nome=str(dados['nome']).strip(),
            categoria=str(dados['categoria']).strip(),
            preco=float(dados['preco']),
            quantidade=int(dados['quantidade']),
            minimo=int(dados['minimo']),
            localizacao=str(dados.get('localizacao', '')).strip()
        )

        if sucesso:
            registrar_evento(
                tipo_evento='produto_criado',
                descricao=f'Produto "{dados["nome"]}" (ID: {dados["id"]}) foi criado com sucesso'
            )
            return jsonify({'mensagem': 'Produto criado com sucesso'}), 201
        else:
            return jsonify({'erro': 'Falha ao criar produto'}), 400

    except Exception as e:
        return jsonify({'erro': str(e)}), 400

@api_bp.route('/produtos/<id_produto>', methods=['PUT'])
@login_required
def atualizar_produto(id_produto):
    """Atualiza um produto"""
    dados = request.get_json()
    produto = estoque.buscar_produto(id_produto)

    if not produto:
        return jsonify({'erro': 'Produto não encontrado'}), 404

    erros = validar_dados_produto(dados, atualizar=True)
    if erros:
        return jsonify({'erro': ' | '.join(erros)}), 400

    try:
        dados_update = {
            'nome': str(dados['nome']).strip(),
            'categoria': str(dados['categoria']).strip(),
            'preco': float(dados['preco']),
            'quantidade': int(dados['quantidade']),
            'minimo': int(dados['minimo']),
            'localizacao': str(dados.get('localizacao', '')).strip()
        }

        sucesso = estoque.atualizar_produto(id_produto, **dados_update)
        if not sucesso:
            return jsonify({'erro': 'Falha ao atualizar produto'}), 400

        produto_atualizado = estoque.buscar_produto(id_produto)
        return jsonify({
            'mensagem': 'Produto atualizado com sucesso',
            'produto': produto_atualizado.to_dict()
        })

    except Exception as e:
        return jsonify({'erro': str(e)}), 400

@api_bp.route('/produtos/<id_produto>', methods=['DELETE'])
@login_required
def deletar_produto(id_produto):
    """Delete um produto"""
    try:
        produto = estoque.buscar_produto(id_produto)
        nome_produto = produto.nome if produto else id_produto

        sucesso = estoque.remover_produto(id_produto)

        if sucesso:
            registrar_evento(
                tipo_evento='produto_deletado',
                descricao=f'Produto "{nome_produto}" (ID: {id_produto}) foi removido'
            )
            return jsonify({'mensagem': 'Produto removido com sucesso'})
        else:
            return jsonify({'erro': 'Produto não encontrado'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@api_bp.route('/entrada', methods=['POST'])
@login_required
def entrada_estoque():
    """Registra entrada de produtos"""
    try:
        dados = request.get_json()

        sucesso = estoque.entrada_estoque(
            id_produto=dados['id'],
            quantidade=int(dados['quantidade']),
            motivo=dados.get('motivo', ''),
            usuario=dados.get('usuario', '')
        )

        if sucesso:
            registrar_evento(
                tipo_evento='entrada_estoque',
                descricao=f'Entrada de {dados["quantidade"]} unidades do produto ID: {dados["id"]} - Motivo: {dados.get("motivo", "Não informado")}'
            )
            return jsonify({'mensagem': 'Entrada registrada com sucesso'})
        else:
            return jsonify({'erro': 'Falha ao registrar entrada'}), 400

    except Exception as e:
        return jsonify({'erro': str(e)}), 400

@api_bp.route('/saida', methods=['POST'])
@login_required
def saida_estoque():
    """Registra saída de produtos"""
    try:
        dados = request.get_json()

        sucesso = estoque.saida_estoque(
            id_produto=dados['id'],
            quantidade=int(dados['quantidade']),
            motivo=dados.get('motivo', ''),
            usuario=dados.get('usuario', '')
        )

        if sucesso:
            registrar_evento(
                tipo_evento='saida_estoque',
                descricao=f'Saída de {dados["quantidade"]} unidades do produto ID: {dados["id"]} - Motivo: {dados.get("motivo", "Não informado")}'
            )
            return jsonify({'mensagem': 'Saída registrada com sucesso'})
        else:
            return jsonify({'erro': 'Falha ao registrar saída'}), 400

    except Exception as e:
        return jsonify({'erro': str(e)}), 400

@api_bp.route('/relatorios/resumo', methods=['GET'])
@login_required
def relatorio_resumo():
    """Retorna resumo do estoque"""
    try:
        estatisticas = estoque.relatorio_valor_total()
        produtos_baixo = len(estoque.relatorio_estoque_baixo())
        return jsonify({
            'estatisticas': estatisticas,
            'produtos_baixo_estoque': produtos_baixo
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500