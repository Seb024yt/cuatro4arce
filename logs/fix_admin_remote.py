from sqlmodel import Session, select
from app.database import create_db_and_tables, engine
from app.models import User
from app.auth import get_password_hash

def fix_admin():
    print("Initializing DB...")
    create_db_and_tables()
    with Session(engine) as session:
        print("Checking admin user...")
        user = session.exec(select(User).where(User.email == "admin@example.com")).first()
        if not user:
            print("Creating admin user...")
            user = User(email="admin@example.com", hashed_password=get_password_hash("admin123"))
            session.add(user)
        else:
            print("Updating admin user password...")
            user.hashed_password = get_password_hash("admin123")
            session.add(user)
        session.commit()
        print("Admin user fixed.")

if __name__ == "__main__":
    fix_admin()
