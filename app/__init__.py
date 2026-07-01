import os
from datetime import datetime, timedelta

from flask import flash, g, redirect, render_template_string, request, session, url_for
from flask_login import LoginManager, current_user, logout_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

from .auth import ROLES_PERMISSIONS, can_perform, get_user_permissions
from .database import create_app as create_db_app
from .database import db
from .migrate import migrate
from .models import User
from .services import EstoqueService
from .utils.logger import criar_logger, registrar_erro, registrar_seguranca

# Instância global do serviço de estoque
estoque = None

# Logger centralizado
app_logger = criar_logger("estoque")


def create_app():
    """Application Factory Pattern"""
    global estoque

    # Criar app com database (mail é inicializado dentro de create_db_app)
    app, db, _ = create_db_app()
    app.logger.handlers = app_logger.handlers
    app.logger.setLevel(app_logger.level)

    # Proteger contra CSRF em formulários (o construtor registra a proteção no app)
    CSRFProtect(app)

    # Configurar LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        """Não autenticado: API/AJAX recebem 401 JSON; navegação HTML é redirecionada.

        Sem isto, o `@login_required` (que envolve `@require_role` nas rotas de
        `/api`) redireciona requisições anônimas para a página HTML de login
        (302). O ramo 401 JSON de `require_role` nunca roda para usuários
        anônimos por estar mais interno, e um cliente JSON acabaria tentando
        parsear HTML. Aqui devolvemos 401 JSON quando a requisição é de API/AJAX.
        """
        from flask import jsonify

        eh_api = (
            request.path.startswith("/api/")
            or request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        )
        if eh_api:
            return jsonify({"error": "Autenticação necessária"}), 401

        flash(login_manager.login_message, login_manager.login_message_category)
        return redirect(url_for(login_manager.login_view))

    @app.before_request
    def _session_timeout():
        """Expire sessões de usuários (não admin) após 10 minutos de inatividade. Registra tempo inicial."""
        try:
            # Registrar tempo inicial para log de duração
            g.start_time = datetime.utcnow()

            # Ignorar arquivos estáticos
            if request.endpoint == "static":
                return

            if hasattr(current_user, "is_authenticated") and current_user.is_authenticated:
                role = getattr(current_user, "role", None)
                # Aplicar apenas para usuários não-admin
                if role != "admin":
                    now = datetime.utcnow()
                    last = session.get("last_activity")
                    if last:
                        try:
                            last_dt = datetime.fromisoformat(last)
                        except Exception:
                            last_dt = now
                        if now - last_dt > timedelta(minutes=10):
                            registrar_seguranca(
                                app_logger,
                                "Sessão expirada por inatividade",
                                usuario=current_user.username,
                            )
                            logout_user()
                            session.pop("last_activity", None)
                            flash("Sessão expirada por inatividade. Faça login novamente.", "info")
                            return redirect(url_for("auth.login"))
                    # Atualizar último acesso
                    session["last_activity"] = now.isoformat()
        except Exception as e:
            # Não interromper a aplicação por problemas de verificação de sessão
            registrar_erro(app_logger, e, {"contexto": "session_timeout"})
            return

    @app.after_request
    def set_secure_headers(response):
        """Adicionar cabeçalhos de segurança básicos e registrar duração da requisição."""
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # HSTS apenas em produção/HTTPS
        if os.getenv("FLASK_ENV") != "development":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
            )

        # Registrar requisição/resposta HTTP
        try:
            if request.endpoint not in ["static", None]:
                duracao = (
                    (datetime.utcnow() - g.start_time).total_seconds()
                    if hasattr(g, "start_time")
                    else 0
                )
                nivel = (
                    "error"
                    if response.status_code >= 500
                    else ("warning" if response.status_code >= 400 else "debug")
                )
                msg = f"HTTP {response.status_code} | {request.method} {request.path} | {duracao:.3f}s"

                if nivel == "error":
                    app_logger.error(msg)
                elif nivel == "warning":
                    app_logger.warning(msg)
                else:
                    app_logger.debug(msg)
        except Exception:
            pass

        return response

    # Registrar blueprints
    from .routes.admin import admin_bp
    from .routes.api import api_bp
    from .routes.auth import auth_bp
    from .routes.entra_auth import entra_bp
    from .routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(entra_bp)

    # Adicionar funções úteis ao contexto de templates
    @app.context_processor
    def inject_auth():
        """Injetar funções de auth nos templates"""
        return {
            "can_perform": can_perform,
            "get_user_permissions": get_user_permissions,
            "ROLES_PERMISSIONS": ROLES_PERMISSIONS,
        }

    # Registrar erros
    @app.errorhandler(403)
    def forbidden(e):
        """Erro de acesso negado"""
        usuario = current_user.username if current_user.is_authenticated else "Anônimo"
        registrar_seguranca(
            app_logger,
            "Acesso negado (403)",
            usuario=usuario,
            detalhes=f"{request.method} {request.path}",
        )
        return render_template_string(
            "<h1>Acesso Negado (403)</h1><p>Você não tem permissão para acessar este recurso.</p>"
        ), 403

    @app.errorhandler(404)
    def not_found(e):
        """Erro de página não encontrada"""
        app_logger.warning(f"404 Not Found: {request.method} {request.path}")
        return render_template_string(
            "<h1>Página Não Encontrada (404)</h1><p>O recurso que você procura não existe.</p>"
        ), 404

    # @app.errorhandler(500)
    # def internal_error(e):
    #     """Erro interno do servidor"""
    #     import traceback
    #     tb = traceback.format_exc()
    #     registrar_erro(app_logger, e, {'endpoint': request.endpoint, 'metodo': request.method, 'caminho': request.path})
    #     app_logger.error(f"TRACEBACK COMPLETO:\n{tb}")
    #     # TEMPORÁRIO - mostra o traceback na tela para diagnóstico - REMOVER DEPOIS
    #     return render_template_string('<h1>Erro Interno (500) - DEBUG TEMP</h1><pre>{{ tb }}</pre>', tb=tb), 500
    # Inicializar Flask-Migrate
    migrate.init_app(app, db)

    # Inicializar banco e serviços
    with app.app_context():
        init_database()

    return app


def _ensure_schema_columns():
    """Adiciona colunas ausentes nas tabelas existentes (migração manual)."""
    inspector = inspect(db.engine)
    migrations = [
        ("users", "foto_perfil", "VARCHAR(255)"),
        ("users", "tipo_contrato", "VARCHAR(10) DEFAULT 'CLT'"),
        ("users", "ultimo_login", "DATETIME"),
        ("users", "tentativas_login_falhas", "INTEGER DEFAULT 0"),
        ("users", "bloqueado_ate", "DATETIME"),
        ("users", "data_atualizacao", "DATETIME"),
        ("users", "email", "VARCHAR(150)"),
        ("chamadas", "foto_anexo", "VARCHAR(255)"),
        # Campos PJ adicionados dinamicamente quando ausentes
        ("users", "pj_contratante", "VARCHAR(255)"),
        ("users", "pj_contratante_cnpj", "VARCHAR(18)"),
        ("users", "pj_contratante_endereco", "VARCHAR(500)"),
        ("users", "pj_contratada", "VARCHAR(255)"),
        ("users", "pj_contratada_cnpj", "VARCHAR(18)"),
        ("users", "pj_data_contrato", "DATE"),
    ]
    for table, column, col_type in migrations:
        if table not in inspector.get_table_names():
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        if column not in existing:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            db.session.commit()
            print(f"[MIGRATE] Coluna '{column}' adicionada em '{table}'")


def init_database():
    """Inicializa o banco de dados e cria dados iniciais"""
    global estoque

    # Exibir informações de configuração
    print("\n" + "=" * 60)
    print("Sistema de Estoque - Inicializando...")
    print("=" * 60)
    from .database import DATABASE_URL

    db_type = "MySQL" if "mysql" in DATABASE_URL else "Desconhecido"
    print(f"Banco de dados: {db_type}")
    print("=" * 60 + "\n")

    try:
        # Aplicar migracoes somente quando houver revisoes geradas.
        try:
            migrations_dir = os.path.join(os.path.dirname(__file__), "..", "migrations")
            versions_dir = os.path.join(migrations_dir, "versions")
            has_revisions = False
            if os.path.exists(versions_dir):
                for fname in os.listdir(versions_dir):
                    if fname.endswith(".py") and fname != "__init__.py":
                        has_revisions = True
                        break

            if has_revisions:
                from flask_migrate import upgrade

                print("Aplicando migracoes do banco de dados...")
                upgrade(revision="head")
            else:
                print("Nenhuma revisao de migracao encontrada; seguindo com create_all().")
        except SystemExit as e:
            print(f"[INFO] Migracoes nao aplicadas (SystemExit: {e}); seguindo inicializacao.")
        except Exception as e:
            print(f"[INFO] Nota: {e}")

        # Garante criacao das tabelas mesmo quando o upgrade nao gera alteracoes.
        print("Garantindo estrutura base do banco...")
        db.create_all()

        # Garantir existência de pastas de upload usadas pela aplicação
        try:
            base_static = os.path.join(os.path.dirname(__file__), "..", "static")
            uploads_dir = os.path.abspath(os.path.join(base_static, "uploads"))
            os.makedirs(uploads_dir, exist_ok=True)
            for sub in ("avatars", "chamadas", "documentos", "documentos/termos"):
                os.makedirs(os.path.join(uploads_dir, sub), exist_ok=True)
        except Exception as _e:
            print(f"[WARN] Não foi possível garantir pastas de upload: {_e}")

        # Garantir que todas as colunas do modelo existam (migrations manuais)
        _ensure_schema_columns()

        # Criar usuário admin se não existir
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            admin_user = User(
                username="admin", password=generate_password_hash("admin"), role="admin"
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Usuario admin criado (login: admin / senha: admin)")
        else:
            # Se existir mas não tiver role válida, atualiza
            if not admin_user.role or admin_user.role not in ["usuario", "admin"]:
                admin_user.role = "admin"
                db.session.commit()

            # Se o hash atual não verificar a senha padrão, redefinir para uma hash compatível
            try:
                if not check_password_hash(admin_user.password, "admin"):
                    admin_user.password = generate_password_hash("admin", method="pbkdf2:sha256")
                    db.session.commit()
                    print(
                        "Senha do usuário admin redefinida para admin devido a hash incompatível."
                    )
            except Exception:
                admin_user.password = generate_password_hash("admin", method="pbkdf2:sha256")
                db.session.commit()
                print("Senha do usuário admin redefinida para admin devido a hash inválido.")

        # Remover usuários com roles obsoletos
        obsolete_users = User.query.filter(User.role.in_(["gerente", "operador"])).all()
        if obsolete_users:
            for old_user in obsolete_users:
                db.session.delete(old_user)
            db.session.commit()
            print(f"Removidos {len(obsolete_users)} usuários com roles obsoletos: gerente/operador")

        # Se a senha do admin for scrypt, atualiza para um hash compatível
        if admin_user and admin_user.password.startswith("scrypt:"):
            admin_user.password = generate_password_hash("admin", method="pbkdf2:sha256")
            db.session.commit()

        # Inicializar o estoque
        estoque = EstoqueService()
        print("Banco de dados inicializado com sucesso\n")

    except Exception as e:
        # Em desenvolvimento, não interromper a aplicação por erros de banco
        registrar_erro(app_logger, e, {"contexto": "init_database"})
        print(f"[AVISO] Erro ao inicializar banco de dados: {str(e)}")
        print("[INFO] Continuando em modo degradado...")
        estoque = EstoqueService()
        print("Sistema iniciado em modo degradado (sem banco de dados)\n")
