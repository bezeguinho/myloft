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

# --- LIGAÇÃO À BASE DE DADOS ---
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
UPLOAD_FOLDER = '/tmp/uploads' if os.environ.get('VERCEL') == '1' else os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

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

# --- BLOQUEIO DE CACHE ---
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Email ou password incorretos.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email já existe.', 'warning')
            return redirect(url_for('register'))
        new_user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash('Conta criada! Faça login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/recuperar-password', methods=['GET', 'POST'])
def recuperar_password():
    if request.method == 'POST':
        flash('Instruções enviadas se o email existir.', 'info')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- ROTAS DE GESTÃO DE POMBOS ---
@app.route("/lista_pombos")
@login_required
def lista_pombos():
    pombos = Pombo.query.filter_by(user_id=current_user.id, oculto=False).all()
    return render_template("pombos.html", pombos=pombos, titulo="Gestão de Pombos")

@app.route("/novo_pombo", methods=['GET', 'POST'])
@login_required
def novo_pombo():
    if request.method == 'POST':
        flash('Pombo inserido!', 'success')
        return redirect(url_for('lista_pombos'))
    return render_template("pombo_form.html")

# --- ROTAS DE PERFIL (MEUS DADOS) ---
@app.route("/meus-dados/ver")
@login_required
def ver_dados():
    utilizador = Utilizador.query.filter_by(user_id=current_user.id).first()
    if not utilizador: return redirect(url_for('inserir_dados'))
    return render_template("meus_dados_ver.html", utilizador=utilizador)

@app.route("/meus-dados/inserir", methods=['GET', 'POST'])
@login_required
def inserir_dados():
    if Utilizador.query.filter_by(user_id=current_user.id).first():
        return redirect(url_for('editar_dados'))
    if request.method == 'POST':
        novo = Utilizador(
            nome=request.form.get('nome'), localberry=request.form.get('localidade'),
            telefone=request.form.get('telefone'), email=request.form.get('email'),
            user_id=current_user.id
        )
        foto = request.files.get('foto')
        if foto and foto.filename:
            filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            novo.foto = 'uploads/' + filename
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('ver_dados'))
    return render_template("meus_dados_form.html", modo_edicao=False)

@app.route("/meus-dados/editar", methods=['GET', 'POST'])
@login_required
def editar_dados():
    utilizador = Utilizador.query.filter_by(user_id=current_user.id).first()
    if not utilizador: return redirect(url_for('inserir_dados'))
    if request.method == 'POST':
        utilizador.nome = request.form.get('nome')
        utilizador.localberry = request.form.get('localidade')
        utilizador.telefone = request.form.get('telefone')
        utilizador.email = request.form.get('email')
        foto = request.files.get('foto')
        if foto and foto.filename:
            filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            utilizador.foto = 'uploads/' + filename
        db.session.commit()
        return redirect(url_for('ver_dados'))
    return render_template("meus_dados_editar.html", utilizador=utilizador)

@app.route("/pedigree/gerar")
@login_required
def gerar_pedigree(): return render_template("gerar_pedigree.html")

@app.route('/reparar_bd')
def reparar_bd():
    from sqlalchemy import text
    try:
        db.session.execute(text("DROP TABLE IF EXISTS pombos CASCADE; DROP TABLE IF EXISTS users CASCADE; DROP TABLE IF EXISTS utilizadores_perfil CASCADE;"))
        db.session.commit()
        db.create_all()
        return "BD Limpa!"
    except Exception as e: return str(e)

@app.errorhandler(Exception)
def handle_exception(e):
    return f"Erro: <pre>{traceback.format_exc()}</pre>", 500

application = app
if __name__ == '__main__': app.run(debug=True)