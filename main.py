from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import traceback

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-myloft-2026'

# --- LIGAÇÃO BLINDADA À BASE DE DADOS (Vercel/Supabase) ---
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

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DE DADOS (Tabelas) ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')

class Pombo(db.Model):
    __tablename__ = 'pombos'
    id = db.Column(db.Integer, primary_key=True)
    anilha = db.Column(db.String(50), unique=True, nullable=False)
    numero = db.Column(db.String(20))
    ano = db.Column(db.Integer)
    nome = db.Column(db.String(100))
    sexo = db.Column(db.String(20), default='Indefinido')
    cor = db.Column(db.String(50))
    pai_anilha = db.Column(db.String(50))
    mae_anilha = db.Column(db.String(50))
    categoria = db.Column(db.String(50))
    observacoes = db.Column(db.Text)
    oculto = db.Column(db.Boolean, default=False)
    cedido_para = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Garantir que as tabelas existem na Base de Dados
with app.app_context():
    db.create_all()

# --- ROTAS DE AUTENTICAÇÃO (O nosso sistema novo) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('lista_pombos'))
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
    if current_user.is_authenticated:
        return redirect(url_for('lista_pombos'))
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email já existe.', 'warning')
            return redirect(url_for('register'))
        new_user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash('Conta criada com sucesso! Faça login.', 'success')
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

# --- ROTAS DOS POMBOS (O teu trabalho recuperado!) ---

@app.route('/lista_pombos')
@app.route('/lista_pombos/<categoria>')
@login_required
def lista_pombos(categoria=None):
    query = Pombo.query.filter_by(user_id=current_user.id)
    titulo = "Todos os Pombos"
    
    if categoria == 'voador':
        query = query.filter_by(categoria='Voador')
        titulo = "Pombos Voadores"
    elif categoria == 'reprodutor':
        query = query.filter_by(categoria='Reprodutor')
        titulo = "Pombos Reprodutores"
    elif categoria == 'cedido':
        query = query.filter_by(categoria='Cedido')
        titulo = "Pombos Cedidos"
    
    pombos = query.all()
    # Usa o teu ficheiro antigo 'pombos.html' para mostrar a tabela verdadeira!
    return render_template('pombos.html', pombos=pombos, titulo=titulo, categoria=categoria)

@app.route('/novo_pombo', methods=['GET', 'POST'])
@login_required
def novo_pombo():
    if request.method == 'POST':
        numero = request.form.get('numero')
        ano = request.form.get('ano')
        anilha = f"PORT-{numero}-{ano}"
        
        if Pombo.query.filter_by(anilha=anilha).first():
            flash('Este pombo já está registado.', 'warning')
            return redirect(url_for('novo_pombo'))

        novo = Pombo(
            anilha=anilha,
            numero=numero,
            ano=int(ano),
            nome=request.form.get('nome'),
            sexo=request.form.get('sexo', 'Indefinido'),
            cor=request.form.get('cor'),
            pai_anilha=request.form.get('pai'),
            mae_anilha=request.form.get('mae'),
            categoria=request.form.get('categoria'),
            observacoes=request.form.get('descricao'),
            oculto=True if request.form.get('oculto') else False,
            cedido_para=request.form.get('cedido_para'),
            user_id=current_user.id
        )
        try:
            db.session.add(novo)
            db.session.commit()
            flash('Pombo registado com sucesso!', 'success')
            return redirect(url_for('lista_pombos', categoria=request.form.get('categoria').lower() if request.form.get('categoria') else None))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao guardar: {str(e)}", 'danger')
            
    return render_template('pombo_form.html', modo_edicao=False)

@app.route('/editar_pombo/<anilha>', methods=['GET', 'POST'])
@login_required
def editar_pombo(anilha):
    pombo = Pombo.query.filter_by(anilha=anilha, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        pombo.nome = request.form.get('nome')
        pombo.sexo = request.form.get('sexo')
        pombo.cor = request.form.get('cor')
        pombo.pai_anilha = request.form.get('pai')
        pombo.mae_anilha = request.form.get('mae')
        pombo.categoria = request.form.get('categoria')
        pombo.observacoes = request.form.get('descricao')
        pombo.oculto = True if request.form.get('oculto') else False
        pombo.cedido_para = request.form.get('cedido_para')
        try:
            db.session.commit()
            flash('Pombo atualizado com sucesso!', 'success')
            return redirect(url_for('lista_pombos', categoria=pombo.categoria.lower() if pombo.categoria else None))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar: {str(e)}", 'danger')
            
    return render_template('pombo_form.html', pombo=pombo, modo_edicao=True)

@app.route('/apagar_pombo/<anilha>')
@login_required
def apagar_pombo(anilha):
    pombo = Pombo.query.filter_by(anilha=anilha, user_id=current_user.id).first_or_404()
    categoria = pombo.categoria
    try:
        db.session.delete(pombo)
        db.session.commit()
        flash('Pombo removido com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao apagar: {str(e)}', 'danger')
    return redirect(url_for('lista_pombos', categoria=categoria.lower() if categoria else None))

# --- OUTRAS ROTAS ---

@app.route('/gerar_pedigree')
@login_required
def gerar_pedigree():
    flash('A geração de Pedigrees global estará disponível em breve!', 'info')
    return redirect(url_for('lista_pombos'))

@app.route('/ver_pombo/<numero>')
@login_required
def ver_pombo_por_numero(numero):
    pombo = Pombo.query.filter(Pombo.anilha.contains(numero), Pombo.user_id == current_user.id).first_or_404()
    return render_template('pedigree_view.html', pombo=pombo)

@app.route('/api/pombo/existe/<anilha>')
@login_required
def api_existe_pombo(anilha):
    existe = Pombo.query.filter_by(anilha=anilha).first() is not None
    return jsonify({'existe': existe})

@app.route('/ver_dados')
@login_required
def ver_dados(): return "Página dos Meus Dados (Em construção)"

@app.route('/admin_panel')
@login_required
def admin_panel(): return "Painel de Admin (Em construção)"

# --- RAIO-X DE ERROS ---
@app.errorhandler(Exception)
def handle_exception(e):
    return f"<h3>Erro detetado no código:</h3><pre>{traceback.format_exc()}</pre>", 500

application = app

if __name__ == '__main__':
    app.run(debug=True)