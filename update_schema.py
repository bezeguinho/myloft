from dotenv import load_dotenv
load_dotenv()

from main import app, db
from sqlalchemy import text
from datetime import datetime, timedelta

with app.app_context():
    try:
        db.session.execute(text('ALTER TABLE users ADD COLUMN data_expiracao TIMESTAMP;'))
        db.session.commit()
        print("Coluna 'data_expiracao' adicionada com sucesso.")
    except Exception as e:
        print("Erro ou a coluna já existe:", e)
        db.session.rollback()
        
    print("Preenchendo expiração para contas antigas...")
    from main import User
    users = User.query.all()
    count = 0
    for u in users:
        if not u.data_expiracao:
            # Assumimos 1 ano a partir de agora de borla para contas antigas
            u.data_expiracao = datetime.now() + timedelta(days=365)
            count += 1
    db.session.commit()
    print(f"Tabela populada com sucesso! Atualizados {count} utilizadores.")
