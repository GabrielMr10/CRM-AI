"""
Script para inicializar o banco de dados (criar tabelas iniciais)
"""
from app.core.security import get_password_hash
from app.db.session import SessionLocal, engine, Base
from app.modules.user import User

# Criar todas as tabelas
Base.metadata.create_all(bind=engine)


def init_db():
    """Inicializa o banco de dados com dados padrão"""
    db = SessionLocal()
    try:
        # Verificar se já existe um usuário admin
        admin = db.query(User).filter(User.email == "admin@crm.com").first()
        
        if not admin:
            # Criar usuário admin padrão
            admin_user = User(
                email="admin@crm.com",
                full_name="Administrador",
                hashed_password=get_password_hash("admin123"),
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("✓ Usuário admin criado com sucesso!")
            print("  Email: admin@crm.com")
            print("  Senha: admin123")
        else:
            print("✓ Usuário admin já existe")
    finally:
        db.close()


if __name__ == "__main__":
    print("Inicializando banco de dados...")
    init_db()
    print("Banco de dados inicializado com sucesso!")

