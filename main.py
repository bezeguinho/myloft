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
        "pool_pre_ping": True, "pool_recycle": 300, "pool_size": 5, "max_overflow": 10
    }

# --- CONFIGURAÇÃO DE UPLOADS (Fotos do Utilizador) ---
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_URL') is not None
if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')

try: os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception: pass
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
    localidade = db.Column(db.String(100))
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

with app.app_context(): db.create_all()

# --- FUNÇÕES AUXILIARES (Estatísticas e Pedigree) ---
def get_colony_stats():
    todos = Pombo.query.filter_by(user_id=current_user.id, oculto=False).all()
    return {
        'total': len(todos),
        'total_f': sum(1 for p in todos if p.sexo == 'Fêmea'),
        'total_m': sum(1 for p in todos if p.sexo == 'Macho'),
        'total_i': sum(1 for p in todos if p.sexo not in ['Fêmea', 'Macho']),
        'voadores': sum(1 for p in todos if p.categoria == 'Voador'),
        'voadores_f': sum(1 for p in todos if p.categoria == 'Voador' and p.sexo == 'Fêmea'),
        'voadores_m': sum(1 for p in todos if p.categoria == 'Voador' and p.sexo == 'Macho'),
        'voadores_i': sum(1 for p in todos if p.categoria == 'Voador' and p.sexo not in ['Fêmea', 'Macho']),
        'reprodutores': sum(1 for p in todos if p.categoria == 'Reprodutor'),
        'reprodutores_f': sum(1 for p in todos if p.categoria == 'Reprodutor' and p.sexo == 'Fêmea'),
        'reprodutores_m': sum(1 for p in todos if p.categoria == 'Reprodutor' and p.sexo == 'Macho'),
        'reprodutores_i': sum(1 for p in todos if p.categoria == 'Reprodutor' and p.sexo not in ['Fêmea', 'Macho']),
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
def index(): return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('lista_pombos'))
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('lista_pombos'))
        flash('Email ou password incorretos.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('lista_pombos'))
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
        flash('Se o email estiver registado, receberá instruções em breve.', 'info')
        return redirect(url_for('login'))
    return render_template('recuperar_password.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- ROTAS DE POMBOS E FUNCIONALIDADES ---
@app.route("/lista_pombos")
@login_required
def lista_pombos():
    categoria = request.args.get('categoria')
    query = Pombo.query.filter_by(user_id=current_user.id)
    
    if categoria == 'reprodutor':
        pombos = query.filter_by(categoria='Reprodutor', status='Ativo', oculto=False).all()
        titulo = "LISTA DE REPRODUTORES"
    elif categoria == 'voador':
        pombos = query.filter_by(categoria='Voador', status='Ativo', oculto=False).all()
        titulo = "LISTA DE VOADORES"
    elif categoria == 'cedido':
        pombos = query.filter_by(categoria='Cedido', oculto=False).all()
        titulo = "LISTA DE CEDIDOS"
    elif categoria == 'oculto':
        pombos = query.filter_by(oculto=True).all()
        titulo = "LISTA DE POMBOS OCULTOS"
    elif categoria == 'editar':
        pombos = query.all()
        titulo = "LISTA DE TODOS OS POMBOS"
    else:
        pombos = query.filter_by(oculto=False).all()
        titulo = "TODOS OS POMBOS"

    nomes_pombos = {p.numero: p.nome for p in query.all()}
    stats = get_colony_stats()

    return render_template("pombos.html", pombos=pombos, titulo=titulo, 
                           nomes_pombos=nomes_pombos, modo_pesquisa=(categoria == 'editar'),
                           modo_cedidos=(categoria == 'cedido'), categoria=categoria, stats=stats)

@app.route("/novo_pombo", methods=['GET', 'POST'])
@login_required
def novo_pombo():
    last_num = request.args.get('last_num', '')
    last_ano = request.args.get('last_ano', '')
    suggested_num = str(int(last_num) + 1) if last_num.isdigit() else last_num
    suggested_ano = last_ano

    if request.method == 'POST':
        numero, ano = request.form.get('numero'), request.form.get('ano')
        anilha = f"PORT-{numero}-{ano}"
        
        if Pombo.query.filter_by(anilha=anilha, user_id=current_user.id).first():
            flash('Este pombo já está registado.', 'warning')
            return redirect(url_for('novo_pombo'))

        novo = Pombo(
            anilha=anilha, numero=numero, ano=ano,
            nome=request.form.get('nome'),
            sexo=request.form.get('sexo', 'Por Definir'),
            cor=request.form.get('cor'),
            pai=request.form.get('pai'),
            mae=request.form.get('mae'),
            categoria=request.form.get('categoria'),
            cedido_para=request.form.get('cedido_para'),
            descricao=request.form.get('descricao'),
            oculto=True if request.form.get('oculto') else False,
            user_id=current_user.id
        )
        db.session.add(novo)
        db.session.commit()
        flash('Pombo inserido com sucesso!', 'success')
        return redirect(url_for('novo_pombo', last_num=numero, last_ano=ano))

    pombos_db = Pombo.query.filter_by(user_id=current_user.id).all()
    todos_pombos_data = [{"n": p.numero, "s": p.sexo, "a": p.ano} for p in pombos_db]
    return render_template("pombo_form.html", suggested_num=suggested_num, suggested_ano=suggested_ano, 
                           todos_pombos_data=todos_pombos_data, de=request.args.get('de', ''))

@app.route("/editar_pombo/<anilha>", methods=['GET', 'POST'])
@login_required
def editar_pombo(anilha):
    pombo = Pombo.query.filter_by(anilha=anilha, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        pombo.nome = request.form.get('nome')
        pombo.sexo = request.form.get('sexo', 'Por Definir')
        pombo.cor = request.form.get('cor')
        pombo.pai = request.form.get('pai')
        pombo.mae = request.form.get('mae')
        pombo.categoria = request.form.get('categoria')
        pombo.cedido_para = request.form.get('cedido_para')
        pombo.descricao = request.form.get('descricao')
        pombo.oculto = True if request.form.get('oculto') else False
        db.session.commit()
        flash('Pombo atualizado!', 'success')
        return redirect(url_for('lista_pombos', categoria=request.form.get('de', '')))
        
    pombos_db = Pombo.query.filter_by(user_id=current_user.id).all()
    todos_pombos_data = [{"n": p.numero, "s": p.sexo, "a": p.ano} for p in pombos_db]
    return render_template("pombo_form.html", pombo=pombo, modo_edicao=True, 
                           todos_pombos_data=todos_pombos_data, de=request.args.get('de', ''))

@app.route("/apagar_pombo/<anilha>")
@login_required
def apagar_pombo(anilha):
    pombo = Pombo.query.filter_by(anilha=anilha, user_id=current_user.id).first()
    if pombo:
        db.session.delete(pombo)
        db.session.commit()
        flash('Pombo apagado.', 'success')
    return redirect(request.referrer or url_for('lista_pombos'))

@app.route("/estatisticas")
@login_required
def estatisticas():
    return render_template("estatisticas.html", stats=get_colony_stats())

@app.