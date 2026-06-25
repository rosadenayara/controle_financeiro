from flask import Blueprint, render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from app.models import User
from app.extensions import db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form.get("confirm_password", "")

        if password != confirm_password:
            flash("As senhas não coincidem. Tente novamente.", "danger")
            return redirect(url_for("auth.register"))

        if len(password) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return redirect(url_for("auth.register"))

        # Verificar se o email já existe
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Este email já está cadastrado. Tente fazer login.", "danger")
            return redirect(url_for("auth.register"))

        user = User(email=email, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()

        flash("Conta criada com sucesso! Faça login para continuar.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    email_digitado = ""

    if request.method == "POST":
        email_digitado = request.form.get("email", "").strip()
        user = User.query.filter_by(email=email_digitado).first()

        if not user:
            erro = "not_found"
        elif not check_password_hash(user.password, request.form.get("password", "")):
            erro = "wrong_password"
        else:
            login_user(user)
            return redirect(url_for("dashboard.home"))

    return render_template("auth/login.html", erro=erro, email_digitado=email_digitado)


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))