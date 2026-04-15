import os
import traceback
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-myloft-2026'

# --- CONFIGURAÇÃO DB ---
uri = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
if uri and uri.startswith('postgres://'):
    uri = uri.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///local.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

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
    nome = db.Column(db.String(100))
    sexo = db.Column(db.String(20))
    categoria = db.Column(db.String(50)) # Reprodutor, Voador
    status = db.Column(db.String(50))    # Ativo, Cedido
    pai = db.Column(db.String(50))
    mae = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# --- ROTAS ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/lista_pombos")
@login_required
def lista_pombos():
    pombos = Pombo.query.filter_by(user_id=current_user.id).all()
    return render_template("pombos.html", pombos=pombos, titulo="TODOS OS POMBOS")

@app.route("/reprodutores")
@login_required
def lista_reprodutores():
    pombos = Pombo.query.filter_by(user_id=current_user.id, categoria="Reprodutor").all()
    return render_template("pombos.html", pombos=pombos, titulo="REPRODUTORES")

@app.route("/voadores")
@login_required
def lista_voadores():
    pombos = Pombo.query.filter_by(user_id=current_user.id, categoria="Voador").all()
    return render_template("pombos.html", pombos=pombos, titulo="VOADORES")

@app.route("/cedidos")
@login_required
def lista_cedidos():
    pombos = Pombo.query.filter_by(user_id=current_user.id, status="Cedido").all()
    return render_template("pombos.html", pombos=pombos, titulo="CEDIDOS")

@app.route("/pedigree/gerar", methods=['GET', 'POST'])
@login_required
def gerar_pedigree():
    if request.method == 'POST':
        anilha = request.form.get('numero')
        pombo = Pombo.query.filter_by(anilha=anilha, user_id=current_user.id).first()
        if pombo:
            dono = Utilizador.query.filter_by(user_id=current_user.id).first()
            return render_template("pedigree_view.html", pombo=pombo, dono=dono)
        flash("Pombo não encontrado!", "warning")
    return render_template("gerar_pedigree.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email').lower()).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/meus-dados/ver")
@login_required
def ver_dados():
    utilizador = Utilizador.query.filter_by(user_id=current_user.id).first()
    return render_template("meus_dados_ver.html", utilizador=