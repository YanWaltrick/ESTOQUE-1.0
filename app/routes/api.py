import os
import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from flask_mail import Message
from sqlalchemy import case
from werkzeug.utils import secure_filename

import app
from app.auth import require_role
from app.auth.security import PasswordValidator, validate_email, validate_username
from app.database import db, mail
from app.models import Chamada, Historico, TermoEntrega, User
from app.services import enviar_notificacao_chamada
from app.utils import registrar_evento

api_bp = Blueprint("api", __name__)


def _smtp_configurado() -> bool:
    return bool(
        current_app.config.get("MAIL_SERVER") and current_app.config.get("MAIL_DEFAULT_SENDER")
    )


def _notificar_usuario_chamado_concluido(chamada: Chamada) -> tuple[bool, str]:
    if not _smtp_configurado():
        return True, ""

    usuario = chamada.usuario
    if not usuario:
        return True, ""

    destinatario = None
    if usuario.email:
        is_valid, _ = validate_email(usuario.email)
        if is_valid:
            destinatario = usuario.email.strip()

    if not destinatario:
        is_valid_username_email, _ = validate_email(usuario.username)
        if is_valid_username_email:
            destinatario = usuario.username.strip()

    if not destinatario:
        return True, ""

    try:
        assunto = "[SOMA ASSET] Seu chamado foi concluído"
        corpo = (
            "Olá,\n\n"
            "O seu chamado foi concluído. Veja os detalhes abaixo:\n\n"
            f"ID do chamado: {chamada.id_chamada}\n"
            f"Status: {chamada.status}\n"
            f"Mensagem: {chamada.mensagem}\n\n"
            "Se precisar de suporte adicional, responda a este e-mail ou abra um novo chamado no sistema.\n\n"
            "Atenciosamente,\n"
            "Equipe de TI"
        )
        msg = Message(subject=assunto, recipients=[destinatario], body=corpo)
        mail.send(msg)
        return True, ""
    except Exception as e:
        current_app.logger.error("Falha ao enviar email de conclusão de chamado: %s", str(e))
        return False, str(e)


def validar_dados_produto(dados, atualizar=False):
    erros = []

    if not dados:
        erros.append("JSON inválido ou vazio")
        return erros

    id_produto = dados.get("id") if not atualizar else None
    nome = dados.get("nome")
    categoria = dados.get("categoria")
    preco = dados.get("preco")
    quantidade = dados.get("quantidade")
    minimo = dados.get("minimo")

    if not atualizar:
        if not id_produto or not str(id_produto).strip():
            erros.append("ID do produto é obrigatório")

    if not nome or not str(nome).strip():
        erros.append("Nome é obrigatório")

    if not categoria or not str(categoria).strip():
        erros.append("Categoria é obrigatória")

    try:
        preco = float(preco)
        if preco < 0:
            erros.append("Preço não pode ser negativo")
    except Exception:
        erros.append("Preço inválido")

    try:
        quantidade = int(quantidade)
        if quantidade < 0:
            erros.append("Quantidade não pode ser negativa")
    except Exception:
        erros.append("Quantidade inválida")

    try:
        minimo = int(minimo)
        if minimo < 0:
            erros.append("Mínimo não pode ser negativo")
    except Exception:
        erros.append("Mínimo inválido")

    return erros


@api_bp.route("/users", methods=["GET"])
@login_required
@require_role("admin")
def get_users():
    """Retorna lista de todos os usuários"""
    try:
        usuarios = User.query.order_by(
            case((User.tipo_contrato == "CLT", 0), else_=1), User.ativo.desc(), User.username.asc()
        ).all()
        return jsonify([usuario.to_dict() for usuario in usuarios])
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/users/<int:user_id>", methods=["GET"])
@login_required
@require_role("admin")
def get_user_details(user_id):
    """Retorna detalhes completos de um usuário específico"""
    try:
        usuario = User.query.get_or_404(user_id)
        return jsonify(usuario.to_dict())
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/users/<int:user_id>", methods=["PUT"])
@login_required
@require_role("admin")
def atualizar_usuario_api(user_id):
    """Atualiza dados de um usuário existente"""
    try:
        usuario = User.query.get_or_404(user_id)

        if usuario.id == current_user.id:
            return jsonify(
                {"erro": "Você não pode editar sua própria conta aqui. Use a página de perfil."}
            ), 403

        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({"erro": "JSON inválido ou vazio"}), 400

        role = (dados.get("role") or usuario.role).strip()
        tipo_contrato = (dados.get("tipo_contrato") or usuario.tipo_contrato).strip().upper()
        area = (dados.get("area") or "").strip()
        localizacao = (dados.get("localizacao") or "").strip()
        empresa = (dados.get("empresa") or "").strip()
        cnpj = (dados.get("cnpj") or "").strip()
        endereco = (dados.get("endereco") or "").strip()
        cargo = (dados.get("cargo") or "").strip()
        cpf = (dados.get("cpf") or "").strip()
        email = (dados.get("email") or "").strip()
        departamento = (dados.get("departamento") or "").strip()
        local_trabalho = (dados.get("local_trabalho") or "").strip()
        pj_contratante = (dados.get("pj_contratante") or "").strip()
        pj_contratante_cnpj = (dados.get("pj_contratante_cnpj") or "").strip()
        pj_contratante_endereco = (dados.get("pj_contratante_endereco") or "").strip()
        pj_contratada = (dados.get("pj_contratada") or "").strip()
        pj_contratada_cnpj = (dados.get("pj_contratada_cnpj") or "").strip()
        data_admissao_str = (dados.get("data_admissao") or "").strip()
        pj_data_contrato_str = (dados.get("pj_data_contrato") or "").strip()
        ativo = dados.get("ativo", usuario.ativo)
        if isinstance(ativo, str):
            ativo = ativo.lower() in ("1", "true", "on", "yes", "ativo")

        if role not in ["admin", "usuario"]:
            return jsonify({"erro": "Role inválido. Escolha entre admin ou usuario."}), 400

        if tipo_contrato not in ["CLT", "PJ"]:
            return jsonify({"erro": "Tipo de contrato inválido. Escolha entre CLT ou PJ."}), 400

        if email:
            is_valid_email, email_error = validate_email(email)
            if not is_valid_email:
                return jsonify({"erro": f"Erro no email: {email_error}"}), 400

        data_admissao = usuario.data_admissao
        if data_admissao_str:
            try:
                data_admissao = datetime.strptime(data_admissao_str, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"erro": "Erro ao processar a data de admissão."}), 400
        else:
            data_admissao = None

        pj_data_contrato = usuario.pj_data_contrato
        if pj_data_contrato_str:
            try:
                pj_data_contrato = datetime.strptime(pj_data_contrato_str, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"erro": "Erro ao processar a data do contrato PJ."}), 400
        else:
            pj_data_contrato = None

        if usuario.role == "admin" and role != "admin":
            admin_count = User.query.filter_by(role="admin").count()
            if admin_count <= 1:
                return jsonify({"erro": "Não é possível remover o último administrador."}), 403

        usuario.role = role
        usuario.tipo_contrato = tipo_contrato
        usuario.area = area
        usuario.localizacao = localizacao
        usuario.empresa = empresa
        usuario.cnpj = cnpj
        usuario.endereco = endereco
        usuario.cargo = cargo
        usuario.cpf = cpf
        usuario.email = email
        usuario.data_admissao = data_admissao
        usuario.departamento = departamento
        usuario.local_trabalho = local_trabalho
        usuario.pj_contratante = pj_contratante
        usuario.pj_contratante_cnpj = pj_contratante_cnpj
        usuario.pj_contratante_endereco = pj_contratante_endereco
        usuario.pj_contratada = pj_contratada
        usuario.pj_contratada_cnpj = pj_contratada_cnpj
        usuario.pj_data_contrato = pj_data_contrato
        usuario.ativo = bool(ativo)

        db.session.commit()

        registrar_evento(
            tipo_evento="usuario_editado",
            descricao=f'Usuário "{usuario.username}" editado via modal - role: "{role}", tipo: "{tipo_contrato}", ativo: {usuario.ativo}',
            usuario_responsavel=current_user.username,
        )

        return jsonify({"mensagem": "Usuário atualizado com sucesso", "usuario": usuario.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/produtos", methods=["GET"])
@login_required
def get_produtos():
    """Retorna lista de todos os produtos"""
    try:
        produtos = app.estoque.listar_produtos()
        return jsonify([prod.to_dict() for prod in produtos])
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/produtos/<id_produto>", methods=["GET"])
@login_required
def get_produto(id_produto):
    """Retorna um produto específico"""
    try:
        produto = app.estoque.buscar_produto(id_produto)
        if not produto:
            return jsonify({"erro": "Produto não encontrado"}), 404

        return jsonify(produto.to_dict())
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/produtos", methods=["POST"])
@login_required
@require_role("admin")
def criar_produto():
    """Cria um novo produto"""
    try:
        dados = request.get_json()
        erros = validar_dados_produto(dados, atualizar=False)
        if erros:
            return jsonify({"erro": " | ".join(erros)}), 400

        sucesso = app.estoque.adicionar_produto(
            id_produto=str(dados["id"]).strip(),
            nome=str(dados["nome"]).strip(),
            categoria=str(dados["categoria"]).strip(),
            preco=float(dados["preco"]),
            quantidade=int(dados["quantidade"]),
            minimo=int(dados["minimo"]),
            localizacao=str(dados.get("localizacao", "")).strip(),
        )

        if sucesso:
            registrar_evento(
                tipo_evento="produto_criado",
                descricao=f'Produto "{dados["nome"]}" (ID: {dados["id"]}) foi criado com sucesso',
            )
            return jsonify({"mensagem": "Produto criado com sucesso"}), 201
        else:
            return jsonify({"erro": "Falha ao criar produto"}), 400

    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@api_bp.route("/produtos/<id_produto>", methods=["PUT"])
@login_required
@require_role("admin")
def atualizar_produto(id_produto):
    """Atualiza um produto"""
    dados = request.get_json()
    produto = app.estoque.buscar_produto(id_produto)

    if not produto:
        return jsonify({"erro": "Produto não encontrado"}), 404

    erros = validar_dados_produto(dados, atualizar=True)
    if erros:
        return jsonify({"erro": " | ".join(erros)}), 400

    try:
        dados_update = {
            "nome": str(dados["nome"]).strip(),
            "categoria": str(dados["categoria"]).strip(),
            "preco": float(dados["preco"]),
            "quantidade": int(dados["quantidade"]),
            "minimo": int(dados["minimo"]),
            "localizacao": str(dados.get("localizacao", "")).strip(),
        }

        sucesso = app.estoque.atualizar_produto(id_produto, **dados_update)
        if not sucesso:
            return jsonify({"erro": "Falha ao atualizar produto"}), 400

        produto_atualizado = app.estoque.buscar_produto(id_produto)
        return jsonify(
            {"mensagem": "Produto atualizado com sucesso", "produto": produto_atualizado.to_dict()}
        )

    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@api_bp.route("/produtos/<id_produto>", methods=["DELETE"])
@login_required
@require_role("admin")
def deletar_produto(id_produto):
    """Delete um produto"""
    try:
        produto = app.estoque.buscar_produto(id_produto)
        nome_produto = produto.nome if produto else id_produto

        sucesso = app.estoque.remover_produto(id_produto)

        if sucesso:
            registrar_evento(
                tipo_evento="produto_deletado",
                descricao=f'Produto "{nome_produto}" (ID: {id_produto}) foi removido',
            )
            return jsonify({"mensagem": "Produto removido com sucesso"})
        else:
            return jsonify({"erro": "Produto não encontrado"}), 404
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/entrada", methods=["POST"])
@login_required
@require_role("admin")
def entrada_estoque():
    """Registra entrada de produtos"""
    try:
        dados = request.get_json()

        sucesso = app.estoque.entrada_estoque(
            id_produto=dados["id"],
            quantidade=int(dados["quantidade"]),
            motivo=dados.get("motivo", ""),
            usuario=dados.get("usuario", ""),
        )

        if sucesso:
            registrar_evento(
                tipo_evento="entrada_estoque",
                descricao=f"Entrada de {dados['quantidade']} unidades do produto ID: {dados['id']} - Motivo: {dados.get('motivo', 'Não informado')}",
            )
            return jsonify({"mensagem": "Entrada registrada com sucesso"})
        else:
            return jsonify({"erro": "Falha ao registrar entrada"}), 400

    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@api_bp.route("/saida", methods=["POST"])
@login_required
@require_role("admin")
def saida_estoque():
    """Registra saída de produtos"""
    try:
        dados = request.get_json()

        sucesso = app.estoque.saida_estoque(
            id_produto=dados["id"],
            quantidade=int(dados["quantidade"]),
            motivo=dados.get("motivo", ""),
            usuario=dados.get("usuario", ""),
        )

        if sucesso:
            registrar_evento(
                tipo_evento="saida_estoque",
                descricao=f"Saída de {dados['quantidade']} unidades do produto ID: {dados['id']} - Motivo: {dados.get('motivo', 'Não informado')}",
            )
            return jsonify({"mensagem": "Saída registrada com sucesso"})
        else:
            return jsonify({"erro": "Falha ao registrar saída"}), 400

    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@api_bp.route("/relatorios/resumo", methods=["GET"])
@login_required
def relatorio_resumo():
    """Retorna resumo do estoque e resumo de chamadas para dashboard"""
    try:
        estatisticas = app.estoque.relatorio_valor_total()
        produtos_baixo = len(app.estoque.relatorio_estoque_baixo())

        sete_dias_atras = datetime.now(timezone(timedelta(hours=-3))) - timedelta(days=7)
        chamadas_analise = Chamada.query.filter_by(status="analise").count()
        chamadas_execucao = Chamada.query.filter_by(status="execucao").count()
        chamadas_novas = Chamada.query.filter_by(status="nova").count()
        chamadas_finalizadas_7dias = Chamada.query.filter(
            Chamada.status == "concluida", Chamada.data_criacao >= sete_dias_atras
        ).count()
        chamadas_abertas = Chamada.query.filter(
            Chamada.status.in_(["nova", "analise", "execucao"])
        ).count()

        return jsonify(
            {
                "estatisticas": estatisticas,
                "produtos_estoque_baixo": produtos_baixo,
                "chamadas_analise": chamadas_analise,
                "chamadas_execucao": chamadas_execucao,
                "chamadas_abertas": chamadas_abertas,
                "chamadas_novas": chamadas_novas,
                "chamadas_finalizadas_7dias": chamadas_finalizadas_7dias,
            }
        )
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/relatorios/estoque-baixo", methods=["GET"])
@login_required
def relatorio_estoque_baixo():
    try:
        produtos = app.estoque.relatorio_estoque_baixo()
        result = []
        for produto in produtos:
            faltam = max(produto.minimo - produto.quantidade, 0)
            result.append(
                {
                    "id": produto.id_produto,
                    "nome": produto.nome,
                    "categoria": produto.categoria,
                    "quantidade": produto.quantidade,
                    "minimo": produto.minimo,
                    "localizacao": produto.localizacao,
                    "valor_total": produto.valor_total(),
                    "faltam": faltam,
                    "data_criacao": produto.data_criacao.strftime("%d/%m/%Y %H:%M:%S")
                    if produto.data_criacao
                    else None,
                    "data_atualizacao": produto.data_atualizacao.strftime("%d/%m/%Y %H:%M:%S")
                    if produto.data_atualizacao
                    else None,
                }
            )
        return jsonify(result)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/relatorios/top-produtos", methods=["GET"])
@login_required
def relatorio_top_produtos():
    try:
        produtos = app.estoque.listar_produtos()
        produtos_ordenados = sorted(produtos, key=lambda p: p.valor_total(), reverse=True)
        result = [
            {
                "id": p.id_produto,
                "nome": p.nome,
                "preco": p.preco,
                "quantidade": p.quantidade,
                "valor_total": p.valor_total(),
            }
            for p in produtos_ordenados[:10]
        ]
        return jsonify(result)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/relatorios/por-categoria", methods=["GET"])
@login_required
def relatorio_por_categoria():
    try:
        dados = app.estoque.relatorio_por_categoria()
        return jsonify(
            [
                {
                    "categoria": categoria,
                    "produtos": valores["total_produtos"],
                    "quantidade": valores["total_unidades"],
                    "valor_total": valores["valor_total"],
                }
                for categoria, valores in dados.items()
            ]
        )
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/historico", methods=["GET"])
@login_required
@require_role("admin")
def historico():
    try:
        query = Historico.query.order_by(Historico.data_evento.desc())
        tipo = request.args.get("tipo", "").strip()
        limit = request.args.get("limit", type=int)

        if tipo:
            query = query.filter_by(tipo_evento=tipo)

        if limit and limit > 0:
            query = query.limit(limit)

        eventos = query.all()
        return jsonify([evento.to_dict() for evento in eventos])
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/users", methods=["POST"])
@login_required
@require_role("admin")
def criar_usuario_api():
    try:
        if request.content_type and request.content_type.startswith("multipart/form-data"):
            dados = request.form
        else:
            dados = request.get_json(silent=True)
        if not dados:
            return jsonify({"erro": "JSON inválido ou vazio"}), 400

        username = (dados.get("username") or "").strip()
        password = dados.get("password") or ""
        role = (dados.get("role") or "usuario").strip()
        if role == "user":
            role = "usuario"
        tipo_contrato = (dados.get("tipo_contrato") or "CLT").strip().upper()
        area = (dados.get("area") or "").strip()
        localizacao = (dados.get("localizacao") or "").strip()
        empresa = (dados.get("empresa") or "").strip()
        cnpj = (dados.get("cnpj") or "").strip()
        endereco = (dados.get("endereco") or "").strip()
        cargo = (dados.get("cargo") or "").strip()
        cpf = (dados.get("cpf") or "").strip()
        email = (dados.get("email") or "").strip()
        departamento = (dados.get("departamento") or "").strip()
        local_trabalho = (dados.get("local_trabalho") or "").strip()
        pj_contratante = (dados.get("pj_contratante") or "").strip()
        pj_contratante_cnpj = (dados.get("pj_contratante_cnpj") or "").strip()
        pj_contratante_endereco = (dados.get("pj_contratante_endereco") or "").strip()
        pj_contratada = (dados.get("pj_contratada") or "").strip()
        pj_contratada_cnpj = (dados.get("pj_contratada_cnpj") or "").strip()
        pj_data_contrato_str = (dados.get("pj_data_contrato") or "").strip()
        foto_perfil_file = request.files.get("foto_perfil")

        # Converter data_admissao
        data_admissao = None
        data_admissao_str = (dados.get("data_admissao") or "").strip()
        if data_admissao_str:
            try:
                from datetime import datetime

                data_admissao = datetime.strptime(data_admissao_str, "%Y-%m-%d").date()
            except Exception:
                return jsonify({"erro": "Erro ao processar a data de admissão."}), 400

        pj_data_contrato = None
        if pj_data_contrato_str:
            try:
                from datetime import datetime

                pj_data_contrato = datetime.strptime(pj_data_contrato_str, "%Y-%m-%d").date()
            except Exception:
                return jsonify({"erro": "Erro ao processar a data do contrato PJ."}), 400

        is_valid_user, user_error = validate_username(username)
        if not is_valid_user:
            return jsonify({"erro": user_error}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({"erro": "Usuário com este nome já existe."}), 400

        is_valid_pass, pass_errors = PasswordValidator.validate(password)
        if not is_valid_pass:
            return jsonify({"erro": "; ".join(pass_errors)}), 400

        if role not in ["admin", "usuario"]:
            return jsonify({"erro": "Role inválido. Escolha entre admin ou usuario."}), 400

        if tipo_contrato not in ["CLT", "PJ"]:
            return jsonify({"erro": "Tipo de contrato inválido. Escolha entre CLT ou PJ."}), 400

        if tipo_contrato == "PJ":
            if not pj_contratante or not pj_contratante_cnpj:
                return jsonify(
                    {"erro": "Para contrato PJ, informe Contratante e CNPJ do Contratante."}
                ), 400

        if email:
            is_valid_email, email_error = validate_email(email)
            if not is_valid_email:
                return jsonify({"erro": f"Email inválido: {email_error}"}), 400

        novo_usuario = User(
            username=username,
            password=PasswordValidator.hash_password(password),
            role=role,
            tipo_contrato=tipo_contrato,
            area=area,
            localizacao=localizacao,
            empresa=empresa,
            cnpj=cnpj,
            endereco=endereco,
            cargo=cargo,
            cpf=cpf,
            email=email,
            data_admissao=data_admissao,
            departamento=departamento,
            local_trabalho=local_trabalho,
            pj_contratante=pj_contratante,
            pj_contratante_cnpj=pj_contratante_cnpj,
            pj_contratante_endereco=pj_contratante_endereco,
            pj_contratada=pj_contratada,
            pj_contratada_cnpj=pj_contratada_cnpj,
            pj_data_contrato=pj_data_contrato,
        )
        db.session.add(novo_usuario)

        # Criar termo inicial junto com o usuário para manter o fluxo consistente.
        db.session.flush()

        if foto_perfil_file and getattr(foto_perfil_file, "filename", "").strip():
            allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
            filename = foto_perfil_file.filename
            extension = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
            if extension not in allowed_extensions:
                return jsonify(
                    {"erro": "Formato de imagem não permitido. Use PNG, JPG, JPEG, GIF ou WEBP."}
                ), 400

            foto_perfil_file.seek(0, os.SEEK_END)
            size = foto_perfil_file.tell()
            foto_perfil_file.seek(0)
            if size > 2 * 1024 * 1024:
                return jsonify({"erro": "Imagem muito grande. Tamanho máximo: 2MB."}), 400

            upload_dir = os.path.join(current_app.static_folder, "uploads", "avatars")
            os.makedirs(upload_dir, exist_ok=True)
            safe_filename = secure_filename(
                f"user_{novo_usuario.id}_{int(datetime.now().timestamp())}.{extension}"
            )
            foto_perfil_file.save(os.path.join(upload_dir, safe_filename))
            novo_usuario.foto_perfil = safe_filename

        if tipo_contrato == "CLT":
            termo = TermoEntrega(
                id_usuario=novo_usuario.id,
                empresa=empresa,
                cnpj=cnpj,
                endereco=endereco,
                nome_colaborador=username,
                cargo_funcao=cargo,
                cpf_cnpj=cpf,
                departamento=departamento,
                local_trabalho=local_trabalho,
                data_admissao=data_admissao,
            )
        else:
            termo = TermoEntrega(
                id_usuario=novo_usuario.id,
                nome_colaborador=username,
                pj_contratante=pj_contratante,
                pj_contratante_cnpj=pj_contratante_cnpj,
                pj_contratante_endereco=pj_contratante_endereco,
                pj_contratada=pj_contratada,
                pj_contratada_cnpj=pj_contratada_cnpj,
                pj_data_contrato=pj_data_contrato,
            )
        db.session.add(termo)
        db.session.commit()

        registrar_evento(
            tipo_evento="usuario_criado",
            descricao=f'Novo usuário criado: "{username}" com role "{role}"',
            usuario_responsavel=current_user.username,
        )

        return jsonify({"mensagem": "Usuário criado com sucesso"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
@require_role("admin")
def deletar_usuario_api(user_id):
    try:
        usuario = User.query.get(user_id)
        if not usuario:
            return jsonify({"erro": "Usuário não encontrado"}), 404

        if usuario.id == current_user.id:
            return jsonify({"erro": "Você não pode deletar sua própria conta."}), 403

        if usuario.role == "admin":
            admin_count = User.query.filter_by(role="admin").count()
            if admin_count <= 1:
                return jsonify({"erro": "Não é possível deletar o último administrador."}), 403

        db.session.delete(usuario)
        db.session.commit()
        registrar_evento(
            tipo_evento="usuario_deletado",
            descricao=f'Usuário "{usuario.username}" foi deletado',
            usuario_responsavel=current_user.username,
        )
        return jsonify({"mensagem": "Usuário removido com sucesso"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/users/me/password", methods=["PUT"])
@login_required
def atualizar_senha_atual_api():
    try:
        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({"erro": "JSON inválido ou vazio"}), 400

        senha_atual = dados.get("senha_atual", "")
        senha_atual_rep = dados.get("senha_atual_rep", "")
        nova_senha = dados.get("nova_senha", "")
        confirm_nova_senha = dados.get("confirm_nova_senha", "")

        if not senha_atual or not senha_atual_rep or not nova_senha or not confirm_nova_senha:
            return jsonify({"erro": "Todos os campos são obrigatórios."}), 400

        if senha_atual != senha_atual_rep:
            return jsonify({"erro": "A senha atual deve ser confirmada corretamente."}), 400

        if not PasswordValidator.verify_password(senha_atual, current_user.password):
            return jsonify({"erro": "Senha atual incorreta."}), 400

        if nova_senha != confirm_nova_senha:
            return jsonify(
                {"erro": "A nova senha deve ser digitada duas vezes de forma idêntica."}
            ), 400

        if nova_senha == senha_atual:
            return jsonify({"erro": "A nova senha deve ser diferente da senha atual."}), 400

        is_valid, errors = PasswordValidator.validate(nova_senha)
        if not is_valid:
            return jsonify({"erro": "; ".join(errors)}), 400

        current_user.password = PasswordValidator.hash_password(nova_senha)
        db.session.commit()

        registrar_evento(
            tipo_evento="senha_alterada",
            descricao="Senha atualizada com sucesso",
            usuario_responsavel=current_user.username,
        )

        return jsonify({"mensagem": "Senha atualizada com sucesso"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/users/<int:user_id>/reset-password", methods=["PUT"])
@login_required
@require_role("admin")
def resetar_senha_usuario_api(user_id):
    try:
        usuario = User.query.get(user_id)
        if not usuario:
            return jsonify({"erro": "Usuário não encontrado"}), 404

        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({"erro": "JSON inválido ou vazio"}), 400

        nova_senha = dados.get("nova_senha", "")
        confirm_nova_senha = dados.get("confirm_nova_senha", "")

        if not nova_senha or not confirm_nova_senha:
            return jsonify({"erro": "Todos os campos são obrigatórios."}), 400

        if nova_senha != confirm_nova_senha:
            return jsonify(
                {"erro": "A nova senha deve ser digitada duas vezes de forma idêntica."}
            ), 400

        is_valid, errors = PasswordValidator.validate(nova_senha)
        if not is_valid:
            return jsonify({"erro": "; ".join(errors)}), 400

        usuario.password = PasswordValidator.hash_password(nova_senha)
        usuario.tentativas_login_falhas = 0
        usuario.bloqueado_ate = None
        db.session.commit()

        registrar_evento(
            tipo_evento="senha_resetada",
            descricao=f'Senha do usuário "{usuario.username}" resetada pelo admin',
            usuario_responsavel=current_user.username,
        )

        return jsonify({"mensagem": "Senha do usuário redefinida com sucesso"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


def validar_dados_chamada(dados):
    erros = []
    if not dados:
        erros.append("Dados inválidos ou vazios")
        return erros

    tipo = (dados.get("tipo") or "").strip()
    subtipo = (dados.get("subtipo") or "").strip()
    mensagem = (dados.get("mensagem") or "").strip()

    if not tipo:
        erros.append("Tipo de chamado é obrigatório")
    if tipo != "Outros" and not subtipo:
        erros.append("Subtipo é obrigatório para o tipo selecionado")
    if not mensagem:
        erros.append("Mensagem é obrigatória")

    return erros


def montar_texto_chamada(tipo, subtipo, mensagem):
    if not tipo or tipo == "Outros":
        return mensagem
    if subtipo:
        return f"[{tipo} - {subtipo}] {mensagem}"
    return f"[{tipo}] {mensagem}"


@api_bp.route("/chamadas", methods=["GET"])
@login_required
def listar_chamadas():
    """Lista chamadas do usuário ou de todos os usuários para admins."""
    try:
        query = Chamada.query.order_by(Chamada.data_criacao.desc())
        limit = request.args.get("limit", type=int)
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        if start_date:
            try:
                start_date_obj = datetime.fromisoformat(start_date)
                query = query.filter(Chamada.data_criacao >= start_date_obj)
            except ValueError:
                return jsonify({"erro": "Data de início inválida"}), 400

        if end_date:
            try:
                end_date_obj = datetime.fromisoformat(end_date)
                query = query.filter(Chamada.data_criacao <= end_date_obj)
            except ValueError:
                return jsonify({"erro": "Data de fim inválida"}), 400

        if not current_user.is_admin:
            query = query.filter_by(id_usuario=current_user.id)

        if limit and limit > 0:
            query = query.limit(limit)

        chamadas = query.all()
        return jsonify([chamada.to_dict() for chamada in chamadas])
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/chamadas", methods=["POST"])
@login_required
def criar_chamada():
    """Cria uma nova chamada para admins."""
    try:
        if request.is_json:
            dados = request.get_json(silent=True) or {}
        else:
            dados = request.form.to_dict()

        erros = validar_dados_chamada(dados)
        if erros:
            return jsonify({"erro": " | ".join(erros)}), 400

        foto_filename = None
        foto = request.files.get("foto_chamada")
        if foto and foto.filename:
            extensoes_permitidas = {"png", "jpg", "jpeg", "gif", "webp"}
            ext = foto.filename.rsplit(".", 1)[1].lower() if "." in foto.filename else ""
            if ext not in extensoes_permitidas:
                return jsonify(
                    {"erro": "Formato de imagem não permitido. Use PNG, JPG, JPEG, GIF ou WEBP."}
                ), 400

            foto.seek(0, os.SEEK_END)
            tamanho = foto.tell()
            foto.seek(0)
            if tamanho > 5 * 1024 * 1024:
                return jsonify({"erro": "Imagem muito grande. Tamanho máximo: 5MB."}), 400

            upload_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "static", "uploads", "chamadas")
            )
            os.makedirs(upload_dir, exist_ok=True)

            nome_base = secure_filename(os.path.splitext(foto.filename)[0]) or "anexo"
            foto_filename = f"chamada_{current_user.id}_{uuid.uuid4().hex}_{nome_base}.{ext}"
            foto.save(os.path.join(upload_dir, foto_filename))

        texto = montar_texto_chamada(dados.get("tipo"), dados.get("subtipo"), dados.get("mensagem"))
        chamada = Chamada(id_usuario=current_user.id, mensagem=texto, foto_anexo=foto_filename)
        db.session.add(chamada)
        db.session.commit()

        registrar_evento(
            tipo_evento="chamada_criada",
            descricao=f"Chamada criada por {current_user.username}: {texto}",
            usuario_responsavel=current_user.username,
        )

        sucesso_notificacao, erro_notificacao = enviar_notificacao_chamada(
            chamada, "chamada_criada"
        )
        if not sucesso_notificacao:
            current_app.logger.warning(
                "Notificação do Teams não enviada para chamada %s: %s",
                chamada.id_chamada,
                erro_notificacao,
            )

        return jsonify(
            {
                "mensagem": "Chamada enviada com sucesso",
                "notificacao_enviada": bool(sucesso_notificacao),
                "erro_notificacao": erro_notificacao,
                "id_chamada": chamada.id_chamada,
            }
        ), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@api_bp.route("/chamadas/nao-lidas", methods=["GET"])
@login_required
@require_role("admin")
def contar_chamadas_nao_lidas():
    try:
        nao_lidas = Chamada.query.filter_by(lida=False).count()
        return jsonify({"nao_lidas": nao_lidas})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@api_bp.route("/chamadas/<int:id_chamada>/status", methods=["PUT"])
@login_required
@require_role("admin")
def atualizar_status_chamada(id_chamada):
    """Atualiza o status de uma chamada (admin)"""
    try:
        # Validar Content-Type
        if not request.is_json:
            return jsonify({"erro": "Content-Type deve ser application/json"}), 400

        dados = request.get_json()
        if not dados:
            return jsonify({"erro": "Corpo da requisição vazio"}), 400

        status = (dados.get("status") or "").strip().lower()

        # Validar status
        status_validos = ["nova", "lida", "analise", "execucao", "concluida"]
        if not status or status not in status_validos:
            return jsonify({"erro": f"Status inválido. Use: {', '.join(status_validos)}"}), 400

        # Buscar chamada
        chamada = Chamada.query.get(id_chamada)
        if not chamada:
            return jsonify({"erro": "Chamada não encontrada"}), 404

        status_anterior = chamada.status

        # Atualizar status
        chamada.status = status
        chamada.lida = status in ["lida", "analise", "execucao", "concluida"]
        db.session.commit()

        # Enviar email para o usuário quando chamado for concluído
        if status == "concluida":
            _notificar_usuario_chamado_concluido(chamada)

        sucesso_notificacao, erro_notificacao = enviar_notificacao_chamada(
            chamada,
            "chamada_status_alterado",
            status_anterior=status_anterior,
        )
        if not sucesso_notificacao:
            current_app.logger.warning(
                "Notificação do Teams não enviada para chamada %s: %s",
                chamada.id_chamada,
                erro_notificacao,
            )

        # Registrar evento
        registrar_evento(
            tipo_evento="chamada_status_alterado",
            descricao=f"Chamada {id_chamada} alterada para status {status}",
            usuario_responsavel=current_user.username,
        )

        return jsonify(
            {
                "mensagem": "Status atualizado com sucesso",
                "novo_status": status,
                "notificacao_enviada": bool(sucesso_notificacao),
                "erro_notificacao": erro_notificacao,
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao atualizar status: {str(e)}"}), 500


@api_bp.route("/chamadas/<int:id_chamada>/ler", methods=["PUT"])
@login_required
@require_role("admin")
def marcar_chamada_como_lida(id_chamada):
    """Marca uma chamada como lida (admin)"""
    try:
        chamada = Chamada.query.get(id_chamada)
        if not chamada:
            return jsonify({"erro": "Chamada não encontrada"}), 404

        chamada.lida = True
        if chamada.status == "nova":
            chamada.status = "lida"
        db.session.commit()

        registrar_evento(
            tipo_evento="chamada_lida",
            descricao=f"Chamada {id_chamada} marcada como lida",
            usuario_responsavel=current_user.username,
        )

        return jsonify({"mensagem": "Chamada marcada como lida"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao marcar como lida: {str(e)}"}), 500
