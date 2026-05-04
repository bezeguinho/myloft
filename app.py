import os
import re
import ssl
from dotenv import load_dotenv
load_dotenv() 

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-myloft-2026'

IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_URL') is not None

# --- CONFIGURAÇÃO DA BASE DE DADOS ---
db_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')

if not db_url:
    db_url = 'sqlite:////tmp/local.db' if IS_VERCEL else 'sqlite:///local.db'

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+pg8000://", 1)
elif db_url.startswith("postgresql://") and "+pg8000" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)

if "sslmode" in db_url:
    if "?" in db_url:
        base, query = db_url.split("?", 1)
        params = [p for p in query.split("&") if not p.startswith("sslmode")]
        db_url = base + ("?" + "&".join(params) if params else "")

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if "postgresql+pg8000" in db_url:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"connect_args": {"ssl_context": ctx}}
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}

# --- Configuração de Uploads ---
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
    data_expiracao = db.Column(db.DateTime, nullable=True)

class Utilizador(db.Model):
    __tablename__ = 'utilizadores_perfil'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), default="Nome do Columbófilo")
    localidade = db.Column(db.String(100), default="")
    telefone = db.Column(db.String(20), default="")
    email = db.Column(db.String(100)) 
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

def get_colony_stats(user_id):
    """Calcula estatísticas da colónia com apenas uma consulta à BD."""
    pombos = Pombo.query.filter_by(user_id=user_id, oculto=False).all()
    current_year = datetime.now().year
    
    # Inicialização do dicionário de estatísticas
    keys = [
        'total', 'total_f', 'total_m', 'total_i', 
        'voadores', 'voadores_f', 'voadores_m', 'voadores_i',
        'v_adultos', 'v_adultos_f', 'v_adultos_m', 'v_adultos_i', 
        'v_yearlings', 'v_yearlings_f', 'v_yearlings_m', 'v_yearlings_i', 
        'v_borrachos', 'v_borrachos_f', 'v_borrachos_m', 'v_borrachos_i',
        'reprodutores', 'reprodutores_f', 'reprodutores_m', 'reprodutores_i', 
        'cedidos', 'cedidos_f', 'cedidos_m', 'cedidos_i'
    ]
    stats = {key: 0 for key in keys}

    for p in pombos:
        stats['total'] += 1
        
        # Determinação do sufixo de sexo (_f, _m, _i)
        if p.sexo == 'Fêmea':
            sexo_sufixo = '_f'
        elif p.sexo == 'Macho':
            sexo_sufixo = '_m'
        else:
            sexo_sufixo = '_i'
            
        stats['total' + sexo_sufixo] += 1
        
        if p.categoria == 'Voador':
            stats['voadores'] += 1
            stats['voadores' + sexo_sufixo] += 1
            
            # Classificação por idade
            if p.ano < current_year - 1:
                cat_idade = 'v_adultos'
            elif p.ano == current_year - 1:
                cat_idade = 'v_yearlings'
            else:
                cat_idade = 'v_borrachos'
                
            stats[cat_idade] += 1
            stats[cat_idade + sexo_sufixo] += 1
            
        elif p.categoria == 'Reprodutor':
            stats['reprodutores'] += 1
            stats['reprodutores' + sexo_sufixo] += 1
            
        elif p.categoria == 'Cedido':
            stats['cedidos'] += 1
            stats['cedidos' + sexo_sufixo] += 1
            
    return stats

def get_pombo_tree(anilha, user_id, depth=0, max_depth=4):
    if not anilha or depth >= max_depth:
        return None
        
    pombo = None
    anilha_str = str(anilha)
    if anilha_str.isdigit():
        pombo = Pombo.query.filter_by(id=int(anilha_str), user_id=user_id).first()
    if not pombo:
        pombo = Pombo.query.filter_by(anilha=anilha_str, user_id=user_id).first()
        
    if not pombo:
        return {'pombo': None, 'p_anilha': anilha, 'nome': 'Não Registado'} 
    return {
        'pombo': pombo,
        'pai': get_pombo_tree(pombo.pai, user_id, depth + 1, max_depth),
        'mae': get_pombo_tree(pombo.mae, user_id, depth + 1, max_depth)
    }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e
    app.logger.error(f"Erro Crítico: {str(e)}", exc_info=True)
    try:
        return render_template("erro_db.html", erro=str(e)), 500
    except Exception:
        return f"<h1>Erro de Sistema</h1><p>Não foi possível carregar o template de erro. Detalhes: {str(e)}</p>", 500

# --- ROTAS DE ACESSO ---
@app.route("/ping")
def ping():
    try:
        db.session.execute(text("SELECT 1"))
        return "Ping: OK | Base de Dados: CONECTADA (pg8000 + SSL Context)"
    except Exception as e:
        return f"Ping: OK | Base de Dados: ERRO ({str(e)})", 500

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
            if user.data_expiracao and datetime.now() > user.data_expiracao:
                user.conta_ativa = False
                db.session.commit()
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
    pombo = Pombo.query.filter_by(user_id=current_user.id, anilha=search).first()
    if pombo:
        return {"existe": True, "anilha": pombo.anilha, "ano": pombo.ano}
    return {"existe": False}

@app.route('/novo_pombo', methods=['GET', 'POST'])
@login_required
def novo_pombo():
    # 1. Preparação de dados para o formulário
    anos_lista = list(range(datetime.now().year, 1990, -1))
    
    # Listas para sugestão de Pais/Mães
    machos = Pombo.query.filter_by(sexo='Macho', user_id=current_user.id).order_by(Pombo.ano.desc(), Pombo.anilha).all()
    femeas = Pombo.query.filter_by(sexo='Fêmea', user_id=current_user.id).order_by(Pombo.ano.desc(), Pombo.anilha).all()
    
    # Nota: Extração de cores únicas do utilizador para o Datalist (conforme solicitado)
    cores_query = db.session.query(Pombo.cor).filter(Pombo.user_id == current_user.id).distinct().all()
    cores_lista = sorted([c[0] for c in cores_query if c[0]]) # Limpa nulos e ordena alfabeticamente

    sugerir_anilha = ""
    sugerir_ano = ""

    if request.method == 'POST':
        anilha_input = request.form.get('anilha')
        ano_input = int(request.form.get('ano') or 0)
        
        # 2. Cirurgia: Verificação de Duplicados
        existente = Pombo.query.filter_by(anilha=anilha_input, ano=ano_input, user_id=current_user.id).first()
        if existente:
            flash(f"Atenção: Já existe um pombo com a anilha {anilha_input} do ano {ano_input}!", "danger")
            return redirect(url_for('novo_pombo'))

        # 3. Criação do Objeto
        novo = Pombo()
        novo.user_id = current_user.id
        novo.anilha = anilha_input
        novo.ano = ano_input
        novo.nome = request.form.get('nome')
        novo.cor = request.form.get('cor')
        novo.sexo = request.form.get('sexo')
        novo.categoria = request.form.get('categoria')
        
        # IDs dos progenitores vindos do JavaScript (campos ocultos)
        novo.pai = request.form.get('pai_id') or None
        novo.mae = request.form.get('mae_id') or None
        
        novo.obs = request.form.get('obs')
        novo.cedido_a = request.form.get('cedido_a')
        # Nota: Lógica do campo Oculto (Mobile-friendly toggle)
        novo.oculto = True if request.form.get('oculto') == 'on' else False

        try:
            db.session.add(novo)
            db.session.commit()
            flash("Pombo gravado com sucesso!", "success")

            # 4. Lógica de Sugestão para inserção em massa (Próximo pombo)
            try:
                sugerir_anilha = int(novo.anilha) + 1
            except:
                sugerir_anilha = novo.anilha
            sugerir_ano = novo.ano

            # Após gravar, recarregamos as cores para incluir a nova se for caso disso
            cores_query = db.session.query(Pombo.cor).filter(Pombo.user_id == current_user.id).distinct().all()
            cores_lista = sorted([c[0] for c in cores_query if c[0]])

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao gravar: {str(e)}", "danger")

    # 5. Renderização final (Garante que todos os dados chegam ao pombo_form.html)
    return render_template("pombo_form.html", 
                           pombo=None, 
                           sugerir_anilha=sugerir_anilha, 
                           sugerir_ano=sugerir_ano,
                           anos_lista=anos_lista, 
                           machos=machos, 
                           femeas=femeas,
                           cores_lista=cores_lista)
                           
@app.route('/editar_pombo/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_pombo(id):
    # 1. Busca o pombo ou retorna 404 se não existir
    pombo = Pombo.query.get_or_404(id)
    
    # Segurança: Garante que o utilizador só edita os seus próprios pombos
    if pombo.user_id != current_user.id:
        flash("Acesso negado!", "danger")
        return redirect(url_for('index'))

    # 2. Preparação de dados para o formulário
    anos_lista = list(range(datetime.now().year, 1990, -1))
    
    # Listas para sugestão de Pais/Mães (Exclui o próprio pombo para evitar erro de linhagem)
    machos = Pombo.query.filter(Pombo.sexo == 'Macho', 
                                Pombo.user_id == current_user.id, 
                                Pombo.id != id).order_by(Pombo.ano.desc(), Pombo.anilha).all()
    
    femeas = Pombo.query.filter(Pombo.sexo == 'Fêmea', 
                                Pombo.user_id == current_user.id, 
                                Pombo.id != id).order_by(Pombo.ano.desc(), Pombo.anilha).all()
    
    # Nota: Extração de cores únicas do utilizador para o Datalist
    cores_query = db.session.query(Pombo.cor).filter(Pombo.user_id == current_user.id).distinct().all()
    cores_lista = sorted([c[0] for c in cores_query if c[0]])

    if request.method == 'POST':
        # 3. Atualização dos campos básicos
        pombo.nome = request.form.get('nome')
        pombo.cor = request.form.get('cor')
        pombo.sexo = request.form.get('sexo')
        pombo.categoria = request.form.get('categoria')
        
        # IDs dos progenitores (Vêm dos inputs hidden preenchidos pelo JS)
        pombo.pai = request.form.get('pai_id') or None
        pombo.mae = request.form.get('mae_id') or None
        
        pombo.obs = request.form.get('obs')
        pombo.cedido_a = request.form.get('cedido_a')
        
        # Nota: Lógica do campo Oculto (checkbox HTML enviada como 'on')[cite: 1]
        pombo.oculto = True if request.form.get('oculto') == 'on' else False

        try:
            db.session.commit()
            flash("Alterações gravadas com sucesso!", "success")
            return redirect(url_for('editar_pombo', id=pombo.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar: {str(e)}", "danger")

    # 4. Renderização (Envia todos os dados necessários para o pombo_form.html)[cite: 1]
    return render_template("pombo_form.html", 
                           pombo=pombo, 
                           anos_lista=anos_lista, 
                           machos=machos, 
                           femeas=femeas,
                           cores_lista=cores_lista,
                           sugerir_anilha=None,
                           sugerir_ano=None)

@app.route("/lista_pombos")
@app.route("/lista_pombos/<categoria>")
@login_required
def lista_pombos(categoria=None):
    query = Pombo.query.filter_by(user_id=current_user.id)

    if categoria == 'Oculto':
        query = query.filter_by(oculto=True)
        titulo = "POMBOS OCULTOS"
    elif categoria:
        query = query.filter_by(categoria=categoria, oculto=False)
        nomes = {"Reprodutor": "REPRODUTORES", "Voador": "VOADORES", "Cedido": "CEDIDOS"}
        titulo = nomes.get(categoria, categoria.upper())
    else:
        query = query.filter_by(oculto=False)
        titulo = "TODOS OS POMBOS"

    pombos = query.order_by(Pombo.ano, Pombo.anilha).all()
    
    # CRIAMOS ESTA LINHA NOVA: Um mapa para converter ID em Anilha
    # Isto cria uma lista onde o computador consulta: "O ID 1 corresponde à Anilha X"
    todos_os_meus_pombos = Pombo.query.filter_by(user_id=current_user.id).all()
    mapa_pombos = {str(p.id): {'anilha': p.anilha, 'ano': p.ano} for p in todos_os_meus_pombos}
    
    anilhas_registadas = {p.anilha for p in todos_os_meus_pombos}
    
    return render_template("pombos.html", 
                           pombos=pombos, 
                           titulo=titulo, 
                           anilhas_registadas=anilhas_registadas,
                           mapa_pombos=mapa_pombos) # Enviamos o mapa para o HTML

@app.route("/ver_pombo/<int:id>")
@login_required
def ver_pombo(id):
    # --- A MÁGICA ESTÁ AQUI ---
    # 1º Tenta procurar pelo ID interno
    pombo = Pombo.query.filter_by(id=id, user_id=current_user.id).first()
    
    # 2º Se não encontrou pelo ID, procura pela Anilha antes de dar erro 404!
    if not pombo:
        pombo = Pombo.query.filter_by(anilha=str(id), user_id=current_user.id).first_or_404()
    # --------------------------

    # O resto do código mantém-se igualzinho e seguro
    todos_os_meus_pombos = Pombo.query.filter_by(user_id=current_user.id).all()
    mapa_pombos = {str(p.id): {'anilha': p.anilha, 'ano': p.ano} for p in todos_os_meus_pombos}

    # PESQUISA DO PAI 
    nome_pai = "---"
    pai_id_real = None
    if pombo.pai:
        pai_str = str(pombo.pai)
        pai_obj = None
        if pai_str.isdigit():
            pai_obj = Pombo.query.filter_by(id=int(pai_str), user_id=current_user.id).first()
        if not pai_obj:
            pai_obj = Pombo.query.filter_by(anilha=pai_str, user_id=current_user.id).first()
        
        if pai_obj:
            nome_pai = pai_obj.nome
            pai_id_real = pai_obj.id

    # PESQUISA DA MÃE
    nome_mae = "---"
    mae_id_real = None
    if pombo.mae:
        mae_str = str(pombo.mae)
        mae_obj = None
        if mae_str.isdigit():
            mae_obj = Pombo.query.filter_by(id=int(mae_str), user_id=current_user.id).first()
        if not mae_obj:
            mae_obj = Pombo.query.filter_by(anilha=mae_str, user_id=current_user.id).first()
            
        if mae_obj:
            nome_mae = mae_obj.nome
            mae_id_real = mae_obj.id

    return render_template("ver_pombo.html", 
                           pombo=pombo, 
                           nome_pai=nome_pai, 
                           nome_mae=nome_mae, 
                           mapa_pombos=mapa_pombos,
                           pai_id_real=pai_id_real, 
                           mae_id_real=mae_id_real)

@app.route("/eliminar_pombo/<int:id>")
@login_required
def eliminar_pombo(id):
    pombo = Pombo.query.get_or_404(id)
    
    # CIRURGIA: Procura filhos onde este pombo é pai ou mãe e limpa a ligação
    # Isso evita o erro de base de dados (Integridade Referencial)
    filhos_como_pai = Pombo.query.filter_by(pai=str(pombo.id)).all()
    for filho in filhos_como_pai:
        filho.pai = None
        
    filhos_como_mae = Pombo.query.filter_by(mae=str(pombo.id)).all()
    for filho in filhos_como_mae:
        filho.mae = None

    try:
        db.session.delete(pombo)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao eliminar: {e}")
        # Aqui podes adicionar uma mensagem de erro para o utilizador se quiseres
        
    return redirect(url_for('lista_pombos'))

@app.route("/pombo_por_anilha/<anilha>")
@login_required
def pombo_por_anilha(anilha):
    pombo = Pombo.query.filter_by(anilha=anilha, user_id=current_user.id).first()
    if pombo:
        # MUDANÇA AQUI: Agora redireciona para 'ver_pombo' em vez de 'editar_pombo'
        return redirect(url_for('ver_pombo', id=pombo.id))
    flash(f"Pombo {anilha} não encontrado.", "warning")
    return redirect(request.referrer or url_for('lista_pombos'))
@app.route("/estatisticas")
@login_required
def estatisticas():
    stats = get_colony_stats(current_user.id)
    return render_template("estatisticas.html", stats=stats)

@app.route("/pedigree/gerar")
@login_required
def gerar_pedigree():
    pombos = Pombo.query.filter_by(user_id=current_user.id).order_by(Pombo.anilha).all()
    return render_template("gerar_pedigree.html", pombos=pombos)

@app.route("/pedigree/view", methods=['POST'])
@login_required
def view_pedigree():
    anilha_input = request.form.get('anilha')
    if not anilha_input:
        flash('Por favor, indique a anilha do pombo.', 'warning')
        return redirect(url_for('gerar_pedigree'))
        
    anilha = anilha_input.split(' - ')[0].strip()
    geracoes = request.form.get('geracoes', '4')
    max_depth = 5 if geracoes == '5' else 4
    
    tree = get_pombo_tree(anilha, current_user.id, max_depth=max_depth)
    if not tree or tree.get('nome') == 'Não Registado':
        flash('Pombo não encontrado.', 'danger')
        return redirect(url_for('gerar_pedigree'))
        
    utilizador = Utilizador.query.filter_by(user_id=current_user.id).first()
    return render_template("pedigree_view.html", tree=tree, utilizador=utilizador, geracoes=geracoes)

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
        utilizador.localidade = request.form.get('localidade') 
        utilizador.telefone = request.form.get('telefone')
        utilizador.email = request.form.get('email')
        
        foto = request.files.get('foto')
        if foto and foto.filename:
            filename = secure_filename(f"perfil_{current_user.id}_{foto.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            foto.save(filepath)
            utilizador.foto = 'uploads/' + filename
        elif request.form.get('remover_foto') == '1':
            utilizador.foto = None

        try:
            db.session.commit()
            flash('Perfil atualizado com sucesso!', 'success')
            return redirect(url_for('ver_dados'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar perfil: {str(e)}', 'danger')

    return render_template("meus_dados_editar.html", utilizador=utilizador)

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Acesso restrito.", "danger")
        return redirect(url_for('index'))
    users = User.query.order_by(User.id).all()
    agora = datetime.now()
    return render_template("admin.html", users=users, agora=agora)

@app.route("/admin/toggle_conta/<int:user_id>")
@login_required
def toggle_conta(user_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    user_alvo = User.query.get(user_id)
    if user_alvo and user_alvo.id != current_user.id:
        agora = datetime.now()
        if user_alvo.conta_ativa and user_alvo.data_expiracao and agora > user_alvo.data_expiracao:
            user_alvo.conta_ativa = True
            user_alvo.data_expiracao = agora + timedelta(days=365)
            msg = f"Conta de {user_alvo.email} ativada (renovada por 1 ano)."
        else:
            user_alvo.conta_ativa = not user_alvo.conta_ativa
            if user_alvo.conta_ativa:
                user_alvo.data_expiracao = agora + timedelta(days=365)
            msg = f"Conta de {user_alvo.email} {'ativada (renovada por 1 ano)' if user_alvo.conta_ativa else 'bloqueada'}."
        db.session.commit()
        flash(msg, "success")
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

@app.route("/eliminar_utilizador/<int:user_id>", methods=['POST'])
@login_required
def eliminar_utilizador(user_id):
    # Só o admin pode executar isto
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    # Impede o admin de se apagar a si próprio
    if current_user.id == user_id:
        flash("Não podes eliminar a tua própria conta!", "danger")
        return redirect(url_for('admin_dashboard'))
        
    user_alvo = User.query.get(user_id)
    if user_alvo:
        email_apagado = user_alvo.email
        try:
            # 1. Apaga os pombos do utilizador
            Pombo.query.filter_by(user_id=user_id).delete()
            
            # 2. NOVO: Apaga o perfil associado na tabela 'utilizadores_perfil'
            from sqlalchemy import text
            db.session.execute(text("DELETE FROM utilizadores_perfil WHERE user_id = :uid"), {"uid": user_id})
            
            # 3. Finalmente, apaga a conta do utilizador em si
            db.session.delete(user_alvo)
            db.session.commit()
            
            flash(f"A conta {email_apagado} e todos os seus dados foram eliminados.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao eliminar a conta: {str(e)}", "danger")
            
    return redirect(url_for('admin_dashboard'))

@app.route("/ganhar_poderes_secretos")
@login_required
def ganhar_poderes_secretos():
    current_user.is_admin = True
    db.session.commit()
    return "<h3>BOOOM! Agora és o Dono Disto Tudo!</h3><p><a href='/admin/dashboard'>Entrar no Painel Secreto</a></p>"

@app.route("/fix-tabela")
def tabela_geral():
    return redirect(url_for('estatisticas'))
    
if __name__ == "__main__":
    app.run(debug=True)