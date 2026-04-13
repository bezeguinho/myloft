import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Pombo

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma_chave_muito_segura_123')

# 1. Configuração da Base de Dados com Múltiplos Fallbacks (Vercel/Supabase)
uri = os.getenv('DATABASE_URL') or \
      os.getenv('POSTGRES_URL') or \
      os.getenv('POSTGRES_URL_NON_POOLING')

if uri:
    if uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)
    
    if 'pgbouncer' in uri:
        from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse
        parsed = urlparse(uri)
        query = parse_qsl(parsed.query, keep_blank_values=True)
        query = [(k, v) for k, v in query if k != 'pgbouncer']
        parsed = parsed._replace(query=urlencode(query))
        uri = urlunparse(parsed)
else:
    # Caso extremo: usa sqlite se nenhuma variável estiver definida para evitar FUNCTION_INVOCATION_FAILED
    uri = 'sqlite:///fallback.db'
    print("AVISO: Nenhuma variável de base de dados (DATABASE_URL/POSTGRES_URL) encontrada.")

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 2. SQLALCHEMY_ENGINE_OPTIONS (Para evitar o Timeout no Supabase)
if uri.startswith('postgresql'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "connect_args": {
            "sslmode": "require",
            "connect_timeout": 10
        },
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10
    }
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}

db.init_app(app)

# 4. Configuração do Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Tabela criação está desativada no arranque para evitar Vercel FUNCTION_INVOCATION_FAILED (timeout)
# Para forçar a criação de tabelas usa um script local ou uma rota específica.

@app.route('/init_db')
def init_db():
    try:
        with app.app_context():
            db.create_all()
        return "Tabelas criadas com sucesso!", 200
    except Exception as e:
        return f"Erro ao criar tabelas: {str(e)}", 500

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

import traceback
from werkzeug.exceptions import HTTPException

@app.errorhandler(Exception)
def handle_exception(e):
    # Passa erros HTTP normais (como 404, 403)
    if isinstance(e, HTTPException):
        return e
    
    # Formata a exceção e retorna ao utilizador (seguro para debug)
    error_trace = traceback.format_exc()
    return f"<h1>DETALHE DO ERRO 500</h1><pre>{error_trace}</pre><p>Por favor tira print a isto e envia-me!</p>", 500

# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not email or not password:
            flash('Por favor, preenche todos os campos obrigatórios.', 'danger')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('As senhas não coincidem. Tenta novamente.', 'danger')
            return render_template('register.html')
        
        try:
            # Gerar um username a partir do email para não quebrar a base de dados
            # Limitar a 50 caracteres para respeitar o limite da BD
            username = email.split('@')[0]
            if len(username) > 40:
                username = username[:40]
                
            # Verificar se o email já existe
            user_exist = User.query.filter_by(email=email).first()
            if user_exist:
                flash('Este email já está registado.', 'danger')
                return render_template('register.html')
                
            # Verificar e garantir que o username gerado é único
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
                
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password_hash=hashed_password)
            
            db.session.add(new_user)
            db.session.commit()
            flash('Conta criada com sucesso! Podes agora fazer login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            # Mostramos o erro detalhado da base de dados no ecrã para identificar falhas no Supabase
            flash(f"CRÍTICO - Erro na base de dados: {str(e)}", 'danger')
            return render_template('register.html')
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Login falhou. Verifique o seu email e senha.', 'danger')
        except Exception as e:
            flash(f"CRÍTICO - Erro de ligação à BD ao fazer login: {str(e)}", 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ROTAS DO DASHBOARD E POMBOS ---

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/pombos')
@app.route('/pombos/<categoria>')
@login_required
def lista_pombos(categoria=None):
    query = Pombo.query.filter_by(user_id=current_user.id)
    titulo = "Todos os Pombos"
    
    if categoria == 'Voador':
        query = query.filter_by(categoria='Voador')
        titulo = "Pombos Voadores"
    elif categoria == 'Reprodutor':
        query = query.filter_by(categoria='Reprodutor')
        titulo = "Pombos Reprodutores"
    elif categoria == 'Cedido':
        query = query.filter_by(categoria='Cedido')
        titulo = "Pombos Cedidos"
    
    pombos = query.all()
    return render_template('pombos.html', pombos=pombos, titulo=titulo, categoria=categoria)

@app.route('/novo_pombo', methods=['GET', 'POST'])
@login_required
def novo_pombo():
    if request.method == 'POST':
        numero = request.form.get('numero')
        ano = request.form.get('ano')
        anilha = f"PORT-{numero}-{ano}"
        
        # Verificar se já existe
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
            return redirect(url_for('lista_pombos', categoria=request.form.get('categoria')))
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
            return redirect(url_for('lista_pombos', categoria=pombo.categoria))
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
    return redirect(url_for('lista_pombos', categoria=categoria))

@app.route('/ver_pombo/<numero>')
@login_required
def ver_pombo_por_numero(numero):
    # Procura um pombo que contenha o número na anilha (ou busca exata se preferires)
    pombo = Pombo.query.filter(Pombo.anilha.contains(numero), Pombo.user_id == current_user.id).first_or_404()
    return render_template('pedigree_view.html', pombo=pombo)

@app.route('/estatisticas')
@login_required
def estatisticas():
    return render_template('estatisticas.html')

@app.route('/gerar_pedigree')
@login_required
def gerar_pedigree():
    # Passa também os pombos do utilizador se o template precisar
    pombos = Pombo.query.filter_by(user_id=current_user.id).all()
    return render_template('gerar_pedigree.html', pombos=pombos)

@app.route('/ver_dados')
@login_required
def ver_dados():
    return render_template('meus_dados_ver.html')

@app.route('/editar_dados', methods=['GET', 'POST'])
@login_required
def editar_dados():
    if request.method == 'POST':
        current_user.nome = request.form.get('nome')
        current_user.telefone = request.form.get('telefone')
        current_user.localidade = request.form.get('localidade')
        try:
            db.session.commit()
            flash('Dados atualizados com sucesso!', 'success')
            return redirect(url_for('ver_dados'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar dados: {str(e)}', 'danger')
    return render_template('meus_dados_editar.html')

@app.route('/admin_panel')
@login_required
def admin_panel():
    return render_template('admin.html')

@app.route('/inserir_dados', methods=['POST'])
@login_required
def inserir_dados():
    # Rota de placeholder para evitar falhas no meus_dados_form.html
    return redirect(url_for('ver_dados'))

# --- API ENDPOINTS ---

@app.route('/api/pombo/existe/<anilha>')
@login_required
def api_existe_pombo(anilha):
    # Se o input vier apenas como número, tentamos match parcial ou sugerimos
    existe = Pombo.query.filter_by(anilha=anilha).first() is not None
    return jsonify({'existe': existe})

if __name__ == '__main__':
    app.run(debug=True)