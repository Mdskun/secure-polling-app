from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user, login_user, logout_user
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape
import re

auth = Blueprint("auth", __name__)

# Password validation constants
PASSWORD_MIN_LENGTH = 8

def validate_password_strength(password):
    """
    Validate password strength requirements.
    Returns (is_valid, error_message)
    """
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    return True, None

def validate_username(username):
    """
    Validate username format.
    Returns (is_valid, error_message)
    """
    username = username.strip() if username else ""
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 80:
        return False, "Username must be less than 80 characters"
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscore, and dash"
    return True, None

@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        # Validate username
        valid, error_msg = validate_username(username)
        if not valid:
            flash(error_msg, "error")
            return redirect(url_for("auth.register")), 400
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose a different one.", "error")
            return redirect(url_for("auth.register")), 409
        
        # Validate password strength
        valid, error_msg = validate_password_strength(password)
        if not valid:
            flash(error_msg, "error")
            return redirect(url_for("auth.register")), 400
        
        # Create new user with hashed password
        user = User(
            username=escape(username),
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("auth.login"))
    
    return render_template("register.html")

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("auth.login")), 400
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for("index"))
        
        # Generic error message - don't reveal if user exists
        flash("Invalid username or password.", "error")
        return redirect(url_for("auth.login")), 401
    
    return render_template("login.html")

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for("index"))
