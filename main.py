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

# Configuração da Base de Dados
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

# Configuração de Uploads
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = 'uploads' # Relativo a static

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

@app.route("/estatisticas")
@login_required
def estatisticas():
    stats = get_colony_stats(current_user.id)
    return render_template("estatisticas.html", stats=stats)

@app.route("/pedigree/gerar")
@login_required
def gerar_pedigree():
    # Passamos os pombos para o seletor no frontend
    pombos = Pombo.query.filter_by(user_id=current_user.id).all()
    return render_template("gerar_pedigree.html", pombos=pombos)

@app.route("/pedigree/view", methods=['POST'])
@login_required
def view_pedigree():
    anilha = request.form.get('anilha')
    if not anilha:
        flash('Por favor, indique a anilha do pombo.', 'warning')
        return redirect(url_for('gerar_pedigree'))
        
    tree = get_pombo_tree(anilha, current_user.id)
    if not tree or tree.get('nome') == 'Não Registado':
        flash('Pombo não encontrado.', 'danger')
        return redirect(url_for('gerar_pedigree'))
        
    utilizador = Utilizador.query.filter_by(user_id=current_user.id).first()
    return render_template("pedigree_view.html", tree=tree, utilizador=utilizador)

@app.route("/meus-dados/ver")
@login_required
def ver_dados():
    utilizador = Utilizador.query.filter_by(user_id=current_user.id).first()
    if not utilizador:
        utilizador = Utilizador(user_id=current_user.id)
        db.session.add(utilizador)
        db.session.commit()
    return render_template("meus_dados_ver.html", utilizador=utilizador)

@app.route("/meus-dados/editar", methods=['GET', 'POST'])
@login_required
def editar_dados():
    utilizador = Utilizador.query.filter_by(user_id=current_user.id).first()
    if not utilizador:
        utilizador = Utilizador(user_id=current_user.id)
        db.session.add(utilizador)
        db.session.commit()

    if request.method == 'POST':
        utilizador.nome = request.form.get('nome')
        utilizador.localidade = request.form.get('localidade') # Mapeado para o campo correto
        utilizador.telefone = request.form.get('telefone')
        utilizador.email = request.form.get('email')
        
        foto = request.files.get('foto')
        if foto and foto.filename:
            filename = secure_filename(f"perfil_{current_user.id}_{foto.filename}")
            filepath = os.path.join(app.static_folder, 'uploads', filename)
            foto.save(filepath)
            utilizador.foto = 'uploads/' + filename

        try:
            db.session.commit()
            flash('Perfil atualizado com sucesso!', 'success')
            return redirect(url_for('ver_dados'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar perfil: {str(e)}', 'danger')

    return render_template("meus_dados_editar.html", utilizador=utilizador)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- ÁREA ADMINISTRATIVA ---
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Acesso restrito.", "danger")
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template("admin.html", users=users)

@app.route("/admin/toggle_conta/<int:user_id>")
@login_required
def toggle_conta(user_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    user_alvo = User.query.get(user_id)
    if user_alvo and user_alvo.id != current_user.id:
        user_alvo.conta_ativa = not user_alvo.conta_ativa
        db.session.commit()
        flash(f"Estado da conta de {user_alvo.email} alterado.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/toggle_admin/<int:user_id>")
@login_required
def toggle_admin_role(user_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    user_alvo = User.query.get(user_id)
    if user_alvo and user_alvo.id != current_user.id:
        user_alvo.is_admin = not user_alvo.is_admin
        db.session.commit()
        flash(f"Cargo de {user_alvo.email} alterado com sucesso.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/ganhar_poderes_secretos")
@login_required
def ganhar_poderes_secretos():
    current_user.is_admin = True
    db.session.commit()
    return "<h3>BOOOM! Agora és o Dono Disto Tudo!</h3><p><a href='/admin/dashboard'>Entrar no Painel Secreto</a></p>"

@app.route("/limpar_tudo")
def limpar_tudo():
    with app.app_context():
        db.drop_all()
        db.create_all()
    return "<h3>Atualização concluída com sucesso!</h3><p><a href='/'>Clica aqui para voltar ao site</a></p>"

if __name__ == "__main__":
    app.run(debug=True)