import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, Pombo, Utilizador

app = Flask(__name__)

# Configuração do Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Se tentar aceder sem login, vai para aqui

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Utilizador, int(user_id))

DATABASE_URL = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)
    
    if "sslmode=" not in DATABASE_URL:
        if "?" in DATABASE_URL:
            DATABASE_URL += "&sslmode=require"
        else:
            DATABASE_URL += "?sslmode=require"
            
    db_path = DATABASE_URL
else:
    IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_URL') is not None
    if IS_VERCEL:
        db_path = 'sqlite:////tmp/myloft.db'
    else:
        db_path = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'myloft.db')

app.config['SQLALCHEMY_DATABASE_URI'] = db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'myloft-secret-key-123'

IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_URL') is not None
UPLOAD_FOLDER = '/tmp/uploads' if IS_VERCEL else os.path.join(app.static_folder, 'uploads')

try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception:
    pass

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db.init_app(app)

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Warning: Could not create tables on startup. {e}")

# --- ROTAS DE ESTATÍSTICAS ---

@app.route('/estatisticas')
def estatisticas_pombos():
    from sqlalchemy import func
    
    def get_counts(status_filter=None):
        query = db.session.query(Pombo.sexo, func.count(Pombo.id))
        if status_filter:
            # Aqui usamos 'categoria' para filtrar Voadores, Reprodutores, etc.
            query = query.filter(Pombo.categoria == status_filter)
        
        counts = dict(query.group_by(Pombo.sexo).all())
        return {
            'total': sum(counts.values()),
            'f': counts.get('Fêmea', 0),
            'm': counts.get('Macho', 0),
            'i': counts.get('Indefinido', 0) or counts.get('Por Definir', 0)
        }

    geral = get_counts()
    voadores = get_counts('Voador')
    reprodutores = get_counts('Reprodutor')
    cedidos = get_counts('Cedido')

    stats = {
        'total': geral['total'], 'total_f': geral['f'], 'total_m': geral['m'], 'total_i': geral['i'],
        'voadores': voadores['total'], 'voadores_f': voadores['f'], 'voadores_m': voadores['m'], 'voadores_i': voadores['i'],
        'reprodutores': reprodutores['total'], 'reprodutores_f': reprodutores['f'], 'reprodutores_m': reprodutores['m'], 'reprodutores_i': reprodutores['i'],
        'cedidos': cedidos['total'], 'cedidos_f': cedidos['f'], 'cedidos_m': cedidos['m'], 'cedidos_i': cedidos['i']
    }

    return render_template('estatisticas.html', stats=stats)

# --- OUTRAS ROTAS ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        user = Utilizador.query.filter_by(username=username).first()
        
        # Como estamos a testar, ele vai deixar entrar se o utilizador existir
        if user:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Utilizador não encontrado!')
            
    return render_template('login.html')
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/pombo/pelo-numero/<numero>")
def ver_pombo_por_numero(numero):
    pombo = Pombo.query.filter_by(numero=numero).first()
    if pombo:
        return redirect(url_for('editar_pombo', anilha=pombo.anilha))
    flash(f"Pombo {numero} não encontrado.", "warning")
    return redirect(request.referrer or url_for('lista_pombos'))

@app.route("/pombo/novo", methods=['GET', 'POST'])
def novo_pombo():
    last_num = request.args.get('last_num', '')
    last_ano = request.args.get('last_ano', '')
    
    suggested_num = ""
    if last_num:
        try:
            suggested_num = str(int(last_num) + 1)
        except ValueError:
            suggested_num = last_num
            
    suggested_ano = last_ano if last_ano else ""

    if request.method == 'POST':
        numero = request.form.get('numero')
        ano = request.form.get('ano')
        anilha = f"PORT-{numero}-{ano}"
        nome = request.form.get('nome')
        sexo_input = request.form.get('sexo')
        sexo = sexo_input if sexo_input in ["Macho", "Fêmea", "Por Definir"] else "Por Definir"
        
        new_pombo = Pombo(
            anilha=anilha, numero=numero, ano=ano, nome=nome, sexo=sexo,
            cor=request.form.get('cor'), pai_anilha=request.form.get('pai'),
            mae_anilha=request.form.get('mae'), categoria=request.form.get('categoria'),
            status='Ativo', cedido_para=request.form.get('cedido_para'),
            observacoes=request.form.get('descricao'),
            oculto=True if request.form.get('oculto') else False
        )

        try:
            db.session.add(new_pombo)
            db.session.commit()
            flash('Pombo inserido com sucesso!', 'success')
            return redirect(url_for('novo_pombo', last_num=numero, last_ano=ano))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao inserir pombo: {str(e)}', 'danger')
            return redirect(url_for('novo_pombo'))
            
    pombos_db = Pombo.query.all()
    todos_pombos_data = [{"n": p.numero, "s": p.sexo, "a": p.ano} for p in pombos_db]
    return render_template("pombo_form.html", suggested_num=suggested_num, suggested_ano=suggested_ano, todos_pombos_data=todos_pombos_data)

@app.route("/pombo/editar/<anilha>", methods=['GET', 'POST'])
def editar_pombo(anilha):
    pombo = Pombo.query.get_or_404(anilha)
    if request.method == 'POST':
        pombo.nome = request.form.get('nome')
        pombo.sexo = request.form.get('sexo')
        pombo.cor = request.form.get('cor')
        pombo.pai_anilha = request.form.get('pai')
        pombo.mae_anilha = request.form.get('mae')
        pombo.categoria = request.form.get('categoria')
        pombo.cedido_para = request.form.get('cedido_para')
        pombo.observacoes = request.form.get('descricao')
        pombo.oculto = True if request.form.get('oculto') else False
        if not pombo.status: pombo.status = 'Ativo'

        try:
            db.session.commit()
            flash('Pombo atualizado com sucesso!', 'success')
            return redirect(url_for('lista_pombos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar: {str(e)}', 'danger')
            
    pombos_db = Pombo.query.all()
    todos_pombos_data = [{"n": p.numero, "s": p.sexo, "a": p.ano} for p in pombos_db]
    return render_template("pombo_form.html", pombo=pombo, modo_edicao=True, todos_pombos_data=todos_pombos_data)

@app.route("/pombo/apagar/<anilha>")
def apagar_pombo(anilha):
    pombo = Pombo.query.filter_by(anilha=anilha).first()
    if pombo:
        db.session.delete(pombo)
        db.session.commit()
        flash(f'Pombo {pombo.numero} apagado!', 'success')
    return redirect(url_for('lista_pombos'))

@app.route("/pombos")
def lista_pombos():
    cat = request.args.get('categoria')
    if cat == 'reprodutor': pombos = Pombo.query.filter_by(categoria='Reprodutor', oculto=False).all()
    elif cat == 'voador': pombos = Pombo.query.filter_by(categoria='Voador', oculto=False).all()
    elif cat == 'cedido': pombos = Pombo.query.filter_by(categoria='Cedido', oculto=False).all()
    else: pombos = Pombo.query.filter_by(oculto=False).all()
    
    return render_template("pombos.html", pombos=pombos, titulo="LISTA DE POMBOS", stats={})

@app.route("/meus-dados/ver")
def ver_dados():
    utilizador = Utilizador.query.first()
    return render_template("meus_dados_ver.html", utilizador=utilizador)

def seed_data():
    if Pombo.query.count() == 0:
        pombos = [
            Pombo(anilha="PORT-1234-23", numero="1234", ano="23", nome="Rel", sexo="Fêmea", categoria="Voador", oculto=False),
            Pombo(anilha="PORT-9012-24", numero="9012", ano="24", nome="Cometa", sexo="Macho", categoria="Voador", oculto=False),
        ]
        db.session.bulk_save_objects(pombos)
        db.session.commit()
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True)

@app.route("/pedigree/gerar", methods=['GET', 'POST'])
def gerar_pedigree():
    if request.method == 'POST':
        anilha_inicial = request.form.get('anilha')
        profundidade = int(request.form.get('profundidade', 3))
        # Aqui podes adicionar a lógica de geração se quiseres
        return render_template("pedigree_view.html", anilha=anilha_inicial)
    
    return render_template("gerar_pedigree.html")