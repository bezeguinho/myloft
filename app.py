import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma_chave_muito_segura_123')

# 1. Configuração da Base de Dados com Correção de Protocolo
uri = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
if uri and uri.startswith('postgres://'):
    uri = uri.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 2. SQLALCHEMY_ENGINE_OPTIONS (A "chave" para evitar o Timeout)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {
        "sslmode": "require",
        "connect_timeout": 10  # Dá 10 segundos para conectar
    },
    "pool_pre_ping": True,     # Verifica se a conexão está viva antes de usar
    "pool_recycle": 300,       # Reinicia conexões a cada 5 minutos
    "pool_size": 5,            # Limite de conexões simultâneas
    "max_overflow": 10
}

db = SQLAlchemy(app)

# 3. Modelo de Utilizador
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')

# 4. Configuração do Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

# --- ROTAS ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Utilizador ou Email já existem.', 'danger')
            return render_template('register.html')
            
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Conta criada com sucesso!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            # Mostra o erro real para sabermos se o timeout persiste
            flash(f"Erro ao criar conta: {str(e)}", 'danger')
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Login falhou.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Rotas do Dashboard (mantidas conforme o teu original)
@app.route('/dashboard')
@login_required
def dashboard(): return render_template('dashboard.html')

@app.route('/novo_pombo')
@login_required
def novo_pombo(): return render_template('pombo_form.html')

@app.route('/lista_pombos')
@login_required
def lista_pombos(): return render_template('pombos.html')

if __name__ == '__main__':
    app.run(debug=True)