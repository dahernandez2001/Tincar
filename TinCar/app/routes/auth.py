from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from app.models import User
from app import db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

    contraseña = data.get('contraseña')

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT contraseña FROM users WHERE correo=%s", (correo,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and check_password(contraseña, user[0]):
        return jsonify({'mensaje': 'En reparación'}), 200
    else:
        return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401
