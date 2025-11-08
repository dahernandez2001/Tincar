import os
import sqlite3
from time import time
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO
from routes.auth import auth
# Usar las funciones centralizadas de acceso a DB desde models
from models import (
    get_connection,
    create_users_table,
    add_user,
    get_user_by_email,
    create_parkings_table,
    add_parking,
    get_parkings_by_owner,
    get_parking,
    update_parking,
    delete_parking,
    create_reservations_table,
    create_reviews_table,
    get_active_parkings,
    get_reservations_count_by_driver,
    get_rating_sum_for_driver,
    add_reservation,
    add_notification,
    get_notifications_by_user,
    mark_driver_arrived,
    finish_reservation,
    get_reservation_by_driver_and_parking,
    cancel_reservation,
    get_reservation,
    add_review,
    notify_expired_reservations,
)
from models import (
    get_driver_profile,
    update_driver_profile,
    update_driver_verification_status,
    update_driver_stats,
    update_last_activity,
    check_license_validity,
    get_driver_age,
    delete_notifications_for_reservation
)
from utils.geocode import geocode_location
import requests
import threading
import time as _time

# Configuración rutas absolutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'static'),
    template_folder=os.path.join(BASE_DIR, 'templates')
)

app.secret_key = 'clave-secreta'

# Inicializar SocketIO
socketio = SocketIO(app)

# Registrar blueprints
app.register_blueprint(auth)
from routes.driver import driver_bp
from routes.parkings import parkings_bp
from routes.reservations import reservations_bp
from routes.notifications import notifications_bp
app.register_blueprint(driver_bp)
app.register_blueprint(parkings_bp)
app.register_blueprint(reservations_bp)
app.register_blueprint(notifications_bp)

# Mantener compatibilidad con llamadas antiguas a url_for('driver_index') u otras
# creando alias de endpoints sin el prefijo del blueprint.
for bp in (driver_bp, parkings_bp, reservations_bp, notifications_bp):
    for endpoint in bp.view_functions:
        full = f"{bp.name}.{endpoint}"
        if full in app.view_functions:
            app.view_functions[endpoint] = app.view_functions[full]
DB_NAME = os.path.join(BASE_DIR, 'database', 'tincar.db')

# Alias a la conexión centralizada en models.py para unificar el acceso a la DB
get_db_connection = get_connection

# Las funciones de usuarios (create, add, get) vienen de models.py: create_users_table, add_user, get_user_by_email


# === Rutas principales ===
@app.route('/')
def home():
    # Si el usuario ya está logueado, redirigir al dashboard correspondiente
    if 'user_id' in session:
        role = session.get('role')
        if role == 'conductor':
            return redirect(url_for('driver_index'))
        elif role == 'arrendador':
            return redirect(url_for('landlord_index'))
    
    return render_template('index.html')


@app.route('/servicios')
def servicios():
    return render_template('servicios.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        role = request.form.get('role')  # conductor o arrendador

        if not all([name, email, password, phone, role]):
            flash('Por favor completa todos los campos.', 'error')
            return redirect(url_for('register'))

        if get_user_by_email(email):
            flash('El correo ya está registrado', 'error')
            return redirect(url_for('register'))

        # Guardar el nuevo usuario
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('INSERT INTO users (name, email, password, phone, role) VALUES (?, ?, ?, ?, ?)',
                  (name, email, password, phone, role))
        conn.commit()
        conn.close()

        flash('Cuenta creada exitosamente, ahora inicia sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)

        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']
            print("ROL LOGUEADO:", user['role'])  # debug
            return redirect(url_for('dashboard'))
        else:
            flash('Correo o contraseña incorrectos', 'error')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, role FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    conn.close()

    # Si el usuario es arrendador, obtener sus parqueaderos desde la BD
    if user and user[2] == 'arrendador':
        try:
            parkings = get_parkings_by_owner(user[0])
        except Exception:
            # fallback: lista vacía
            parkings = []
        # Normalizar para la plantilla: incluir estado/price/time de ejemplo si faltan
        for p in parkings:
            p.setdefault('status', 'Libre')
            p.setdefault('price', '0')
            p.setdefault('time', '00:00:00')
        return render_template('dashboard_landlord.html', nombre=user[1], role=user[2], parkings=parkings)

    # Por defecto, renderizar dashboard genérico
    if user:
        return render_template('dashboard.html', nombre=user[1], role=user[2])
    # Si por alguna razón no encontramos usuario, redirigir al login
    return redirect(url_for('auth.login'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# === Ruta para conductor ===
@app.route('/driver')
def driver_index():
    # Verificar sesión
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    # Nombre de usuario (compatibilidad con distintos nombres de clave)
    nombre = session.get('user_name') or session.get('name') or '(usuario)'
    return render_template('index_driver.html', nombre=nombre)


@app.route('/landlord')
def landlord_index():
    """Dashboard para arrendador (landlord)."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, role FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return redirect(url_for('auth.login'))

    # Solo arrendadores pueden ver este dashboard
    if user[2] != 'arrendador':
        # Si no es arrendador, redirigir al dashboard genérico
        return redirect(url_for('dashboard'))

    try:
        parkings = get_parkings_by_owner(user[0])
    except Exception:
        parkings = []

    for p in parkings:
        p.setdefault('status', 'Libre')
        p.setdefault('price', '0')
        p.setdefault('time', '00:00:00')

    return render_template('dashboard_landlord.html', nombre=user[1], role=user[2], parkings=parkings)


@app.route('/driver/profile')
def driver_profile():
    """Página de perfil completo del conductor"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    from models import get_driver_profile, check_license_validity, get_driver_age
    
    user_id = session['user_id']
    profile = get_driver_profile(user_id)
    
    if not profile:
        flash('No se pudo cargar el perfil', 'error')
        return redirect(url_for('driver_index'))
    
    # Agregar datos calculados
    profile['age'] = get_driver_age(user_id)
    profile['license_validity'] = check_license_validity(user_id)
    
    return render_template('driver_profile_new.html', profile=profile)


# Parkings routes moved to `routes/parkings.py`


@app.route('/parkings/<int:parking_id>/active', methods=['POST'])
def set_parking_active(parking_id):
    """Establece el campo active para un parking (payload JSON: { active: true/false })."""
    if 'user_id' not in session:
        return {'error': 'not authenticated'}, 401
    data = request.get_json(silent=True) or {}
    # allow form-encoded too
    if not data and request.form.get('active') is not None:
        val = request.form.get('active')
        data['active'] = val.lower() in ('1','true','yes','on')

    if 'active' not in data:
        return {'error': 'missing active'}, 400
    try:
        active_value = 1 if bool(data['active']) else 0
        conn = get_connection()
        cur = conn.cursor()
        # Ensure owner owns this parking
        cur.execute('SELECT owner_id FROM parkings WHERE id = ?', (parking_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return {'error': 'not found'}, 404
        if row[0] != session['user_id']:
            conn.close()
            return {'error': 'forbidden'}, 403
        cur.execute('UPDATE parkings SET active = ? WHERE id = ?', (active_value, parking_id))
        conn.commit()
        # fetch updated parking info to return
        cur.execute('SELECT id, name, address, latitude, longitude FROM parkings WHERE id = ?', (parking_id,))
        parking_info = cur.fetchone()
        conn.close()
        if not parking_info:
            return {'error': 'not found'}, 404
        return {
            'success': True,
            'id': parking_info[0],
            'name': parking_info[1],
            'address': parking_info[2],
            'latitude': parking_info[3],
            'longitude': parking_info[4],
            'active': bool(active_value)
        }
    except Exception as e:
        return {'error': str(e)}, 500


@app.route('/parkings/<int:parking_id>', methods=['GET'])
def parking_detail(parking_id):
    if 'user_id' not in session:
        return jsonify({'error':'not authenticated'}), 401
    try:
        p = get_parking(parking_id)
        if not p:
            return jsonify({'error':'not found'}), 404
        # Only allow owner to view details
        if p['owner_id'] != session['user_id']:
            return jsonify({'error':'forbidden'}), 403
        return jsonify({'success': True, 'parking': p})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/parkings/<int:parking_id>/update', methods=['POST'])
def parking_update(parking_id):
    if 'user_id' not in session:
        return jsonify({'error':'not authenticated'}), 401
    # collect fields
    form = request.form
    data = {}
    for key in ['name','phone','email','address','department','city','housing_type','size','features']:
        if key in form:
            data[key] = form.get(key)
    # permitir actualizar coordenadas desde el modal de edición
    for key in ['latitude','longitude']:
        if key in form:
            # intentar parsear a float si existe
            raw = form.get(key)
            try:
                data[key] = float(raw) if raw not in (None, '', 'None') else None
            except ValueError:
                data[key] = None

    # Actualizar en la base de datos
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Ensure owner owns this parking
        cur.execute('SELECT owner_id FROM parkings WHERE id = ?', (parking_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return {'error': 'not found'}, 404
        if row[0] != session['user_id']:
            conn.close()
            return {'error': 'forbidden'}, 403
        # Actualizar solo los campos que fueron enviados
        set_clause = ', '.join(f"{k} = ?" for k in data.keys())
        cur.execute(f'UPDATE parkings SET {set_clause} WHERE id = ?', (*data.values(), parking_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, phone, role FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    if not user:
        return redirect(url_for('auth.logout'))  # Forzar logout si no se encuentra el usuario
    return render_template('profile.html', user=user)


@app.route('/profile/update', methods=['POST'])
def profile_update():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    data = request.form
    user_id = session['user_id']
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')

    # Validar datos mínimos
    if not all([name, email, phone]):
        return jsonify({'success': False, 'error': 'Por favor completa todos los campos.'}), 400

    try:
        conn = get_connection()
        cur = conn.cursor()
        # Actualizar usuario
        cur.execute('UPDATE users SET name = ?, email = ?, phone = ? WHERE id = ?', (name, email, phone, user_id))
        conn.commit()
        conn.close()
        # Actualizar datos en la sesión
        session['name'] = name
        session['email'] = email
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Reservations routes moved to `routes/reservations.py`
# (/reservations, /reservations/create, /reservations/<id>/cancel, and all /api/reservations/* endpoints)

# Parkings APIs moved to `routes/parkings.py`


@app.route('/api/users/profile', methods=['GET'])
def api_get_user_profile():
    """API del conductor: crear una nueva reserva."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    
    data = request.get_json(silent=True) or {}
    parking_id = data.get('parking_id')
    duration_minutes = data.get('duration_minutes', 10)
    eta_minutes = data.get('eta_minutes', 0)
    
    if not parking_id:
        return jsonify({'success': False, 'error': 'Se requiere parking_id'}), 400
    
    try:
        # Verificar si ya existe una reserva activa para este parqueadero
        existing = get_reservation_by_driver_and_parking(session['user_id'], parking_id)
        if existing and existing.get('status') not in ['cancelled', 'completed']:
            # Forzar notificación si no existe
            from models import add_notification, get_notifications_by_user
            notifications = get_notifications_by_user(session['user_id'])
            notif_exists = any(n['type'] == 'active_reservation' and n['reservation_id'] == existing['id'] for n in notifications)
            if not notif_exists:
                # Obtener nombre del garaje
                from models import get_parking
                parking = get_parking(parking_id)
                parking_name = parking['name'] if parking and 'name' in parking else 'el garaje'
                add_notification(
                    user_id=session['user_id'],
                    message=f'Tienes una reserva activa en {parking_name}.',
                    type='active_reservation',
                    reservation_id=existing['id'],
                    owner_id=parking['owner_id'] if parking and 'owner_id' in parking else None,
                    eta=existing.get('eta_minutes', 0),
                    extra_data=f'{{"parking_name": "{parking_name}", "duration": {existing.get("duration_minutes", 10)}}}'
                )
            return jsonify({'success': False, 'error': 'Ya tienes una reserva activa para este parqueadero', 'reservation': existing}), 400
        # Crear la reserva
        reservation = add_reservation(
            driver_id=session['user_id'],
            parking_id=parking_id,
            duration_minutes=duration_minutes,
            eta_minutes=eta_minutes
        )
        if not reservation:
            return jsonify({'success': False, 'error': 'No se pudo crear la reserva'}), 500
        return jsonify({
            'success': True,
            'reservation': reservation
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/profile', methods=['GET'])
def api_get_user_profile():
    """API del usuario: obtener información del perfil."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, phone, role FROM users WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        return jsonify({
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'phone': user['phone'],
            'role': user['role']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/profile/<int:user_id>', methods=['GET'])
def api_get_user_profile_by_id(user_id):
    """Obtener perfil público (limitado) de un usuario por ID. Requiere sesión autenticada."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        # Usar get_driver_profile si existe (contiene phone, emergency_phone, rating, total_reservations)
        from models import get_driver_profile
        profile = get_driver_profile(user_id)
        if not profile:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        # Construir respuesta pública (solo campos necesarios para el menú lateral)
        return jsonify({
            'success': True,
            'id': profile.get('id'),
            'name': profile.get('name'),
            'email': profile.get('email'),
            'phone': profile.get('phone'),
            'emergency_phone': profile.get('emergency_phone'),
            'profile_photo': profile.get('profile_photo'),
            'rating': profile.get('rating') or 0,
            'total_reservations': profile.get('total_reservations') or 0
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/profile/update', methods=['POST'])
def api_update_user_profile():
    """API del usuario: actualizar información del perfil."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    data = request.get_json(silent=True) or {}
    user_id = session['user_id']
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')

    # Validar datos mínimos
    if not all([name, email, phone]):
        return jsonify({'success': False, 'error': 'Por favor completa todos los campos.'}), 400

    try:
        conn = get_connection()
        cur = conn.cursor()
        # Actualizar usuario
        cur.execute('UPDATE users SET name = ?, email = ?, phone = ? WHERE id = ?', (name, email, phone, user_id))
        conn.commit()
        conn.close()
        # Actualizar datos en la sesión
        session['name'] = name
        session['email'] = email
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/parkings/<int:parking_id>/reserve', methods=['POST'])
def api_reserve_parking(parking_id):
    """API pública: reservar un parqueadero."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    data = request.get_json(silent=True) or {}
    # Validar datos
    required_fields = ['start_time', 'end_time']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'error': 'Faltan datos requeridos.'}), 400

    try:
        # Crear reserva
        reservation_id = add_reservation(driver_id=session['user_id'], parking_id=parking_id,
                                        start_time=data['start_time'], end_time=data['end_time'])
        if not reservation_id:
            return jsonify({'success': False, 'error': 'No se pudo crear la reserva.'}), 500
        return jsonify({'success': True, 'reservation_id': reservation_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === Rutas para pruebas y depuración ===
@app.route('/debug/killall')
def debug_kill_all():
    """Ruta de depuración: termina todas las sesiones y procesos de fondo."""
    if os.environ.get('FLASK_ENV') == 'development':
        os._exit(0)
    return 'OK'


@app.route('/debug/db/reset', methods=['POST'])
def debug_db_reset():
    """Ruta de depuración: reinicia la base de datos (borrar y crear tablas)."""
    if os.environ.get('FLASK_ENV') != 'development':
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Borrar datos existentes
        c.execute('DROP TABLE IF EXISTS users')
        c.execute('DROP TABLE IF EXISTS parkings')
        c.execute('DROP TABLE IF EXISTS reservations')
        c.execute('DROP TABLE IF EXISTS reviews')
        # Crear tablas nuevamente
        create_users_table()
        create_parkings_table()
        create_reservations_table()
        create_reviews_table()
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/debug/populate', methods=['POST'])
def debug_populate():
    """Ruta de depuración: llena la base de datos con datos de prueba."""
    if os.environ.get('FLASK_ENV') != 'development':
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Insertar usuarios de prueba
        c.executemany('''
            INSERT INTO users (name, email, password, phone, role) VALUES (?, ?, ?, ?, ?)
        ''', [
            ('Conductor Uno', 'conductor1@example.com', 'password', '3001112233', 'conductor'),
            ('Conductor Dos', 'conductor2@example.com', 'password', '3002233445', 'conductor'),
            ('Arrendador Uno', 'arrendador1@example.com', 'password', '3109876543', 'arrendador'),
            ('Arrendador Dos', 'arrendador2@example.com', 'password', '3108765432', 'arrendador')
        ])
        # Insertar parqueaderos de prueba
        c.executemany('''
            INSERT INTO parkings (owner_id, name, phone, email, address, department, city, housing_type, size, features, image_path, latitude, longitude, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            (3, 'Parqueadero Centro', '3001112233', 'contacto@example.com', 'Calle 10 # 10-10', 'Antioquia', 'Medellín', 'Edificio', 'Pequeño', 'Cubierto', None, 6.2442, -75.5812, 1),
            (3, 'Parqueadero Norte', '3002223344', 'contacto@example.com', 'Carrera 30 # 20-20', 'Antioquia', 'Medellín', 'Casa', 'Mediano', 'Descubierto', None, 6.2518, -75.5636, 1),
            (4, 'Parqueadero Sur', '3109876543', 'contacto@example.com', 'Avenida 80 # 10-10', 'Cundinamarca', 'Bogotá', 'Edificio', 'Grande', 'Cubierto, CCTV', None, 4.6097, -74.0817, 1),
            (4, 'Parqueadero Este', '3108765432', 'contacto@example.com', 'Transversal 50 # 20-20', 'Cundinamarca', 'Bogotá', 'Casa', 'Pequeño', 'Descubierto', None, 4.6100, -74.0700, 1)
        ])
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API para obtener los parqueaderos del arrendador (dashboard)
@app.route('/api/owner/parkings', methods=['GET'])
def api_owner_parkings():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        parkings = get_parkings_by_owner(session['user_id'])
        return jsonify({'success': True, 'parkings': parkings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


"""
Rutas y APIs de perfil de conductor.

Estas rutas estaban definidas originalmente dentro del guardia
`if __name__ == '__main__':`. Para permitir importar `app` desde
otros módulos (tests, workers, WSGI servers) se extraen y se dejan
definidas siempre cuando el paquete se importa.
"""

# Driver-related routes moved to `routes/driver.py` (blueprint)


# Crear tablas necesarias al iniciar (se dejará en el guardia __main__)
if __name__ == '__main__':
    # Create DB tables if missing and start background worker + socketio
    from models import create_notifications_table
    create_users_table()
    create_parkings_table()
    create_reservations_table()
    create_reviews_table()
    create_notifications_table()
    # Start background thread to check for expired reservations
    def _expiration_worker():
        from models import notify_expired_reservations
        while True:
            try:
                notify_expired_reservations()
            except Exception:
                pass
            _time.sleep(30)

    t = threading.Thread(target=_expiration_worker, daemon=True)
    t.start()

    port = int(os.environ.get('PORT', '5000'))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
