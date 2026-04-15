import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class Pombo(db.Model):
    __tablename__ = 'pombos'
    anilha = db.Column(db.String(12), primary_key=True) # Max 12
    nome = db.Column(db.String(40)) # Max 40
    ano = db.Column(db.Integer, nullable=False) # Obrigatório
    cor = db.Column(db.String(30)) # Max 30
    sexo = db.Column(db.String(20), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    pai = db.Column(db.String(4)) # Apenas 4 dígitos
    mae = db.Column(db.String(4)) # Apenas 4 dígitos
    obs = db.Column(db.Text)
    cedido_a = db.Column(db.String(100))
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

@app.route("/novo_pombo", methods=['GET', 'POST'])
@login_required
def novo_pombo():
    # Lista de anos para o campo Ano (descendente)
    anos_lista = list(range(datetime.now().year, 1990, -1))
    
    # Lista de pombos do utilizador para os campos Pai e Mãe
    pombos_existentes = Pombo.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        try:
            novo = Pombo(
                anilha=request.form.get('anilha'),
                nome=request.form.get('nome'),
                ano=int(request.form.get('ano')),
                sexo=request.form.get('sexo'),
                cor=request.form.get('cor'),
                categoria=request.form.get('categoria'),
                pai=request.form.get('pai'),
                mae=request.form.get('mae'),
                obs=request.form.get('obs'),
                cedido_a=request.form.get('cedido_a'),
                user_id=current_user.id
            )
            db.session.add(novo)
            db.session.commit()
            return redirect(url_for('lista_pombos'))
        except Exception as e:
            db.session.rollback()
            flash("Erro ao gravar. Verifique os dados.", "danger")
            
    return render_template("pombo_form.html", anos_lista=anos_lista, pombos_user=pombos_existentes)

@app.route("/lista_pombos")
@login_required
def lista_pombos():
    pombos = Pombo.query.filter_by(user_id=current_user.id).all()
    return render_template("pombos.html", pombos=pombos, titulo="LISTA DE POMBOS")

# ... (outras rotas: login, reprodutores, etc., mantêm-se iguais)