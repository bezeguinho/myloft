import os
from flask import Flask, render_template, redirect, url_for, request, flash
from werkzeug.utils import secure_filename
from models import db, Pombo, Utilizador

app = Flask(__name__)

DATABASE_URL = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)
        
    # Assegurar que a conexão exige SSL (para Neon / Vercel Postgres)
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
app.config['SECRET_KEY'] = 'myloft-secret-key-123' # Necessário para flash messages

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

@app.route("/api/pombo/existe/<search>")
def api_pombo_existe(search):
    # Procura por anilha exata ou apenas pelo número
    pombo = Pombo.query.filter((Pombo.anilha == search) | (Pombo.numero == search)).first()
    
    # Se não encontrar, tenta normalizar o ano de 4 para 2 dígitos (ex: 2023 -> 23)
    if not pombo and search.startswith("PORT-"):
        parts = search.split("-")
        if len(parts) == 3 and len(parts[2]) == 4:
            year2 = parts[2][2:] # Retira os primeiros dois dígitos: 2023 -> 23
            search2 = f"PORT-{parts[1]}-{year2}"
            pombo = Pombo.query.filter_by(anilha=search2).first()

    if pombo:
        return {"existe": True, "numero": pombo.numero, "ano": pombo.ano}
    return {"existe": False}

@app.route("/pombo/pelo-numero/<numero>")
def ver_pombo_por_numero(numero):
    # Procura o pombo pelo número e redireciona para a edição
    pombo = Pombo.query.filter_by(numero=numero).first()
    if pombo:
        return redirect(url_for('editar_pombo', anilha=pombo.anilha))
    flash(f"Pombo {numero} não encontrado.", "warning")
    return redirect(request.referrer or url_for('lista_pombos'))


@app.route("/pombo/novo", methods=['GET', 'POST'])
def novo_pombo():
    import datetime
    agora = datetime.datetime.now()
    ano_atual = str(agora.year)
    
    # Valores sugeridos vindos do último pombo inserido
    last_num = request.args.get('last_num', '')
    last_ano = request.args.get('last_ano', '')
    
    suggested_num = ""
    if last_num:
        try:
            suggested_num = str(int(last_num) + 1)
        except ValueError:
            suggested_num = last_num # Mantém se não for número puro
            
    suggested_ano = last_ano if last_ano else ""

    if request.method == 'POST':
        numero = request.form.get('numero')
        ano = request.form.get('ano')
        # Formata anilha padrão: PORT-NUMERO-ANO
        anilha = f"PORT-{numero}-{ano}"
        
        nome = request.form.get('nome')
        
        sexo_input = request.form.get('sexo')
        sexo_validos = ["Macho", "Fêmea", "Por Definir"]
        sexo = sexo_input if sexo_input in sexo_validos else "Por Definir"
        
        cor = request.form.get('cor')
        pai = request.form.get('pai')
        mae = request.form.get('mae')
        categoria = request.form.get('categoria')
        cedido_para = request.form.get('cedido_para')
        descricao = request.form.get('descricao')
        oculto = True if request.form.get('oculto') else False

        new_pombo = Pombo(
            anilha=anilha,
            numero=numero,
            ano=ano,
            nome=nome,
            sexo=sexo,
            cor=cor,
            pai=pai,
            mae=mae,
            categoria=categoria,
            status='Ativo', # Valor por defeito transparente
            cedido_para=cedido_para,
            descricao=descricao,
            oculto=oculto
        )

        try:
            db.session.add(new_pombo)
            db.session.commit()
            flash('Pombo inserido com sucesso!', 'success')
            # Mantém na página de inserção com o próximo número sugerido
            return redirect(url_for('novo_pombo', last_num=numero, last_ano=ano))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao inserir pombo: {str(e)}', 'danger')
            return redirect(url_for('novo_pombo'))
            
    pombos_db = Pombo.query.all()
    todos_pombos_data = [{"n": p.numero, "s": p.sexo, "a": p.ano} for p in pombos_db]
    
    de = request.args.get('de', '')
    return render_template("pombo_form.html", 
                           suggested_num=suggested_num, 
                           suggested_ano=suggested_ano, 
                           todos_pombos_data=todos_pombos_data,
                           de=de)

@app.route("/pombo/editar/<anilha>", methods=['GET', 'POST'])
def editar_pombo(anilha):
    pombo = Pombo.query.get_or_404(anilha)
    
    if request.method == 'POST':
        # A anilha, número e ano não mudam por ser a identidade do pombo
        pombo.nome = request.form.get('nome')
        
        sexo_input = request.form.get('sexo')
        sexo_validos = ["Macho", "Fêmea", "Por Definir"]
        pombo.sexo = sexo_input if sexo_input in sexo_validos else "Por Definir"
        
        pombo.cor = request.form.get('cor')
        pombo.pai = request.form.get('pai')
        pombo.mae = request.form.get('mae')
        pombo.categoria = request.form.get('categoria')
        pombo.cedido_para = request.form.get('cedido_para')
        pombo.descricao = request.form.get('descricao')
        pombo.oculto = True if request.form.get('oculto') else False
        
        # Garante que o status não se perde na edição (importante para filtragem)
        if not pombo.status:
            pombo.status = 'Ativo'

        try:
            db.session.commit()
            flash('Pombo atualizado com sucesso!', 'success')
            de = request.form.get('de')
            return redirect(url_for('lista_pombos', categoria=de if de else 'editar'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar pombo: {str(e)}', 'danger')
            return redirect(url_for('editar_pombo', anilha=anilha))
            
    pombos_db = Pombo.query.all()
    todos_pombos_data = [{"n": p.numero, "s": p.sexo, "a": p.ano} for p in pombos_db]

    de = request.args.get('de', '')
    return render_template("pombo_form.html", 
                           pombo=pombo, 
                           modo_edicao=True, 
                           todos_pombos_data=todos_pombos_data,
                           de=de)

def seed_data():
    if Pombo.query.count() == 0:
        pombos = [
            Pombo(anilha="PORT-1234-23", numero="1234", ano="23", nome="Rel", sexo="Fêmea", cor="Azul", categoria="voador"),
            Pombo(anilha="PORT-3333-24", numero="3333", ano="24", nome="Veloz", sexo="Indefinido", cor="Indefinido", categoria="cedido"),
            Pombo(anilha="PORT-9012-24", numero="9012", ano="24", nome="Cometa", sexo="Macho", cor="Branco", categoria="voador"),
        ]
        db.session.bulk_save_objects(pombos)
        db.session.commit()

def get_colony_stats():
    # Cálculo de estatísticas globais para a dashboard e modal de totais
    todos_nao_ocultos = Pombo.query.filter_by(oculto=False).all()
    stats = {
        'total': len(todos_nao_ocultos),
        'total_f': sum(1 for p in todos_nao_ocultos if p.sexo == 'Fêmea'),
        'total_m': sum(1 for p in todos_nao_ocultos if p.sexo == 'Macho'),
        'total_i': sum(1 for p in todos_nao_ocultos if p.sexo not in ['Fêmea', 'Macho']),
        'voadores': sum(1 for p in todos_nao_ocultos if p.categoria == 'Voador'),
        'voadores_f': sum(1 for p in todos_nao_ocultos if p.categoria == 'Voador' and p.sexo == 'Fêmea'),
        'voadores_m': sum(1 for p in todos_nao_ocultos if p.categoria == 'Voador' and p.sexo == 'Macho'),
        'voadores_i': sum(1 for p in todos_nao_ocultos if p.categoria == 'Voador' and p.sexo not in ['Fêmea', 'Macho']),
        'reprodutores': sum(1 for p in todos_nao_ocultos if p.categoria == 'Reprodutor'),
        'reprodutores_f': sum(1 for p in todos_nao_ocultos if p.categoria == 'Reprodutor' and p.sexo == 'Fêmea'),
        'reprodutores_m': sum(1 for p in todos_nao_ocultos if p.categoria == 'Reprodutor' and p.sexo == 'Macho'),
        'reprodutores_i': sum(1 for p in todos_nao_ocultos if p.categoria == 'Reprodutor' and p.sexo not in ['Fêmea', 'Macho']),
        'cedidos': sum(1 for p in todos_nao_ocultos if p.categoria == 'Cedido'),
        'cedidos_f': sum(1 for p in todos_nao_ocultos if p.categoria == 'Cedido' and p.sexo == 'Fêmea'),
        'cedidos_m': sum(1 for p in todos_nao_ocultos if p.categoria == 'Cedido' and p.sexo == 'Macho'),
        'cedidos_i': sum(1 for p in todos_nao_ocultos if p.categoria == 'Cedido' and p.sexo not in ['Fêmea', 'Macho']),
    }
    return stats

@app.route("/")
def index():
    stats = get_colony_stats()
    return render_template("index.html", stats=stats)

@app.route("/pombo/apagar/<anilha>")
def apagar_pombo(anilha):
    pombo = Pombo.query.filter_by(anilha=anilha).first()
    if pombo:
        db.session.delete(pombo)
        db.session.commit()
        flash(f'Pombo {pombo.numero} apagado com sucesso!', 'success')
    else:
        flash('Pombo não encontrado.', 'danger')
    return redirect(request.referrer or url_for('lista_pombos'))

@app.route("/pedigree/gerar")
def gerar_pedigree():
    return render_template("gerar_pedigree.html")

def get_pombo_tree(numero):
    if not numero:
        return None
    pombo = Pombo.query.filter_by(numero=numero).first()
    if not pombo:
        return None
        
    return {
        'pombo': pombo,
        'pai': get_pombo_tree(pombo.pai),
        'mae': get_pombo_tree(pombo.mae)
    }

@app.route("/pedigree/view", methods=['POST'])
def view_pedigree():
    numero = request.form.get('numero')
    
    if not numero:
        flash('Por favor, indique o número do pombo.', 'warning')
        return redirect(url_for('gerar_pedigree'))
        
    tree = get_pombo_tree(numero)
    if not tree:
        flash('Pombo não encontrado.', 'danger')
        return redirect(url_for('gerar_pedigree'))
        
    utilizador = Utilizador.query.first()
    
    return render_template("pedigree_view.html", tree=tree, utilizador=utilizador)

@app.route("/pombos")
def lista_pombos():
    categoria = request.args.get('categoria')
    
    if categoria == 'reprodutor':
        pombos = Pombo.query.filter_by(categoria='Reprodutor', status='Ativo', oculto=False).all()
        titulo = "LISTA DE REPRODUTORES"
    elif categoria == 'voador':
        pombos = Pombo.query.filter_by(categoria='Voador', status='Ativo', oculto=False).all()
        titulo = "LISTA DE VOADORES"
    elif categoria == 'cedido':
        pombos = Pombo.query.filter_by(categoria='Cedido', oculto=False).all()
        titulo = "LISTA DE CEDIDOS"
    elif categoria == 'oculto':
        pombos = Pombo.query.filter_by(oculto=True).all()
        titulo = "LISTA DE POMBOS OCULTOS"
    elif categoria == 'editar':
        pombos = Pombo.query.all()
        titulo = "LISTA DE TODOS OS POMBOS"
    else:
        pombos = Pombo.query.filter_by(oculto=False).all()
        titulo = "TODOS OS POMBOS"

    # Dicionário de nomes para resolver nomes de pais na lista
    nomes_pombos = {p.numero: p.nome for p in Pombo.query.all()}
        
    stats = get_colony_stats()

    return render_template("pombos.html", 
                           pombos=pombos, 
                           titulo=titulo, 
                           nomes_pombos=nomes_pombos, 
                           modo_pesquisa=(categoria == 'editar'),
                           modo_cedidos=(categoria == 'cedido'),
                           categoria=categoria,
                           stats=stats)

@app.route("/meus-dados/inserir", methods=['GET', 'POST'])
def inserir_dados():
    # Se já existir um utilizador, redireciona para a página de ver dados
    utilizador_existente = Utilizador.query.first()
    if utilizador_existente:
        flash('Os dados já foram inseridos. Pode editá-los aqui.', 'info')
        return redirect(url_for('editar_dados'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        localidade = request.form.get('localidade')
        telefone = request.form.get('telefone')
        email = request.form.get('email')

        foto_path = None
        foto = request.files.get('foto')
        if foto and foto.filename:
            filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            foto_path = 'uploads/' + filename

        novo = Utilizador(
            nome=nome,
            localidade=localidade,
            telefone=telefone,
            email=email,
            foto=foto_path
        )

        try:
            db.session.add(novo)
            db.session.commit()
            flash('Dados inseridos com sucesso!', 'success')
            return redirect(url_for('ver_dados'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao inserir dados: {str(e)}', 'danger')
            return redirect(url_for('inserir_dados'))

    return render_template("meus_dados_form.html")

@app.route("/meus-dados/ver")
def ver_dados():
    utilizador = Utilizador.query.first()
    if not utilizador:
        flash('Ainda não inseriu os seus dados.', 'warning')
        return redirect(url_for('inserir_dados'))
    return render_template("meus_dados_ver.html", utilizador=utilizador)

@app.route("/meus-dados/editar", methods=['GET', 'POST'])
def editar_dados():
    utilizador = Utilizador.query.first()
    if not utilizador:
        flash('Ainda não inseriu os seus dados.', 'warning')
        return redirect(url_for('inserir_dados'))

    if request.method == 'POST':
        utilizador.nome = request.form.get('nome')
        utilizador.localidade = request.form.get('localidade')
        utilizador.telefone = request.form.get('telefone')
        utilizador.email = request.form.get('email')

        foto = request.files.get('foto')
        if foto and foto.filename:
            filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            utilizador.foto = 'uploads/' + filename

        try:
            db.session.commit()
            flash('Dados atualizados com sucesso!', 'success')
            return redirect(url_for('ver_dados'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar dados: {str(e)}', 'danger')
            return redirect(url_for('editar_dados'))

    return render_template("meus_dados_editar.html", utilizador=utilizador)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True)
