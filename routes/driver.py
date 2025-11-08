from flask import Blueprint, request, session, jsonify, render_template, redirect, url_for
import os
from werkzeug.utils import secure_filename
import time as _time

from models import (
    get_driver_profile,
    update_driver_profile,
    update_driver_verification_status,
    update_driver_stats,
    update_last_activity,
    check_license_validity,
    get_driver_age,
    add_notification
)

driver_bp = Blueprint('driver', __name__)


@driver_bp.route('/driver')
def driver_index():
    # Verificar sesión
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    nombre = session.get('user_name') or session.get('name') or '(usuario)'
    return render_template('index_driver.html', nombre=nombre)


@driver_bp.route('/driver/profile')
def driver_profile():
    """Página de perfil completo del conductor"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    profile = get_driver_profile(user_id)
    if not profile:
        # si no existe, redirigir con mensaje
        return redirect(url_for('driver_index'))
    profile['age'] = get_driver_age(user_id)
    profile['license_validity'] = check_license_validity(user_id)
    return render_template('driver_profile_new.html', profile=profile)


# ---- APIs para perfil de conductor (prefijo /api/driver) ----
@driver_bp.route('/api/driver/profile/<int:user_id>', methods=['GET'])
def api_get_driver_profile(user_id):
    try:
        if 'user_id' not in session or (session['user_id'] != user_id and session.get('role') != 'admin'):
            return jsonify({'error': 'No autorizado'}), 403
        profile = get_driver_profile(user_id)
        if profile:
            profile['age'] = get_driver_age(user_id)
            profile['license_validity'] = check_license_validity(user_id)
            return jsonify(profile), 200
        return jsonify({'error': 'Perfil no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@driver_bp.route('/api/driver/profile/<int:user_id>', methods=['PUT'])
def api_update_driver_profile(user_id):
    try:
        if 'user_id' not in session or session['user_id'] != user_id:
            return jsonify({'error': 'No autorizado'}), 403
        data = request.get_json() or {}
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        success = update_driver_profile(user_id, data)
        if success:
            update_last_activity(user_id)
            return jsonify({'message': 'Perfil actualizado correctamente'}), 200
        return jsonify({'error': 'Error al actualizar perfil'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@driver_bp.route('/api/driver/profile/<int:user_id>/verify', methods=['POST'])
def api_verify_driver_documents(user_id):
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'No autorizado - Solo administradores'}), 403
        data = request.get_json() or {}
        document_verified = data.get('document_verified')
        license_verified = data.get('license_verified')
        success = update_driver_verification_status(
            user_id,
            document_verified=document_verified,
            license_verified=license_verified
        )
        if success:
            if document_verified == 'verificado' or license_verified == 'verificado':
                add_notification(user_id=user_id, type='verification_approved', message='Tus documentos han sido verificados correctamente')
            elif document_verified == 'rechazado' or license_verified == 'rechazado':
                add_notification(user_id=user_id, type='verification_rejected', message='Algunos documentos fueron rechazados. Por favor revisa tu perfil.')
            return jsonify({'message': 'Estado de verificación actualizado'}), 200
        return jsonify({'error': 'Error al actualizar verificación'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@driver_bp.route('/api/driver/stats', methods=['GET'])
def api_get_driver_stats():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'No autenticado'}), 401
        user_id = session['user_id']
        profile = get_driver_profile(user_id)
        if not profile:
            return jsonify({'error': 'Perfil no encontrado'}), 404
        stats = {
            'rating': profile.get('rating', 0),
            'total_reservations': profile.get('total_reservations', 0),
            'total_cancellations': profile.get('total_cancellations', 0),
            'account_status': profile.get('account_status'),
            'document_verified': profile.get('document_verified'),
            'license_verified': profile.get('license_verified')
        }
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@driver_bp.route('/api/driver/upload-photo', methods=['POST'])
def api_upload_driver_photo():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'No autenticado'}), 401
        if 'photo' not in request.files:
            return jsonify({'error': 'No se envió ninguna foto'}), 400
        file = request.files['photo']
        photo_type = request.form.get('type')
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        if not photo_type or photo_type not in ['profile', 'document', 'license']:
            return jsonify({'error': 'Tipo de foto inválido'}), 400
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'error': 'Formato de archivo no permitido'}), 400
        upload_folder = os.path.join('static', 'uploads', 'profiles')
        os.makedirs(upload_folder, exist_ok=True)
        user_id = session['user_id']
        timestamp = int(_time.time())
        filename = secure_filename(f"{user_id}_{photo_type}_{timestamp}_{file.filename}")
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        relative_path = f"/static/uploads/profiles/{filename}"
        field_map = {'profile': 'profile_photo', 'document': 'document_photo', 'license': 'license_photo'}
        success = update_driver_profile(user_id, {field_map[photo_type]: relative_path})
        if success:
            update_last_activity(user_id)
            return jsonify({'message': 'Foto subida correctamente', 'path': relative_path}), 200
        os.remove(filepath)
        return jsonify({'error': 'Error al actualizar base de datos'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@driver_bp.route('/api/driver/license-validity/<int:user_id>', methods=['GET'])
def api_check_license_validity(user_id):
    try:
        if 'user_id' not in session or (session['user_id'] != user_id and session.get('role') != 'admin'):
            return jsonify({'error': 'No autorizado'}), 403
        validity = check_license_validity(user_id)
        return jsonify(validity), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@driver_bp.route('/api/driver/vehicles', methods=['GET'])
def api_get_driver_vehicles():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 403
        user_id = session['user_id']
        profile = get_driver_profile(user_id)
        if not profile:
            return jsonify({'error': 'Perfil no encontrado'}), 404
        vehicles = []
        if profile.get('vehicle_plate'):
            vehicles.append({
                'plate': profile.get('vehicle_plate'),
                'brand': profile.get('vehicle_brand'),
                'model': profile.get('vehicle_model'),
                'color': profile.get('vehicle_color'),
                'year': profile.get('vehicle_year'),
                'dimensions': profile.get('vehicle_dimensions')
            })
        current_vehicle = None
        current_plate = session.get('current_vehicle_plate')
        if current_plate:
            current_vehicle = next((v for v in vehicles if v['plate'] == current_plate), None)
        elif vehicles:
            current_vehicle = vehicles[0]
            session['current_vehicle_plate'] = current_vehicle['plate']
        return jsonify({'vehicles': vehicles, 'current_vehicle': current_vehicle}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@driver_bp.route('/api/driver/select-vehicle', methods=['POST'])
def api_select_vehicle():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 403
        data = request.get_json() or {}
        plate = data.get('plate')
        if not plate:
            return jsonify({'error': 'Placa requerida'}), 400
        user_id = session['user_id']
        profile = get_driver_profile(user_id)
        if not profile or profile.get('vehicle_plate') != plate:
            return jsonify({'error': 'Vehículo no encontrado'}), 404
        session['current_vehicle_plate'] = plate
        return jsonify({'success': True, 'message': f'Vehículo {plate} seleccionado'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
