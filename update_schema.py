import os
import sqlite3

def load_env_manual():
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ[key] = val

load_env_manual()

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# Obter URL ignorando as mudancas no main.py que forçam o pg8000
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://')

engine = create_engine(db_url, connect_args={"sslmode": "require"})

with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE users ADD COLUMN data_expiracao TIMESTAMP;'))
        conn.commit()
        print("Coluna 'data_expiracao' adicionada com sucesso.")
    except Exception as e:
        print("Erro ou a coluna já existe:", e)
        conn.rollback()
        
    print("Preenchendo expiração para contas antigas...")
    result = conn.execute(text("SELECT id FROM users WHERE data_expiracao IS NULL"))
    users = result.fetchall()
    
    count = 0
    now = datetime.now() + timedelta(days=365)
    for u in users:
        conn.execute(text("UPDATE users SET data_expiracao = :data WHERE id = :idx"), {"data": now, "idx": u[0]})
        count += 1
    conn.commit()
    print(f"Tabela populada com sucesso! Atualizados {count} utilizadores.")
