from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Pombo(db.Model):
    __tablename__ = 'pombos'
    
    anilha = db.Column(db.String(50), primary_key=True)
    numero = db.Column(db.String(20))
    ano = db.Column(db.String(10))
    nome = db.Column(db.String(100))
    sexo = db.Column(db.String(20), default='Indefinido') # Macho, Fêmea, Indefinido
    cor = db.Column(db.String(50), default='Indefinido')
    pai = db.Column(db.String(50)) # Anilha do pai
    mae = db.Column(db.String(50)) # Anilha da mãe
    categoria = db.Column(db.String(50)) # Reprodutor, Voador, Cedido, etc.
    status = db.Column(db.String(20), default='Ativo') # Mantido por retrocompatibilidade
    cedido_para = db.Column(db.String(100)) # Registar para quem foi cedido
    descricao = db.Column(db.Text)
    oculto = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Pombo {self.anilha}>'


class Utilizador(db.Model):
    __tablename__ = 'utilizadores'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(60))
    telefone = db.Column(db.String(25))
    email = db.Column(db.String(60))
    localidade = db.Column(db.String(60))
    foto = db.Column(db.String(300))  # caminho para o ficheiro da foto

    def __repr__(self):
        return f'<Utilizador {self.nome}>'
