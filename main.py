import os
import re
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-myloft-2026'

IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_URL') is not None

# --- INÍCIO DA NOVA CONFIGURAÇÃO DA BASE DE DADOS ---
db_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')

if not db_url:
    if IS_VERCEL:
        db_url = 'sqlite:////tmp/local.db'
    else:
        db_url = 'sqlite:///local.db'

# Corrige automaticamente o prefixo para o SQLAlchemy moderno
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {} 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# --- FIM DA NOVA CONFIGURAÇÃO DA BASE DE DADOS ---

# Configuração de Uploads - No Vercel só podemos escrever em /tmp
if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')

try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception:
    pass

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS ---
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
    email = db.Column(db.String(100)) # Adicionado para recuperação de perfil
    foto = db.Column(db.String(255)) # Adicionado para recuperação de perfil
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

def get_colony_stats(user_id):
    # Cálculo de estatísticas filtradas por utilizador
    pombos = Pombo.query.filter_by(user_id=user_id, oculto=False).all()
    stats = {
        'total': len(pombos),
        'total_f': sum(1 for p in pombos if p.sexo == 'Fêmea'),
        'total_m': sum(1 for p in pombos if p.sexo == 'Macho'),
        'total_i': sum(1 for p in pombos if p.sexo not in ['Fêmea', 'Macho']),
        'voadores': sum(1 for p in pombos if p.categoria == 'Voador'),
        'voadores_f': sum(1 for p in pombos if p.categoria == 'Voador' and p.sexo == 'Fêmea'),
        'voadores_m': sum(1 for p in pombos if p.categoria == 'Voador' and p.sexo == 'Macho'),
        'voadores_i': sum(1 for p in pombos if p.categoria == 'Voador' and p.sexo not in ['Fêmea', 'Macho']),
        'reprodutores': sum(1 for p in pombos if p.categoria == 'Reprodutor'),
        'reprodutores_f': sum(1 for p in pombos if p.categoria == 'Reprodutor' and p.sexo == 'Fêmea'),
        'reprodutores_m': sum(1 for p in pombos if p.categoria == 'Reprodutor' and p.sexo == 'Macho'),
        'reprodutores_i': sum(1 for p in pombos if p.categoria == 'Reprodutor' and p.sexo not in ['Fêmea', 'Macho']),
        'cedidos': sum(1 for p in pombos if p.categoria == 'Cedido'),
        'cedidos_f': sum(1 for p in pombos if p.categoria == 'Cedido' and p.sexo == 'Fêmea'),
        'cedidos_m': sum(1 for p in pombos if p.categoria == 'Cedido' and p.sexo == 'Macho'),
        'cedidos_i': sum(1 for p in pombos if p.categoria == 'Cedido' and p.sexo not in ['Fêmea', 'Macho']),
    }
    return stats

def get_pombo_tree(anilha, user_id):
    if not anilha:
        return None
    pombo = Pombo.query.filter_by(anilha=anilha, user_id=user_id).first()
    if not pombo:
        return {'p_anilha': anilha, 'nome': 'Não Registado'} # Para mostrar anilhas mesmo que o pombo não esteja na DB
        
    return {
        'pombo': pombo,
        'pai': get_pombo_tree(pombo.pai, user_id),
        'mae': get_pombo_tree(pombo.mae, user_id)
    }

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
    return render_template("erro_db.html", erro=str(e)), 500

# --- ROTAS DE ACESSO ---
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
@app.route("/api/pombo/existe/<search>")
@login_required
def api_pombo_existe(search):
    # Procura por anilha no contexto do utilizador logado
    pombo = Pombo.query.filter_by(user_id=current_user.id, anilha=search).first()
    if pombo:
        return {"existe": True, "anilha": pombo.anilha, "ano": pombo.ano}
    return {"existe": False}

# --- GESTÃO DE POMBOS ---
@app.route("/novo_pombo", methods=['GET', 'POST'])
@login_required
def novo_pombo():
    anos_lista = list(range(datetime.now().year, 1990, -1))
    
    # Lógica de sugestão: tenta encontrar o último número da anilha anterior e incrementa
    proxima_anilha = ""
    ultimo_pombo = Pombo.query.filter_by(user_id=current_user.id).order_by(Pombo.id.desc()).first()
    if ultimo_pombo and ultimo_pombo.anilha:
        match = re.search(r'(\d+)$', ultimo_pombo.anilha)
        if match:
            try:
                numero_novo = int(match.group(1)) + 1
                tamanho = len(match.group(1))
                proxima_anilha = ultimo_pombo.anilha[:match.start()] + str(numero_novo).zfill(tamanho)
            except:
                proxima_anilha = ultimo_pombo.anilha
                
    if request.method == 'POST':
        anilha_form = request.form.get('anilha')
        # Se o campo anilha estiver vazio, usa a sugestão
        anilha_final = anilha_form if anilha_form and anilha_form.strip() else request.form.get('anilha_sugerida')
            
        novo = Pombo(
            anilha=anilha_final, 
            nome=request.form.get('nome'),
            ano=int(request.form.get('ano') or 0), 
            sexo=request.form.get('sexo'),
            cor=request.form.get('cor'), 
            categoria=request.form.get('categoria'),
            pai=request.form.get('pai'), 
            mae=request.form.get('mae'),
            obs=request.form.get('obs'), 
            cedido_a=request.form.get('cedido_a'),
            user_id=current_user.id,
            oculto=True if request.form.get('oculto') == 'on' else False
        )
        try:
            db.session.add(novo)
            db.session.commit()
            flash(f"Pombo {anilha_final} gravado com sucesso!", "success")
            return redirect(url_for('novo_pombo', saved='1'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao gravar pombo: {str(e)}", "danger")
            return redirect(url_for('novo_pombo'))

    return render_template("pombo_form.html", anos_lista=anos_lista, proxima_anilha=proxima_anilha)