import os
from app import app, db, User
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import sqlalchemy

def executar_migracao_admin():
    with app.app_context():
        # Configuração do Admin
        email_alvo = "admin@myloft.pt" # Altera para o teu email de eleição
        password_final = "A_TUA_PASSWORD_SEGURA"
        
        print(f"🔍 A verificar ligação ao Supabase...")
        
        try:
            # 1. Verificar se o User já existe
            admin = User.query.filter_by(email=email_alvo).first()
            
            if not admin:
                print(f"🔨 A criar nova conta de administrador: {email_alvo}")
                hashed_pw = generate_password_hash(password_final)
                
                # Usamos a classe 'User' conforme definido no teu app.py
                novo_admin = User(
                    email=email_alvo,
                    password_hash=hashed_pw,
                    is_admin=True,
                    conta_ativa=True,
                    data_expiracao=datetime.now() + timedelta(days=365)
                )
                
                db.session.add(novo_admin)
                db.session.commit()
                print("✅ Administrador criado com sucesso!")
            else:
                print(f"ℹ️ O utilizador {email_alvo} já existe. A atualizar privilégios admin...")
                admin.is_admin = True
                admin.conta_ativa = True
                db.session.commit()
                print("✅ Privilégios atualizados!")

        except sqlalchemy.exc.InterfaceError:
            print("❌ ERRO DE REDE: Não consegui chegar ao Supabase.")
            print("👉 Verifica se o teu IP está autorizado no Dashboard do Supabase (Network Restrictions) ou se a tua net caiu.")
        except Exception as e:
            print(f"❌ ERRO CRÍTICO: {str(e)}")

if __name__ == "__main__":
    executar_migracao_admin()