from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-myloft-2026'

uri = os.getenv("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///local.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Email ou password incorretos.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email já existe.', 'warning')
            return redirect(url_for('register'))
        new_user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/recuperar-password', methods=['GET', 'POST'])
def recuperar_password():
    if request.method == 'POST':
        # NOTA: Para enviar email real, precisamos configurar Flask-Mail e um servidor SMTP.
        # Por agora, apenas mostramos a confirmação visual.
        flash('Se o email estiver registado, receberá instruções em breve.', 'info')
        return redirect(url_for('login'))
    return render_template('recuperar_password.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Rotas de suporte para o menu
@app.route('/novo_pombo')
@login_required
def novo_pombo(): return "Página em construção"

@app.route('/lista_pombos')
@login_required
def lista_pombos(): return "Página em construção"

@app.route('/gerar_pedigree')
@login_required
def gerar_pedigree(): return "Página em construção"

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

application = app

if __name__ == '__main__':
    app.run(debug=True)