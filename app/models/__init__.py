from datetime import datetime, timezone, timedelta
from app.database import db
from flask_login import UserMixin
from sqlalchemy.dialects.mysql import LONGBLOB


def now_gmt3():
    """Retorna datetime com fuso-horário GMT-3."""
    return datetime.now(timezone(timedelta(hours=-3)))


class User(db.Model, UserMixin):
    """Modelo para usuários do sistema com RBAC (Role-Based Access Control)"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)  # Aumentado para hash seguro
    
    # RBAC - Roles: 'admin', 'usuario'
    role = db.Column(db.String(50), nullable=False, default='usuario')

    # Tipo de contrato/vínculo
    tipo_contrato = db.Column(db.String(10), nullable=False, default='CLT')
    
    # Informações do usuário
    area = db.Column(db.String(255), nullable=False, default='')
    localizacao = db.Column(db.String(255), nullable=False, default='')
    
    # Informações da empresa
    empresa = db.Column(db.String(255), nullable=False, default='')
    cnpj = db.Column(db.String(18), nullable=False, default='')
    endereco = db.Column(db.String(500), nullable=False, default='')
    cargo = db.Column(db.String(255), nullable=False, default='')
    cpf = db.Column(db.String(14), nullable=False, default='')
    email = db.Column(db.String(150), nullable=True, default='')
    data_admissao = db.Column(db.Date, nullable=True)
    departamento = db.Column(db.String(255), nullable=False, default='')
    local_trabalho = db.Column(db.String(255), nullable=False, default='')
    # Campos específicos para contratação PJ
    pj_contratante = db.Column(db.String(255), nullable=True, default='')
    pj_contratante_cnpj = db.Column(db.String(18), nullable=True, default='')
    pj_contratante_endereco = db.Column(db.String(500), nullable=True, default='')
    pj_contratada = db.Column(db.String(255), nullable=True, default='')
    pj_contratada_cnpj = db.Column(db.String(18), nullable=True, default='')
    pj_data_contrato = db.Column(db.Date, nullable=True)
    
    # Status e auditoria
    ativo = db.Column(db.Boolean, default=True, nullable=False)  # Se usuário está ativo/bloqueado
    data_criacao = db.Column(db.DateTime, default=now_gmt3, nullable=False)
    data_atualizacao = db.Column(db.DateTime, default=now_gmt3, onupdate=now_gmt3)

    # Foto de perfil
    foto_perfil = db.Column(db.String(255), nullable=True)
    
    # Segurança - Último login e tentativas falhas
    ultimo_login = db.Column(db.DateTime, nullable=True)
    tentativas_login_falhas = db.Column(db.Integer, default=0)  # Para detecção de força bruta
    bloqueado_ate = db.Column(db.DateTime, nullable=True)  # Bloqueio temporário após X tentativas
    
    # Relacionamentos
    chamadas = db.relationship('Chamada', backref='usuario', lazy=True, cascade='all, delete-orphan')

    def __init__(self, username, password, role='usuario', tipo_contrato='CLT', area='', localizacao='', empresa='', cnpj='', 
                 endereco='', cargo='', cpf='', email='', data_admissao=None, departamento='', local_trabalho='',
                 pj_contratante='', pj_contratante_cnpj='', pj_contratante_endereco='', pj_contratada='', pj_contratada_cnpj='', pj_data_contrato=None):
        self.username = username
        self.password = password  # Já deve vir em hash
        self.role = role
        self.tipo_contrato = (tipo_contrato or 'CLT').strip().upper()
        self.area = area.strip() if area else ''
        self.localizacao = localizacao.strip() if localizacao else ''
        self.empresa = empresa.strip() if empresa else ''
        self.cnpj = cnpj.strip() if cnpj else ''
        self.endereco = endereco.strip() if endereco else ''
        self.cargo = cargo.strip() if cargo else ''
        self.cpf = cpf.strip() if cpf else ''
        self.email = email.strip() if email else ''
        self.data_admissao = data_admissao
        self.departamento = departamento.strip() if departamento else ''
        self.local_trabalho = local_trabalho.strip() if local_trabalho else ''
        # Atribuir campos PJ
        self.pj_contratante = pj_contratante.strip() if pj_contratante else ''
        self.pj_contratante_cnpj = pj_contratante_cnpj.strip() if pj_contratante_cnpj else ''
        self.pj_contratante_endereco = pj_contratante_endereco.strip() if pj_contratante_endereco else ''
        self.pj_contratada = pj_contratada.strip() if pj_contratada else ''
        self.pj_contratada_cnpj = pj_contratada_cnpj.strip() if pj_contratada_cnpj else ''
        self.pj_data_contrato = pj_data_contrato
        self.ativo = True
        self.tentativas_login_falhas = 0

    @property
    def is_admin(self):
        """Verifica se o usuário é admin"""
        return self.role == 'admin'
    
    @property
    def is_active(self):
        """Override de is_active para Flask-Login - verifica se está ativo e desbloqueado"""
        if not self.ativo:
            return False
        
        # Verificar se está bloqueado temporariamente
        if self.bloqueado_ate:
            if datetime.now(timezone(timedelta(hours=-3))) < self.bloqueado_ate:
                return False
            # Se expirou o bloqueio, limpar
            self.bloqueado_ate = None
            db.session.commit()
        
        return True
    
    def registrar_login_sucesso(self):
        """Registra login bem-sucedido e reseta tentativas falhas"""
        self.ultimo_login = now_gmt3()
        self.tentativas_login_falhas = 0
        self.bloqueado_ate = None
        db.session.commit()
    
    def registrar_login_falho(self, max_tentativas=5, bloqueio_minutos=15):
        """
        Registra tentativa falha e bloqueia após X tentativas.
        
        Args:
            max_tentativas: Número máximo de tentativas antes de bloquear
            bloqueio_minutos: Minutos de bloqueio após máximo atingido
        """
        self.tentativas_login_falhas += 1
        
        if self.tentativas_login_falhas >= max_tentativas:
            # Bloquear por X minutos
            self.bloqueado_ate = now_gmt3() + timedelta(minutes=bloqueio_minutos)
        
        db.session.commit()
    
    def pode_tentar_login(self) -> bool:
        """Verifica se o usuário pode tentar login (não está bloqueado)"""
        if self.bloqueado_ate:
            agora = datetime.now(timezone(timedelta(hours=-3)))
            if agora < self.bloqueado_ate:
                return False
            # Se expirou, liberar
            self.bloqueado_ate = None
            self.tentativas_login_falhas = 0
            db.session.commit()
        
        return True
    
    def minutos_ate_desbloqueio(self) -> int:
        """Retorna quantos minutos faltam para desbloqueio"""
        if not self.bloqueado_ate:
            return 0
        
        agora = datetime.now(timezone(timedelta(hours=-3)))
        diferenca = self.bloqueado_ate - agora
        return max(0, int(diferenca.total_seconds() / 60))
    
    def to_dict(self):
        """Converte usuário para dicionário (sem password!)"""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'tipo_contrato': self.tipo_contrato,
            'area': self.area,
            'localizacao': self.localizacao,
            'empresa': self.empresa,
            'cnpj': self.cnpj,
            'endereco': self.endereco,
            'cargo': self.cargo,
            'cpf': self.cpf,
            'data_admissao': self.data_admissao.strftime("%d/%m/%Y") if self.data_admissao else None,
            'data_admissao_iso': self.data_admissao.strftime("%Y-%m-%d") if self.data_admissao else None,
            'departamento': self.departamento,
            'local_trabalho': self.local_trabalho,
            'email': self.email,
            'pj_contratante': self.pj_contratante,
            'pj_contratante_cnpj': self.pj_contratante_cnpj,
            'pj_contratante_endereco': self.pj_contratante_endereco,
            'pj_contratada': self.pj_contratada,
            'pj_contratada_cnpj': self.pj_contratada_cnpj,
            'pj_data_contrato': self.pj_data_contrato.strftime("%d/%m/%Y") if self.pj_data_contrato else None,
            'pj_data_contrato_iso': self.pj_data_contrato.strftime("%Y-%m-%d") if self.pj_data_contrato else None,
            'foto_perfil': self.foto_perfil,
            'ativo': self.ativo,
            'data_criacao': self.data_criacao.strftime("%d/%m/%Y %H:%M:%S") if self.data_criacao else None,
            'ultimo_login': self.ultimo_login.strftime("%d/%m/%Y %H:%M:%S") if self.ultimo_login else "Nunca",
            'is_admin': self.is_admin
        }


class Produto(db.Model):
    """Modelo para produtos do estoque"""
    __tablename__ = 'produtos'

    id_produto = db.Column(db.String(50), primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    minimo = db.Column(db.Integer, nullable=False, default=0)
    localizacao = db.Column(db.String(255))
    data_criacao = db.Column(db.DateTime, default=now_gmt3)
    data_atualizacao = db.Column(db.DateTime, default=now_gmt3, onupdate=now_gmt3)

    # Relacionamento com movimentações
    movimentacoes = db.relationship('Movimentacao', backref='produto', lazy=True, cascade='all, delete-orphan')

    def __init__(self, id_produto, nome, categoria, preco, quantidade, minimo, localizacao=""):
        self.id_produto = id_produto
        self.nome = nome
        self.categoria = categoria
        self.preco = preco
        self.quantidade = quantidade
        self.minimo = minimo
        self.localizacao = localizacao

    def to_dict(self):
        """Converte o produto para dicionário"""
        return {
            'id': self.id_produto,
            'nome': self.nome,
            'categoria': self.categoria,
            'preco': self.preco,
            'quantidade': self.quantidade,
            'minimo': self.minimo,
            'localizacao': self.localizacao,
            'valor_total': self.valor_total(),
            'abaixo_minimo': self.abaixo_minimo(),
            'data_criacao': self.data_criacao.strftime("%d/%m/%Y %H:%M:%S") if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.strftime("%d/%m/%Y %H:%M:%S") if self.data_atualizacao else None
        }

    def valor_total(self):
        """Calcula o valor total do produto em estoque"""
        return self.quantidade * self.preco

    def abaixo_minimo(self):
        """Verifica se o produto está abaixo do estoque mínimo"""
        return self.quantidade < self.minimo


class Movimentacao(db.Model):
    """Modelo para histórico de movimentações"""
    __tablename__ = 'movimentacoes'

    id_movimentacao = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_produto = db.Column(db.String(50), db.ForeignKey('produtos.id_produto'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'ENTRADA' ou 'SAIDA'
    quantidade = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(255))
    data_movimentacao = db.Column(db.DateTime, default=now_gmt3)
    usuario = db.Column(db.String(100))

    def __init__(self, id_produto, tipo, quantidade, motivo="", usuario=""):
        self.id_produto = id_produto
        self.tipo = tipo
        self.quantidade = quantidade
        self.motivo = motivo
        self.usuario = usuario


class Categoria(db.Model):
    """Modelo para categorias de produtos"""
    __tablename__ = 'categorias'

    id_categoria = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.String(255))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, nome, descricao=""):
        self.nome = nome
        self.descricao = descricao


class Chamada(db.Model):
    """Modelo para chamadas/notificações de usuários para admins"""
    __tablename__ = 'chamadas'

    id_chamada = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    foto_anexo = db.Column(db.String(255), nullable=True)
    data_criacao = db.Column(db.DateTime, default=now_gmt3)
    lida = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50), default='nova', nullable=False)

    # Relacionamento com usuário (backref definido no modelo User)
    # A propriedade `usuario` será criada automaticamente pelo backref.

    def __init__(self, id_usuario, mensagem, foto_anexo=None):
        self.id_usuario = id_usuario
        self.mensagem = mensagem
        self.foto_anexo = foto_anexo
        self.status = 'nova'
        self.lida = False

    def to_dict(self):
        return {
            'id': self.id_chamada,
            'id_usuario': self.id_usuario,
            'usuario': self.usuario.username if self.usuario else 'Desconhecido',
            'usuario_foto': self.usuario.foto_perfil if self.usuario else None,
            'usuario_foto_url': f'/static/uploads/avatars/{self.usuario.foto_perfil}' if self.usuario and self.usuario.foto_perfil else None,
            'usuario_area': self.usuario.area if self.usuario else '',
            'usuario_localizacao': self.usuario.localizacao if self.usuario else '',
            'mensagem': self.mensagem,
            'foto_anexo': self.foto_anexo,
            'foto_url': f'/static/uploads/chamadas/{self.foto_anexo}' if self.foto_anexo else None,
            'data_criacao': self.data_criacao.strftime("%d/%m/%Y %H:%M:%S") if self.data_criacao else None,
            'lida': self.lida,
            'status': self.status
        }


class Historico(db.Model):
    """Modelo para histórico de mudanças no sistema (auditoria)"""
    __tablename__ = 'historico'

    id_evento = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tipo_evento = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    usuario_responsavel = db.Column(db.String(150))
    data_evento = db.Column(db.DateTime, default=now_gmt3)
    detalhes = db.Column(db.Text)

    def __init__(self, tipo_evento, descricao, usuario_responsavel=None, detalhes=None):
        self.tipo_evento = tipo_evento
        self.descricao = descricao
        self.usuario_responsavel = usuario_responsavel
        self.detalhes = detalhes

    def to_dict(self):
        return {
            'id': self.id_evento,
            'tipo_evento': self.tipo_evento,
            'descricao': self.descricao,
            'usuario_responsavel': self.usuario_responsavel,
            'data_evento': self.data_evento.strftime("%d/%m/%Y %H:%M:%S") if self.data_evento else None,
            'detalhes': self.detalhes
        }


class DocumentoUsuario(db.Model):
    """Modelo para documentos associados a usuários"""
    __tablename__ = 'documentos_usuarios'

    id_documento = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nome_documento = db.Column(db.String(255), nullable=False)
    arquivo = db.Column(db.String(255), nullable=False)  # Nome do arquivo salvo
    descricao = db.Column(db.Text, nullable=True)
    tipo_arquivo = db.Column(db.String(50), nullable=False)  # extensão do arquivo
    tamanho_arquivo = db.Column(db.Integer, nullable=False)  # em bytes
    data_criacao = db.Column(db.DateTime, default=now_gmt3)
    data_atualizacao = db.Column(db.DateTime, default=now_gmt3, onupdate=now_gmt3)
    usuario_enviador = db.Column(db.String(150), nullable=False)  # Quem fez upload
    
    # Relacionamento com usuário
    usuario = db.relationship('User', backref=db.backref('documentos', lazy=True, cascade='all, delete-orphan'))

    def __init__(self, id_usuario, nome_documento, arquivo, tipo_arquivo, tamanho_arquivo, usuario_enviador, descricao=None):
        self.id_usuario = id_usuario
        self.nome_documento = nome_documento
        self.arquivo = arquivo
        self.tipo_arquivo = tipo_arquivo
        self.tamanho_arquivo = tamanho_arquivo
        self.usuario_enviador = usuario_enviador
        self.descricao = descricao

    def to_dict(self):
        return {
            'id': self.id_documento,
            'id_usuario': self.id_usuario,
            'usuario': self.usuario.username if self.usuario else 'Desconhecido',
            'nome_documento': self.nome_documento,
            'arquivo': self.arquivo,
            'tipo_arquivo': self.tipo_arquivo,
            'tamanho_arquivo': self.tamanho_arquivo,
            'descricao': self.descricao,
            'data_criacao': self.data_criacao.strftime("%d/%m/%Y %H:%M:%S") if self.data_criacao else None,
            'usuario_enviador': self.usuario_enviador
        }


class DocumentoArquivo(db.Model):
    """Armazena conteúdo binário de documentos migrados/guardados no banco."""
    __tablename__ = 'documentos_arquivos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(255), nullable=False, index=True)
    # LONGBLOB (até 4 GB) em vez de LargeBinary/BLOB (64 KB no MySQL), evitando
    # truncamento silencioso de documentos grandes.
    content = db.Column(LONGBLOB, nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    size = db.Column(db.Integer, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=now_gmt3)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'mime_type': self.mime_type,
            'size': self.size,
            'uploaded_at': self.uploaded_at.strftime('%d/%m/%Y %H:%M:%S') if self.uploaded_at else None,
        }


class ItemRecebido(db.Model):
    """Modelo para itens recebidos por usuários"""
    __tablename__ = 'itens_recebidos'

    id_item = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    descricao_item = db.Column(db.String(255), nullable=False)
    tipo_recebimento = db.Column(db.String(50), nullable=False)  # 'entrada' ou 'posteriormente'
    data_criacao = db.Column(db.DateTime, default=now_gmt3)
    data_atualizacao = db.Column(db.DateTime, default=now_gmt3, onupdate=now_gmt3)
    usuario_responsavel = db.Column(db.String(150), nullable=False)  # Quem registrou
    
    # Relacionamento com usuário
    usuario = db.relationship('User', backref=db.backref('itens_recebidos', lazy=True, cascade='all, delete-orphan'))

    def __init__(self, id_usuario, descricao_item, tipo_recebimento, usuario_responsavel):
        self.id_usuario = id_usuario
        self.descricao_item = descricao_item
        self.tipo_recebimento = tipo_recebimento
        self.usuario_responsavel = usuario_responsavel

    def to_dict(self):
        return {
            'id': self.id_item,
            'id_usuario': self.id_usuario,
            'descricao_item': self.descricao_item,
            'tipo_recebimento': self.tipo_recebimento,
            'data_criacao': self.data_criacao.strftime("%d/%m/%Y %H:%M:%S") if self.data_criacao else None,
            'usuario_responsavel': self.usuario_responsavel
        }


class TermoEntrega(db.Model):
    """Modelo para Termo de Entrega e Responsabilidade de Equipamentos"""
    __tablename__ = 'termos_entrega'

    id_termo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Informações da empresa (CLT)
    empresa = db.Column(db.String(255), nullable=False, default='')
    cnpj = db.Column(db.String(18), nullable=False, default='')
    endereco = db.Column(db.String(500), nullable=False, default='')
    
    # Informações do colaborador (CLT)
    nome_colaborador = db.Column(db.String(255), nullable=False, default='')
    cargo_funcao = db.Column(db.String(255), nullable=False, default='')
    cpf_cnpj = db.Column(db.String(18), nullable=False, default='')
    departamento = db.Column(db.String(255), nullable=False, default='')
    local_trabalho = db.Column(db.String(255), nullable=False, default='')
    data_admissao = db.Column(db.Date, nullable=True)
    
    # Informações PJ (Contratante)
    pj_contratante = db.Column(db.String(255), nullable=True, default='')
    pj_contratante_cnpj = db.Column(db.String(18), nullable=True, default='')
    pj_contratante_endereco = db.Column(db.String(500), nullable=True, default='')
    
    # Informações PJ (Contratada)
    pj_contratada = db.Column(db.String(255), nullable=True, default='')
    pj_contratada_cnpj = db.Column(db.String(18), nullable=True, default='')
    
    # Data do Contrato PJ
    pj_data_contrato = db.Column(db.Date, nullable=True)
    
    # Equipamentos entregues (JSON para flexibilidade)
    equipamentos = db.Column(db.Text, nullable=True, default='[]')  # JSON string
    
    # Status e auditoria
    data_criacao = db.Column(db.DateTime, default=now_gmt3, nullable=False)
    data_atualizacao = db.Column(db.DateTime, default=now_gmt3, onupdate=now_gmt3)
    assinado = db.Column(db.Boolean, default=False)
    data_assinatura = db.Column(db.DateTime, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    
    # Relacionamento com usuário
    usuario = db.relationship('User', backref=db.backref('termos_entrega', lazy=True, cascade='all, delete-orphan'))

    def __init__(self, id_usuario, empresa='', cnpj='', endereco='', nome_colaborador='', 
                 cargo_funcao='', cpf_cnpj='', departamento='', local_trabalho='', data_admissao=None,
                 pj_contratante='', pj_contratante_cnpj='', pj_contratante_endereco='',
                 pj_contratada='', pj_contratada_cnpj='', pj_data_contrato=None):
        self.id_usuario = id_usuario
        self.empresa = empresa
        self.cnpj = cnpj
        self.endereco = endereco
        self.nome_colaborador = nome_colaborador
        self.cargo_funcao = cargo_funcao
        self.cpf_cnpj = cpf_cnpj
        self.departamento = departamento
        self.local_trabalho = local_trabalho
        self.data_admissao = data_admissao
        self.pj_contratante = pj_contratante
        self.pj_contratante_cnpj = pj_contratante_cnpj
        self.pj_contratante_endereco = pj_contratante_endereco
        self.pj_contratada = pj_contratada
        self.pj_contratada_cnpj = pj_contratada_cnpj
        self.pj_data_contrato = pj_data_contrato
        self.equipamentos = '[]'
        self.assinado = False

    def to_dict(self):
        import json
        return {
            'id': self.id_termo,
            'id_usuario': self.id_usuario,
            'usuario': self.usuario.username if self.usuario else 'Desconhecido',
            'empresa': self.empresa,
            'cnpj': self.cnpj,
            'endereco': self.endereco,
            'nome_colaborador': self.nome_colaborador,
            'cargo_funcao': self.cargo_funcao,
            'cpf_cnpj': self.cpf_cnpj,
            'departamento': self.departamento,
            'local_trabalho': self.local_trabalho,
            'data_admissao': self.data_admissao.strftime("%d/%m/%Y") if self.data_admissao else None,
            'pj_contratante': self.pj_contratante,
            'pj_contratante_cnpj': self.pj_contratante_cnpj,
            'pj_contratante_endereco': self.pj_contratante_endereco,
            'pj_contratada': self.pj_contratada,
            'pj_contratada_cnpj': self.pj_contratada_cnpj,
            'pj_data_contrato': self.pj_data_contrato.strftime("%d/%m/%Y") if self.pj_data_contrato else None,
            'equipamentos': json.loads(self.equipamentos) if self.equipamentos else [],
            'data_criacao': self.data_criacao.strftime("%d/%m/%Y %H:%M:%S") if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.strftime("%d/%m/%Y %H:%M:%S") if self.data_atualizacao else None,
            'assinado': self.assinado,
            'data_assinatura': self.data_assinatura.strftime("%d/%m/%Y %H:%M:%S") if self.data_assinatura else None,
            'observacoes': self.observacoes
        }