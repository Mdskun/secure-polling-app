from app import app
from models import db, User
from werkzeug.security import generate_password_hash
import os

admin_user = os.getenv("ADMINU")
admin_password = os.getenv("ADMINP")

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username=admin_user).first():
        u = User(username="admin", password_hash=generate_password_hash(admin_password), is_admin=True)
        db.session.add(u)
        db.session.commit()
        print("Admin created")
    else:
        print("Admin exists")
