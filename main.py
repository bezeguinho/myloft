import os
import re
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-myloft-2026'

db_url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
if db_url:
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    if 'sslmode' not in db_url:
        db_url += '?sslmode=require'
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/local.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DE BASE DE DADOS ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    conta_ativa = db.Column(db.Boolean, default=True) 

class Utilizador(db.Model):
    __tablename__ = 'utilizadores_perfil'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), default="Nome do Columbófilo")
    localidade = db.Column(db.String(100), default="")
    telefone = db.Column(db.String(20), default="")
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class Pombo(db.Model):
    __tablename__ = 'pombos'
    id = db.Column(db.Integer, primary_key=True)
    anilha = db.Column(db.String(50), nullable=False)
    nome = db.Column(db.String(100))
    ano = db.Column(db.Integer, nullable=False)
    sexo = db.Column(db.String(20), nullable=False)
    cor = db.Column(db.String(50))
    categoria = db.Column(db.String(50), nullable=False)
    pai = db.Column(db.String(50))
    mae = db.Column(db.String(50))
    obs = db.Column(db.Text)
    cedido_a = db.Column(db.String(100))
    oculto = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.errorhandler(Exception)
def handle_exception(e):
    return f"""
    <div style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1 style="color: #dc3545;">Temos de Atualizar a Base de Dados</h1>
        <a href="/limpar_tudo" style="background-color: #0d6efd; color: white; padding: 15px 30px; border-radius: 8px; text-decoration: none; font-weight: bold;">
            CLICAR AQUI PARA ATUALIZAR
        </a>
        <p style="margin-top:20px; color:#666;">{str(e)}</p>
    </div>
    """, 500

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: 
        return redirect(url_for('index'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email').lower()).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            if not user.conta_ativa:
                return redirect(url_for('conta_suspensa'))
            login_user(user)
            return redirect(url_for('index'))
        flash("Email ou Password incorretos.", "danger")
    return render_template('login.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        logout_user() 
    if request.method == 'POST':
        email = request.form.get('email').lower()
        if User.query.filter_by(email=email).first():
            flash("Email já registado.", "danger")
            return redirect(url_for('register'))
        new_user = User(email=email, password_hash=generate_password_hash(request.form.get('password')))
        db.session.add(new_user)
        db.session.commit()
        flash("Conta criada com sucesso! Faça login.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route("/suspenso")
def conta_suspensa():
    return render_template("suspenso.html")

# --- GESTÃO DE POMBOS ---
@app.route("/novo_pombo", methods=['GET', 'POST'])
@login_required
def novo_pombo():
    anos_lista = list(range(datetime.now().year, 1990, -1))
    if request.method == 'POST':
        anilha_final = request.form.get('anilha')
        if not anilha_final: anilha_final = request.form.get('anilha_sugerida')
            
        novo = Pombo(
            anilha=anilha_final, nome=request.form.get('nome'),
            ano=int(request.form.get('ano') or 0), sexo=request.form.get('sexo'),
            cor=request.form.get('cor'), categoria=request.form.get('categoria'),
            pai=request.form.get('pai'), mae=request.form.get('mae'),
            obs=request.form.get('obs'), cedido_a=request.form.get('cedido_a'),
            user_id=current_user.id,
            oculto=True if request.form.get('oculto') == 'on' else False
        )
        db.session.add(novo)
        db.session.commit()
        flash(f"Pombo {anilha_final} gravado com sucesso!", "success")
        return redirect(url_for('novo_pombo', saved='1'))
        
    proxima_anilha = ""
    if request.args.get('saved') == '1':
        ultimo_pombo = Pombo.query.filter_by(user_id=current_user.id).order_by(Pombo.id.desc()).first()
        if ultimo_pombo and ultimo_pombo.anilha:
            match = re.search(r'(\d+)$', ultimo_pombo.anilha)
            if match:
                numero_novo = int(match.group(1)) + 1
                tamanho = len(match.group(1))
                proxima_anilha = ultimo_pombo.anilha[:match.start()]