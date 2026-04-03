from app import app, db
from models import Pombo

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Base de dados recriada com sucesso!")
