import os
import datetime
import traceback
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-myloft-2026'

# --- LIGAÇÃO BLINDADA À BASE DE DADOS ---
uri = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('POSTGRES_URL_NON_POOLING')
if uri and uri.startswith('postgres://'):
    uri = uri.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///local.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if uri and uri.startswith('postgresql'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "connect_args": {"sslmode": "require", "connect_timeout": 10},
        "pool_pre_ping": True, 
        "pool_recycle": 300, 
        "pool_size": 5, 
        "max_overflow": 10
    }

# --- CONFIGURAÇÃO DE UPLOADS ---
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_URL') is not None
if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')

try: 
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception: 
    pass
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- BLOQUEIO DE CACHE ---
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# --- MODELOS DE DADOS ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')

class Utilizador(db.Model):
    __tablename__ = 'utilizadores_perfil'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    localberry = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    foto = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class Pombo(db.Model):
    __tablename__ = 'pombos'
    anilha = db.Column(db.String(50), primary_key=True)
    numero = db.Column(db.String(20))
    ano = db.Column(db.String(10))
    nome = db.Column(db.String(100))
    sexo = db.Column(db.String(20), default='Por Definir')
    cor = db.Column(db.String(50))
    pai = db.Column(db.String(50))
    mae = db.Column(db.String(50))
    categoria = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Ativo')
    cedido_para = db.Column(db.String(100))
    descricao = db.Column(db.Text)
    oculto = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context(): 
    db.create_all()

# --- FUNÇÕES AUXILIARES ---
def get_colony_stats():
    todos = Pombo.query.filter_by(user_id=current_user.id, oculto=False).all()
    return {
        'total': len(todos),
        'total_f': sum(1 for p in todos if p.sexo == 'Fêmea'),
        'total_m': sum(1 for p in todos if p.sexo == 'Macho'),
        'total_i': sum(1 for p in todos if p.sexo not in ['Fêmea', 'Macho']),
        'voadores': sum(1 for p in todos if p.categoria == 'Voador'),
        'reprodutores': sum(1 for p in todos if p.categoria == 'Reprodutor'),
        'cedidos': sum(1 for p in todos if p.categoria == 'Cedido'),
    }

def get_pombo_tree(numero, user_id):
    if not numero: return None
    pombo = Pombo.query.filter_by(numero=numero, user_id=user_id).first()
    if not pombo: return None
    return {
        'pombo': pombo,
        'pai': get_pombo_tree(pombo.pai, user_id) if pombo.pai else None,
        'mae': get_pombo_tree(pombo.mae, user_id) if pombo.mae else None
    }

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/')
def index(): 
    # Agora a página principal mostra sempre o index.html, logado ou não.
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user