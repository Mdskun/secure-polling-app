from app import app
from models import db, User
from werkzeug.security import generate_password_hash
import os

admin_user = os.getenv("ADMINU")
admin_password = os.getenv("ADMINP")

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username=admin_user).first():
        u = User(username=admin_user, password_hash=generate_password_hash(admin_password), is_admin=True)
        db.session.add(u)
        db.session.commit()
        print(f"Admin '{admin_user}' created")
    else:
        print(f"Admin '{admin_user}' exists")
