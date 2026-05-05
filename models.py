from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user', 'admin'
    is_active = db.Column(db.Boolean, default=True)
    
    # --- Gestão de Subscrição ---
    plano = db.Column(db.String(20), default='free') # 'free', 'premium', 'pro'
    data_expiracao = db.Column(db.DateTime, nullable=True)
    
    # Perfil
    nome = db.Column(db.String(60))
    telefone = db.Column(db.String(25))
    localidade = db.Column(db.String(60))
    foto = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pombos = db.relationship('Pombo', backref='dono', lazy=True)

class Pombo(db.Model):
    __tablename__ = 'pombos'
    
    id = db.Column(db.BigInteger, primary_key=True)
    anilha = db.Column(db.String(50), nullable=False) # Removido unique=True aqui
    numero = db.Column(db.String(20))
    ano = db.Column(db.Integer)
    nome = db.Column(db.String(100))
    sexo = db.Column(db.String(20), default='Indefinido')
    cor = db.Column(db.String(50))
    linhagem = db.Column(db.String(200))
    
    # --- Evolução para Pedigrees Complexos ---
    # Guardamos a anilha como texto (para pais externos), 
    # mas podemos adicionar campos de ID para pais que já estão no sistema.
    pai_id = db.Column(db.BigInteger, db.ForeignKey('pombos.id'), nullable=True)
    mae_id = db.Column(db.BigInteger, db.ForeignKey('pombos.id'), nullable=True)
    
    pai_anilha = db.Column(db.String(50)) # Backup visual/externo
    mae_anilha = db.Column(db.String(50))
    
    categoria = db.Column(db.String(50)) # Reprodutor, Voador, etc.
    status = db.Column(db.String(20), default='Ativo')
    observacoes = db.Column(db.Text)
    oculto = db.Column(db.Boolean, default=False)
    
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Constraint de Unicidade: Um user não pode ter duas anilhas iguais
    __table_args__ = (
        db.UniqueConstraint('anilha', 'user_id', name='_anilha_user_uc'),
    )