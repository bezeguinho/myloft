from main import app, db

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Base de dados recriada com sucesso!")
