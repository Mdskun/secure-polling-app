from flask import Flask, render_template
from flask_login import LoginManager
from models import db, User, Poll
from auth import auth
from admin import admin
from poll_blueprint import polls
import os
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fallback-dev-key-change-me")
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////data/polls.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure CSRF to work with regular HTML forms (not just WTForms)
app.config['WTF_CSRF_CHECK_DEFAULT'] = False  # Don't check by default
csrf = CSRFProtect(app)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def index():
    polls_list = Poll.query.all()
    return render_template("index.html", polls=polls_list)

@app.route("/health")
def health():
    return {"status": "healthy"}, 200

@app.route("/ready")
def ready():
    try:
        db.session.execute('SELECT *')
        return {"status": "ready"}, 200
    except Exception as e:
        return {"status": "not ready", "error": str(e)}, 503

# Register blueprints
app.register_blueprint(auth)
app.register_blueprint(admin)
app.register_blueprint(polls)

if __name__ == "__main__":
    app.run(debug=True)