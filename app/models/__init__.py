from datetime import datetime, timezone, timedelta
from app.database import db
from flask_login import UserMixin


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
    
    # Informações do usuário
    area = db.Column(db.String(255), nullable=False, default='')
    localizacao = db.Column(db.String(255), nullable=False, default='')
    
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

    def __init__(self, username, password, role='usuario', area='', localizacao=''):
        self.username = username
        self.password = password  # Já deve vir em hash
        self.role = role
        self.area = area.strip() if area else ''
        self.localizacao = localizacao.strip() if localizacao else ''
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
            'area': self.area,
            'localizacao': self.localizacao,
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
    data_criacao = db.Column(db.DateTime, default=now_gmt3)
    lida = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50), default='nova', nullable=False)

    # Relacionamento com usuário (backref definido no modelo User)
    # A propriedade `usuario` será criada automaticamente pelo backref.

    def __init__(self, id_usuario, mensagem):
        self.id_usuario = id_usuario
        self.mensagem = mensagem
        self.status = 'nova'
        self.lida = False

    def to_dict(self):
        return {
            'id': self.id_chamada,
            'id_usuario': self.id_usuario,
            'usuario': self.usuario.username if self.usuario else 'Desconhecido',
            'usuario_area': self.usuario.area if self.usuario else '',
            'usuario_localizacao': self.usuario.localizacao if self.usuario else '',
            'mensagem': self.mensagem,
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