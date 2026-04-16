import os
import traceback # Ferramenta de Raio-X
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-myloft-2026'

# --- LIGAÇÃO DB COM PROTEÇÃO ---
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

# --- OS TEUS MODELOS ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

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
    oculto = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROTAS DA TUA APLICAÇÃO ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email').lower()).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash("Email ou Password incorretos.", "danger")
    return render_template('login.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        if User.query.filter_by(email=email).first():
            flash("Email já registado.", "danger")
            return redirect(url_for('register'))
        new_user = User(email=email, password_hash=generate_password_hash(request.form.get('password')))
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Conta criada com sucesso! Por favor, faça login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            return f"Erro ao gravar na DB: {e}"
    return render_template('register.html')

@app.route("/meus-dados/ver")
@login_required
def ver_dados():
    utilizador = Utilizador.query.filter_by(user_id=current_user.id).first()
    if not utilizador:
        utilizador = Utilizador(user_id=current_user.id)
        db.session.add(utilizador)
        db.session.commit()
    return render_template("meus_dados_ver.html", utilizador=utilizador)

@app.route("/novo_pombo", methods=['GET', 'POST'])
@login_required
def novo_pombo():
    anos_lista = list(range(datetime.now().year, 1990, -1))
    if request.method == 'POST':
        novo = Pombo(
            anilha=request.form.get('anilha'), nome=request.form.get('nome'),
            ano=int(request.form.get('ano') or 0), sexo=request.form.get('sexo'),
            cor=request.form.get('cor'), categoria=request.form.get('categoria'),
            pai=request.form.get('pai'), mae=request.form.get('mae'),
            obs=request.form.get('obs'), user_id=current_user.id,
            oculto=True if request.form.get('oculto') == 'on' else False
        )
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('lista_pombos'))
    return render_template("pombo_form.html", anos_lista=anos_lista)

@app.route("/lista_pombos") @login_required
def lista_pombos():
    pombos = Pombo.query.filter_by(user_id=current_user.id, oculto=False).all()
    return render_template("pombos.html", pombos=pombos, titulo="TODOS OS POMBOS")

@app.route("/reprodutores") @login_required
def reprodutores():
    pombos = Pombo.query.filter_by(user_id=current_user.id, categoria="Reprodutor", oculto=False).all()
    return render_template("pombos.html", pombos=pombos, titulo="REPRODUTORES")

@app.route("/voadores") @login_required
def voadores():
    pombos = Pombo.query.filter_by(user_id=current_user.id, categoria="Voador", oculto=False).all()
    return render_template("pombos.html", pombos=pombos, titulo="VOADORES")

@app.route("/cedidos") @login_required
def cedidos():
    pombos = Pombo.query.filter_by(user_id=current_user.id, categoria="Cedido", oculto=False).all()
    return render_template("pombos.html", pombos=pombos, titulo="CEDIDOS")

@app.route("/pombos_ocultos") @login_required
def pombos_ocultos():
    pombos = Pombo.query.filter_by(user_id=current_user.id, oculto=True).all()
    return render_template("pombos.html", pombos=pombos, titulo="POMBOS OCULTOS")

@app.route("/pedigree/gerar") @login_required
def gerar_pedigree():
    return render_template("gerar_pedigree.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- A ROTA RAIO-X PARA APANHAR O ERRO ---
@app.route("/limpar_tudo")
def limpar_tudo():
    try:
        db.drop_all()
        db.create_all()
        return "<h3>Base de Dados criada com sucesso!</h3><p>Volta ao site e cria a tua conta.</p>"
    except Exception as e:
        erro = traceback.format_exc()
        return f"""
        <h2>Apanhámos o Erro!</h2>
        <p>A Base de Dados rejeitou a ligação. Envia-me um print deste quadro vermelho para resolvermos a fonte do problema:</p>
        <pre style='background-color: #ffe6e6; color: #990000; padding: 15px; border: 1px solid #cc0000; border-radius: 5px; white-space: pre-wrap;'>{erro}</pre>
        """

if __name__ == "__main__":
    app.run(debug=True)