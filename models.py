from datetime import datetime, timezone, timedelta
from database import db
from flask_login import UserMixin


def now_gmt3():
    """Retorna datetime com fuso-horário GMT-3."""
    return datetime.now(timezone(timedelta(hours=-3)))


class User(db.Model, UserMixin):
    """Modelo para usuários do sistema"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')  # 'user' ou 'admin'
    area = db.Column(db.String(255), nullable=False, default='')
    localizacao = db.Column(db.String(255), nullable=False, default='')
    data_criacao = db.Column(db.DateTime, default=now_gmt3)

    def __init__(self, username, password, role='user', area='', localizacao=''):
        self.username = username
        self.password = password
        self.role = role
        self.area = area.strip() if area else ''
        self.localizacao = localizacao.strip() if localizacao else ''

    @property
    def is_admin(self):
        return self.role == 'admin'


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

    # Relacionamento com usuário
    usuario = db.relationship('User', backref=db.backref('chamadas', lazy=True, cascade='all, delete-orphan'))

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