import os
import sqlite3
from datetime import datetime, timedelta

def update_local_db():
    try:
        conn = sqlite3.connect('local.db')
        cursor = conn.cursor()
        
        # 1. Adicionar coluna (SQLite suporta ADD COLUMN)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN data_expiracao DATETIME")
            print("Coluna 'data_expiracao' adicionada com sucesso.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("A coluna 'data_expiracao' já existe. Continuando...")
            else:
                print(f"Aviso ao adicionar coluna: {e}")
            
        # 2. Atualizar as contas existentes para ganharem 1 ano de validade a partir de agora
        data_expiracao = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S.000000') 
        # Formato comum para suportar leitura do db.DateTime
        cursor.execute("UPDATE users SET data_expiracao = ? WHERE data_expiracao IS NULL", (data_expiracao,))
        print(f"Atualizadas {cursor.rowcount} contas antigas com a data de expiração ({data_expiracao}).")
        
        conn.commit()
        conn.close()
        print("\n--> Base de dados local atualizada com sucesso! <--\n")
    except Exception as e:
        print(f"Erro inesperado ao atualizar BD local: {e}")

if __name__ == '__main__':
    update_local_db()
