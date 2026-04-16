import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-myloft-2026'

uri = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
if uri and uri.startswith('postgres://'):
    uri = uri.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///local.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Utilizador(db.Model):
    __tablename__ = 'utilizadores_perfil'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    localidade = db.Column(db.String(100))
    email = db.Column(db.String(120))
    telefone = db.Column(db.String(20))
    foto = db.Column(db.String(255))
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

with app.app_context():
    db.create_all()

@app.route("/limpar_tudo")
def limpar_tudo():
    with app.app_context():
        db.drop_all()
        db.create_all()
    return "<h3>Base de Dados Reiniciada!</h3><p>Crie uma nova conta.</p>"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/novo_pombo", methods=['GET', 'POST'])
@login_required
def novo_pombo():
    anos_lista = list(range(datetime.now().year, 1990, -1))
    pombos_user = Pombo.query.filter_by(user_id=current_user.id).all()
    
    if request.method == 'POST':
        anilha_in = request.form.get('anilha')
        if Pombo.query.filter_by(anilha=anilha_in, user_id=current_user.id).first():
            flash("Pombo existente", "danger")
            return redirect(url_for('novo_pombo'))
        
        novo = Pombo(
            anilha=anilha_in,
            nome=request.form.get('nome'),
            ano=int(request.form.get('ano') or 0),
            sexo=request.form.get('sexo'),
            cor=request.form.get('cor'),
            categoria=request.form.get('categoria'),
            pai=request.form.get('pai'),
            mae=request.form.get('mae'),
            obs=request.form.get('obs'),
            oculto=True if request.form.get('oculto') == 'on' else False,
            user_id=current_user.id
        )
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('lista_pombos'))
    return render_template("pombo_form.html", anos_lista=anos_lista, pombos_user=pombos_user)

@app.route("/lista_pombos")
@login_required
def lista_pombos():
    pombos = Pombo.query.filter_by(user_id=current_user.id, oculto=False).all()
    return render_template("pombos.html", pombos=pombos, titulo="TODOS OS POMBOS")

@app.route("/reprodutores")
@login_required
def reprodutores():
    pombos = Pombo.query.filter_by(user_id=current_user.id, categoria="Reprodutor", oculto=False).all()
    return render_template("pombos.html", pombos=pombos, titulo="REPRODUTORES")

@app.route("/voadores")
@login_required
def voadores():
    pombos = Pombo.query.filter_by(user_id=current_user.id, categoria="Voador", oculto=False).all()
    return render_template("pombos.html", pombos=pombos, titulo="VOADORES")

@app.route("/cedidos")
@login_required
def cedidos():
    pombos = Pombo.query.filter_by(user_id=current_user.id, categoria="Cedido", oculto=False).all()
    return render_template("pombos.html", pombos=pombos, titulo="CEDIDOS")

@app.route("/pombos_ocultos")
@login_required
def pombos_ocultos():
    pombos = Pombo.query.filter_by(user_id=current_user.id, oculto=True).all()
    return render_template("pombos.html", pombos=pombos, titulo="POMBOS OCULTOS")

@app.route("/pedigree/gerar")
@login_required
def gerar_pedigree():
    return render_template("gerar_pedigree.html")

@app.route("/meus-dados/ver")
@login_required
def ver_dados():
    utilizador = Utilizador.query.filter_by(user_id=current_user.id).first()
    if not utilizador:
        utilizador = Utilizador(nome="Pombal", user_id=current_user.id)
        db.session.add(utilizador)
        db.session.commit()
    return render_template("meus_dados_ver.html", utilizador=utilizador)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email').lower()).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash("Email ou Password incorretos.", "danger")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        if password != confirm:
            flash("As passwords não coincidem!", "danger")
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash("Email já registado.", "danger")
            return redirect(url_for('register'))
        new_user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)