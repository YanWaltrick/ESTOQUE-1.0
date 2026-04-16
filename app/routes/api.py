from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import app
from app.auth import require_role
from app.auth.security import PasswordValidator, validate_username
from app.database import db
from app.models import User, Chamada, Historico
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

@api_bp.route('/users', methods=['GET'])
@login_required
@require_role('admin')
def get_users():
    """Retorna lista de todos os usuários"""
    try:
        usuarios = User.query.order_by(User.username).all()
        return jsonify([usuario.to_dict() for usuario in usuarios])
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@api_bp.route('/produtos', methods=['GET'])
@login_required
def get_produtos():
    """Retorna lista de todos os produtos"""
    try:
        produtos = app.estoque.listar_produtos()
        return jsonify([prod.to_dict() for prod in produtos])
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@api_bp.route('/produtos/<id_produto>', methods=['GET'])
@login_required
def get_produto(id_produto):
    """Retorna um produto específico"""
    try:
        produto = app.estoque.buscar_produto(id_produto)
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

        sucesso = app.estoque.adicionar_produto(
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
    produto = app.estoque.buscar_produto(id_produto)

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

        sucesso = app.estoque.atualizar_produto(id_produto, **dados_update)
        if not sucesso:
            return jsonify({'erro': 'Falha ao atualizar produto'}), 400

        produto_atualizado = app.estoque.buscar_produto(id_produto)
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
        produto = app.estoque.buscar_produto(id_produto)
        nome_produto = produto.nome if produto else id_produto

        sucesso = app.estoque.remover_produto(id_produto)

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

        sucesso = app.estoque.entrada_estoque(
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

        sucesso = app.estoque.saida_estoque(
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
        estatisticas = app.estoque.relatorio_valor_total()
        produtos_baixo = len(app.estoque.relatorio_estoque_baixo())
        return jsonify({
            'estatisticas': estatisticas,
            'produtos_baixo_estoque': produtos_baixo
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@api_bp.route('/relatorios/estoque-baixo', methods=['GET'])
@login_required
def relatorio_estoque_baixo():
    try:
        produtos = app.estoque.relatorio_estoque_baixo()
        result = []
        for produto in produtos:
            faltam = max(produto.minimo - produto.quantidade, 0)
            result.append({
                'id': produto.id_produto,
                'nome': produto.nome,
                'categoria': produto.categoria,
                'quantidade': produto.quantidade,
                'minimo': produto.minimo,
                'localizacao': produto.localizacao,
                'valor_total': produto.valor_total(),
                'faltam': faltam,
                'data_criacao': produto.data_criacao.strftime('%d/%m/%Y %H:%M:%S') if produto.data_criacao else None,
                'data_atualizacao': produto.data_atualizacao.strftime('%d/%m/%Y %H:%M:%S') if produto.data_atualizacao else None
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@api_bp.route('/relatorios/top-produtos', methods=['GET'])
@login_required
def relatorio_top_produtos():
    try:
        produtos = app.estoque.listar_produtos()
        produtos_ordenados = sorted(produtos, key=lambda p: p.valor_total(), reverse=True)
        result = [
            {
                'id': p.id_produto,
                'nome': p.nome,
                'preco': p.preco,
                'quantidade': p.quantidade,
                'valor_total': p.valor_total()
            }
            for p in produtos_ordenados[:10]
        ]
        return jsonify(result)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@api_bp.route('/relatorios/por-categoria', methods=['GET'])
@login_required
def relatorio_por_categoria():
    try:
        dados = app.estoque.relatorio_por_categoria()
        return jsonify([
            {
                'categoria': categoria,
                'produtos': valores['total_produtos'],
                'quantidade': valores['total_unidades'],
                'valor_total': valores['valor_total']
            }
            for categoria, valores in dados.items()
        ])
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@api_bp.route('/historico', methods=['GET'])
@login_required
@require_role('admin')
def historico():
    try:
        query = Historico.query.order_by(Historico.data_evento.desc())
        tipo = request.args.get('tipo', '').strip()
        limit = request.args.get('limit', type=int)

        if tipo:
            query = query.filter_by(tipo_evento=tipo)

        if limit and limit > 0:
            query = query.limit(limit)

        eventos = query.all()
        return jsonify([evento.to_dict() for evento in eventos])
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@api_bp.route('/users', methods=['POST'])
@login_required
@require_role('admin')
def criar_usuario_api():
    try:
        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({'erro': 'JSON inválido ou vazio'}), 400

        username = (dados.get('username') or '').strip()
        password = dados.get('password') or ''
        role = (dados.get('role') or 'usuario').strip()
        if role == 'user':
            role = 'usuario'
        area = (dados.get('area') or '').strip()
        localizacao = (dados.get('localizacao') or '').strip()

        is_valid_user, user_error = validate_username(username)
        if not is_valid_user:
            return jsonify({'erro': user_error}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'erro': 'Usuário com este nome já existe.'}), 400

        is_valid_pass, pass_errors = PasswordValidator.validate(password)
        if not is_valid_pass:
            return jsonify({'erro': '; '.join(pass_errors)}), 400

        if role not in ['admin', 'usuario']:
            return jsonify({'erro': 'Role inválido. Escolha entre admin ou usuario.'}), 400

        novo_usuario = User(
            username=username,
            password=PasswordValidator.hash_password(password),
            role=role,
            area=area,
            localizacao=localizacao
        )
        db.session.add(novo_usuario)
        db.session.commit()

        registrar_evento(
            tipo_evento='usuario_criado',
            descricao=f'Novo usuário criado: "{username}" com role "{role}"',
            usuario_responsavel=current_user.username
        )

        return jsonify({'mensagem': 'Usuário criado com sucesso'}), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@api_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
@require_role('admin')
def deletar_usuario_api(user_id):
    try:
        usuario = User.query.get(user_id)
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        if usuario.id == current_user.id:
            return jsonify({'erro': 'Você não pode deletar sua própria conta.'}), 403

        if usuario.role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                return jsonify({'erro': 'Não é possível deletar o último administrador.'}), 403

        db.session.delete(usuario)
        db.session.commit()
        registrar_evento(
            tipo_evento='usuario_deletado',
            descricao=f'Usuário "{usuario.username}" foi deletado',
            usuario_responsavel=current_user.username
        )
        return jsonify({'mensagem': 'Usuário removido com sucesso'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@api_bp.route('/users/me/password', methods=['PUT'])
@login_required
def atualizar_senha_atual_api():
    try:
        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({'erro': 'JSON inválido ou vazio'}), 400

        senha_atual = dados.get('senha_atual', '')
        senha_atual_rep = dados.get('senha_atual_rep', '')
        nova_senha = dados.get('nova_senha', '')
        confirm_nova_senha = dados.get('confirm_nova_senha', '')

        if not senha_atual or not senha_atual_rep or not nova_senha or not confirm_nova_senha:
            return jsonify({'erro': 'Todos os campos são obrigatórios.'}), 400

        if senha_atual != senha_atual_rep:
            return jsonify({'erro': 'A senha atual deve ser confirmada corretamente.'}), 400

        if not PasswordValidator.verify_password(senha_atual, current_user.password):
            return jsonify({'erro': 'Senha atual incorreta.'}), 400

        if nova_senha != confirm_nova_senha:
            return jsonify({'erro': 'A nova senha deve ser digitada duas vezes de forma idêntica.'}), 400

        if nova_senha == senha_atual:
            return jsonify({'erro': 'A nova senha deve ser diferente da senha atual.'}), 400

        is_valid, errors = PasswordValidator.validate(nova_senha)
        if not is_valid:
            return jsonify({'erro': '; '.join(errors)}), 400

        current_user.password = PasswordValidator.hash_password(nova_senha)
        db.session.commit()

        registrar_evento(
            tipo_evento='senha_alterada',
            descricao='Senha atualizada com sucesso',
            usuario_responsavel=current_user.username
        )

        return jsonify({'mensagem': 'Senha atualizada com sucesso'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@api_bp.route('/users/<int:user_id>/reset-password', methods=['PUT'])
@login_required
@require_role('admin')
def resetar_senha_usuario_api(user_id):
    try:
        usuario = User.query.get(user_id)
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({'erro': 'JSON inválido ou vazio'}), 400

        nova_senha = dados.get('nova_senha', '')
        confirm_nova_senha = dados.get('confirm_nova_senha', '')

        if not nova_senha or not confirm_nova_senha:
            return jsonify({'erro': 'Todos os campos são obrigatórios.'}), 400

        if nova_senha != confirm_nova_senha:
            return jsonify({'erro': 'A nova senha deve ser digitada duas vezes de forma idêntica.'}), 400

        is_valid, errors = PasswordValidator.validate(nova_senha)
        if not is_valid:
            return jsonify({'erro': '; '.join(errors)}), 400

        usuario.password = PasswordValidator.hash_password(nova_senha)
        usuario.tentativas_login_falhas = 0
        usuario.bloqueado_ate = None
        db.session.commit()

        registrar_evento(
            tipo_evento='senha_resetada',
            descricao=f'Senha do usuário "{usuario.username}" resetada pelo admin',
            usuario_responsavel=current_user.username
        )

        return jsonify({'mensagem': 'Senha do usuário redefinida com sucesso'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


def validar_dados_chamada(dados):
    erros = []
    if not dados or not isinstance(dados, dict):
        erros.append('JSON inválido ou vazio')
        return erros

    tipo = (dados.get('tipo') or '').strip()
    subtipo = (dados.get('subtipo') or '').strip()
    mensagem = (dados.get('mensagem') or '').strip()

    if not tipo:
        erros.append('Tipo de chamado é obrigatório')
    if tipo != 'Outros' and not subtipo:
        erros.append('Subtipo é obrigatório para o tipo selecionado')
    if not mensagem:
        erros.append('Mensagem é obrigatória')

    return erros


def montar_texto_chamada(tipo, subtipo, mensagem):
    if not tipo or tipo == 'Outros':
        return mensagem
    if subtipo:
        return f'[{tipo} - {subtipo}] {mensagem}'
    return f'[{tipo}] {mensagem}'


@api_bp.route('/chamadas', methods=['GET'])
@login_required
def listar_chamadas():
    """Lista chamadas do usuário ou de todos os usuários para admins."""
    try:
        query = Chamada.query.order_by(Chamada.data_criacao.desc())
        limit = request.args.get('limit', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date:
            try:
                start_date_obj = datetime.fromisoformat(start_date)
                query = query.filter(Chamada.data_criacao >= start_date_obj)
            except ValueError:
                return jsonify({'erro': 'Data de início inválida'}), 400

        if end_date:
            try:
                end_date_obj = datetime.fromisoformat(end_date)
                query = query.filter(Chamada.data_criacao <= end_date_obj)
            except ValueError:
                return jsonify({'erro': 'Data de fim inválida'}), 400

        if not current_user.is_admin:
            query = query.filter_by(id_usuario=current_user.id)

        if limit and limit > 0:
            query = query.limit(limit)

        chamadas = query.all()
        return jsonify([chamada.to_dict() for chamada in chamadas])
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@api_bp.route('/chamadas', methods=['POST'])
@login_required
def criar_chamada():
    """Cria uma nova chamada para admins."""
    try:
        dados = request.get_json(silent=True)
        erros = validar_dados_chamada(dados)
        if erros:
            return jsonify({'erro': ' | '.join(erros)}), 400

        texto = montar_texto_chamada(dados.get('tipo'), dados.get('subtipo'), dados.get('mensagem'))
        chamada = Chamada(id_usuario=current_user.id, mensagem=texto)
        db.session.add(chamada)
        db.session.commit()

        registrar_evento(
            tipo_evento='chamada_criada',
            descricao=f'Chamada criada por {current_user.username}: {texto}',
            usuario_responsavel=current_user.username
        )

        return jsonify({'mensagem': 'Chamada enviada com sucesso'}), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 400


@api_bp.route('/chamadas/nao-lidas', methods=['GET'])
@login_required
@require_role('admin')
def contar_chamadas_nao_lidas():
    try:
        nao_lidas = Chamada.query.filter_by(lida=False).count()
        return jsonify({'nao_lidas': nao_lidas})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@api_bp.route('/chamadas/<int:id_chamada>/status', methods=['PUT'])
@login_required
@require_role('admin')
def atualizar_status_chamada(id_chamada):
    try:
        dados = request.get_json(silent=True) or {}
        status = (dados.get('status') or '').strip().lower()
        if status not in ['nova', 'lida', 'analise', 'execucao', 'concluida']:
            return jsonify({'erro': 'Status inválido'}), 400

        chamada = Chamada.query.get(id_chamada)
        if not chamada:
            return jsonify({'erro': 'Chamada não encontrada'}), 404

        chamada.status = status
        chamada.lida = status in ['lida', 'analise', 'execucao', 'concluida']
        db.session.commit()

        registrar_evento(
            tipo_evento='chamada_status_alterado',
            descricao=f'Chamada {id_chamada} alterada para status {status}',
            usuario_responsavel=current_user.username
        )

        return jsonify({'mensagem': 'Status atualizado com sucesso'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@api_bp.route('/chamadas/<int:id_chamada>/ler', methods=['PUT'])
@login_required
@require_role('admin')
def marcar_chamada_como_lida(id_chamada):
    try:
        chamada = Chamada.query.get(id_chamada)
        if not chamada:
            return jsonify({'erro': 'Chamada não encontrada'}), 404

        chamada.lida = True
        if chamada.status == 'nova':
            chamada.status = 'lida'
        db.session.commit()

        registrar_evento(
            tipo_evento='chamada_lida',
            descricao=f'Chamada {id_chamada} marcada como lida',
            usuario_responsavel=current_user.username
        )

        return jsonify({'mensagem': 'Chamada marcada como lida'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
