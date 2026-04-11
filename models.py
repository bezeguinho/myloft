from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Pombo(db.Model):
    __tablename__ = 'pombos'
    
    id = db.Column(db.BigInteger, primary_key=True) # BigInteger para alinhar com Supabase
    anilha = db.Column(db.String(50), unique=True, nullable=False)
    numero = db.Column(db.String(20))
    ano = db.Column(db.Integer)
    nome = db.Column(db.String(100))
    sexo = db.Column(db.String(20), default='Indefinido')
    cor = db.Column(db.String(50), default='Indefinido')
    linhagem = db.Column(db.String(200))
    pai_anilha = db.Column(db.String(50))
    mae_anilha = db.Column(db.String(50))
    categoria = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Ativo')
    cedido_para = db.Column(db.String(100))
    observacoes = db.Column(db.Text)
    oculto = db.Column(db.Boolean, default=False)
    
    # ESTA LINHA É A CHAVE: Liga o pombo a um utilizador específico
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'))

    def __repr__(self):
        return f'<Pombo {self.anilha}>'


class Utilizador(db.Model, UserMixin): # UserMixin permite que o Flask-Login funcione
    __tablename__ = 'utilizadores'

    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.Text, nullable=False) # Para guardar a senha segura
    role = db.Column(db.String(20), default='user')    # 'user' ou 'admin'
    is_active = db.Column(db.Boolean, default=True)   # Para tu bloqueares contas
    
    # Campos de perfil que já tinhas
    nome = db.Column(db.String(60))
    telefone = db.Column(db.String(25))
    localidade = db.Column(db.String(60))
    foto = db.Column(db.String(300))

    # Relacionamento: permite ver todos os pombos de um user facilmente
    pombos = db.relationship('Pombo', backref='dono', lazy=True)

    def __repr__(self):
        return f'<Utilizador {self.username}>'