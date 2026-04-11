import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Utilizador

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma_chave_muito_segura_123')

# Configuração da Base de Dados
uri = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
if uri and uri.startswith('postgres://'):
    uri = uri.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {"sslmode": "require"},
    "pool_pre_ping": True
}

# Inicializar Base de Dados
db.init_app(app)

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, inicie sessão para aceder a esta página.'
login_manager.login_message_category = 'info'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Utilizador.query.get(int(user_id))

# Rota de Registo
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Verificar se o utilizador já existe
        if Utilizador.query.filter((Utilizador.username == username) | (Utilizador.email == email)).first():
            flash('Utilizador ou Email já existem.', 'danger')
            return render_template('register.html')
            
        hashed_password = generate_password_hash(password)
        new_user = Utilizador(username=username, email=email, password_hash=hashed_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Conta criada com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar conta: {str(e)}", 'danger')
            
    return render_template('register.html')

# Rota de Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Utilizador.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Bem-vindo de volta, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        
        flash('Login falhou. Verifique o seu utilizador e senha.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão terminada.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

# Placeholder routes for navigation links used in base.html
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/novo_pombo')
@login_required
def novo_pombo():
    return render_template('pombo_form.html')

@app.route('/lista_pombos')
@login_required
def lista_pombos():
    return render_template('pombos.html')

@app.route('/pedigree')
@login_required
def gerar_pedigree():
    return render_template('gerar_pedigree.html')

@app.route('/meus_dados')
@login_required
def ver_dados():
    return render_template('meus_dados_ver.html')

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.role != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('index'))
    return render_template('admin.html')

if __name__ == '__main__':
    with app.app_context():
        # db.create_all() # No automatic creation to avoid conflicts with Supabase schema managed externally
        pass
    app.run(debug=True)