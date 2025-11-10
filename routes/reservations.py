"""
Blueprint para manejar todas las rutas y APIs relacionadas con reservas.
Extraído de app.py para mejor organización y mantenibilidad.
"""
from flask import Blueprint, request, session, jsonify, render_template, redirect, url_for
from models import (
    get_connection,
    add_reservation,
    get_reservation_by_driver_and_parking,
    get_parking,
    add_notification,
    get_notifications_by_user,
    cancel_reservation,
    get_reservation,
    mark_driver_arrived,
    finish_reservation,
    add_review,
    update_user_rating,
    delete_notifications_for_reservation
)

reservations_bp = Blueprint('reservations', __name__)


@reservations_bp.route('/reservations')
def reservations():
    """Vista HTML de reservas del conductor"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.id, p.name, r.start_time, r.end_time, r.status
        FROM reservations r
        JOIN parkings p ON r.parking_id = p.id
        WHERE r.driver_id = ?
    ''', (session['user_id'],))
    reservations_list = cursor.fetchall()
    conn.close()
    return render_template('reservations.html', reservations=reservations_list)


@reservations_bp.route('/reservations/create', methods=['POST'])
def create_reservation():
    """Crear reserva desde formulario (deprecated - usar API)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    data = request.get_json(silent=True) or {}
    required_fields = ['parking_id', 'start_time', 'end_time']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'error': 'Faltan datos requeridos.'}), 400
    try:
        reservation_id = add_reservation(driver_id=session['user_id'], parking_id=data['parking_id'],
                                        start_time=data['start_time'], end_time=data['end_time'])
        if not reservation_id:
            return jsonify({'success': False, 'error': 'No se pudo crear la reserva.'}), 500
        return jsonify({'success': True, 'reservation_id': reservation_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/reservations/<int:reservation_id>/cancel', methods=['POST'])
def cancel_reservation_route(reservation_id):
    """Cancelar reserva desde ruta HTML (deprecated - usar API)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        result = cancel_reservation(reservation_id, session['user_id'])
        if not result:
            return jsonify({'success': False, 'error': 'No se pudo cancelar la reserva.'}), 500
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============= APIs REST =============

@reservations_bp.route('/api/reservations', methods=['POST'])
def api_create_reservation():
    """API: crear una nueva reserva"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    data = request.get_json(silent=True) or {}
    parking_id = data.get('parking_id')
    duration_minutes = data.get('duration_minutes', 10)
    eta_minutes = data.get('eta_minutes', 0)
    if not parking_id:
        return jsonify({'success': False, 'error': 'Se requiere parking_id'}), 400
    try:
        existing = get_reservation_by_driver_and_parking(session['user_id'], parking_id)
        if existing and existing.get('status') not in ['cancelled', 'completed']:
            notifications = get_notifications_by_user(session['user_id'])
            notif_exists = any(n['type'] == 'active_reservation' and n['reservation_id'] == existing['id'] for n in notifications)
            if not notif_exists:
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
        reservation = add_reservation(
            driver_id=session['user_id'],
            parking_id=parking_id,
            duration_minutes=duration_minutes,
            eta_minutes=eta_minutes
        )
        if not reservation:
            return jsonify({'success': False, 'error': 'No se pudo crear la reserva'}), 500
        return jsonify({'success': True, 'reservation': reservation})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/driver', methods=['GET'])
def api_get_driver_reservations():
    """API: obtener reservas del conductor"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.id, p.name, r.start_time, r.end_time, r.status
            FROM reservations r
            JOIN parkings p ON r.parking_id = p.id
            WHERE r.driver_id = ?
        ''', (session['user_id'],))
        reservations_list = cursor.fetchall()
        conn.close()
        return jsonify([{
            'id': r['id'],
            'parking_name': r['name'],
            'start_time': r['start_time'],
            'end_time': r['end_time'],
            'status': r['status']
        } for r in reservations_list])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/active/driver', methods=['GET'])
def api_get_active_reservations_driver():
    """API: reservas activas del conductor"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
         SELECT r.id, r.status, r.duration_minutes, r.eta_minutes, r.created_at, r.driver_id,
             u.name as driver_name, r.parking_id, p.name as parking_name, p.address, p.occupied_since,
             owner.name as owner_name
            FROM reservations r
            LEFT JOIN users u ON r.driver_id = u.id
            LEFT JOIN parkings p ON r.parking_id = p.id
            LEFT JOIN users owner ON p.owner_id = owner.id
            WHERE r.driver_id = ? AND r.status IN ('pending','arrived','active')
            ORDER BY r.created_at DESC
        ''', (session['user_id'],))
        rows = cursor.fetchall()
        conn.close()
        out = []
        for r in rows:
            try:
                owner_name = r.get('owner_name') or 'un arrendador' if hasattr(r, 'get') else 'un arrendador'
                out.append({
                    'id': r['id'],
                    'status': r['status'],
                    'occupied_since': r.get('occupied_since') if hasattr(r, 'get') else None,
                    'duration_minutes': r.get('duration_minutes') if hasattr(r, 'get') else None,
                    'eta': r.get('eta_minutes') if hasattr(r, 'get') else None,
                    'eta_minutes': r.get('eta_minutes') if hasattr(r, 'get') else None,
                    'created_at': r['created_at'],
                    'driver_id': r['driver_id'],
                    'driver_name': r['driver_name'],
                    'parking_id': r['parking_id'],
                    'parking_name': r['parking_name'],
                    'address': r['address'],
                    'owner_name': owner_name
                })
            except Exception as e:
                print(f"Error parsing row: {e}, row: {r}")
                continue
        return jsonify({'success': True, 'reservations': out})
    except Exception as e:
        import traceback
        print(f"Error in active/driver: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/active/owner', methods=['GET'])
def api_get_active_reservations_owner():
    """API: reservas activas para parqueaderos del arrendador"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
         SELECT r.id, r.status, r.duration_minutes, r.eta_minutes, r.created_at, r.driver_id,
             u.name as driver_name, r.parking_id, p.name as parking_name, p.address, p.occupied_since
            FROM reservations r
            LEFT JOIN users u ON r.driver_id = u.id
            LEFT JOIN parkings p ON r.parking_id = p.id
            WHERE p.owner_id = ? AND r.status IN ('pending','arrived','active')
            ORDER BY r.created_at DESC
        ''', (session['user_id'],))
        rows = cursor.fetchall()
        conn.close()
        out = []
        for r in rows:
            try:
                expired = False
                try:
                    if r.get('occupied_since') and r.get('duration_minutes'):
                        import datetime
                        occ = datetime.datetime.fromisoformat(r['occupied_since'])
                        now = datetime.datetime.utcnow()
                        secs = (now - occ).total_seconds()
                        elapsed_min = int((secs + 59) // 60) if secs > 0 else 0
                        expired = elapsed_min >= int(r.get('duration_minutes', 0))
                except Exception:
                    expired = False
                out.append({
                    'id': r['id'],
                    'status': r['status'],
                    'duration_minutes': r.get('duration_minutes', None) if hasattr(r, 'keys') else (r[2] if len(r) > 2 else None),
                    'eta': r.get('eta_minutes', None) if hasattr(r, 'keys') else (r[3] if len(r) > 3 else None),
                    'created_at': r['created_at'] if 'created_at' in r.keys() else (r[4] if len(r) > 4 else None),
                    'driver_id': r['driver_id'],
                    'driver_name': r['driver_name'],
                    'parking_id': r['parking_id'],
                    'parking_name': r['parking_name'],
                    'address': r['address'],
                    'occupied_since': r['occupied_since'] if 'occupied_since' in r.keys() else None,
                    'expired': expired
                })
            except Exception:
                out.append({
                    'id': r[0], 'status': r[1], 'duration_minutes': r[2] if len(r) > 2 else None,
                    'eta': r[3] if len(r) > 3 else None, 'created_at': r[4] if len(r) > 4 else None,
                    'driver_id': r[5] if len(r) > 5 else None, 'driver_name': r[6] if len(r) > 6 else None,
                    'parking_id': r[7] if len(r) > 7 else None, 'parking_name': r[8] if len(r) > 8 else None,
                    'address': r[9] if len(r) > 9 else None
                })
        return jsonify({'success': True, 'reservations': out})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/<int:reservation_id>/finish', methods=['POST'])
def api_finish_reservation(reservation_id):
    """API: finalizar reserva"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        reservation = get_reservation(reservation_id)
        if not reservation:
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT owner_id FROM parkings WHERE id = ?', (reservation['parking_id'],))
        parking = cursor.fetchone()
        conn.close()
        if not (reservation['driver_id'] == session['user_id'] or (parking and parking[0] == session['user_id'])):
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        if reservation['status'] not in ['arrived', 'active']:
            return jsonify({'success': False, 'error': 'La reserva no está activa o el conductor no ha llegado'}), 400
        data = request.get_json(silent=True) or {}
        rating = data.get('rating')
        comment = data.get('comment')
        try:
            if rating is not None:
                add_review(session['user_id'], reservation['driver_id'], reservation['parking_id'], int(rating), comment)
        except Exception:
            pass
        success = finish_reservation(reservation_id, session['user_id'])
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'No se pudo finalizar la reserva'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/<int:reservation_id>/arrived', methods=['POST'])
def api_mark_arrived(reservation_id):
    """API: marcar llegada del conductor"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        reservation = get_reservation(reservation_id)
        if not reservation:
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404
        if reservation['driver_id'] != session['user_id']:
            return jsonify({'success': False, 'error': 'No autorizado para esta reserva'}), 403
        if reservation['status'] == 'cancelled':
            return jsonify({'success': False, 'error': 'La reserva ya fue cancelada'}), 400
        success = mark_driver_arrived(reservation_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'No se pudo registrar la llegada'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/<int:reservation_id>/cancel', methods=['POST'])
def api_cancel_reservation(reservation_id):
    """API: cancelar reserva"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        user_id = session['user_id']
        result = cancel_reservation(reservation_id, user_id)
        if not result:
            return jsonify({'success': False, 'error': 'No se pudo cancelar la reserva.'}), 500
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/<int:reservation_id>/request-extra-time', methods=['POST'])
def request_extra_time(reservation_id):
    """API: solicitar tiempo extra"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        data = request.get_json() or {}
        extra_minutes = data.get('extra_minutes', 0)
        if extra_minutes not in [10, 20, 30]:
            return jsonify({'success': False, 'error': 'Minutos inválidos'}), 400
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT driver_id, parking_id FROM reservations WHERE id = ?', (reservation_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404
        driver_id, parking_id = row[0], row[1]
        if driver_id != session['user_id']:
            conn.close()
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        cur.execute('SELECT owner_id FROM parkings WHERE id = ?', (parking_id,))
        parking_row = cur.fetchone()
        if not parking_row:
            conn.close()
            return jsonify({'success': False, 'error': 'Parqueadero no encontrado'}), 404
        owner_id = parking_row[0]
        conn.close()
        add_notification(
            user_id=owner_id,
            type='extra_time_request',
            message=f'El conductor solicita {extra_minutes} minutos adicionales',
            reservation_id=reservation_id,
            owner_id=owner_id,
            extra_data={'extra_minutes': extra_minutes, 'driver_id': driver_id}
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/<int:reservation_id>/at-vehicle', methods=['POST'])
def at_vehicle(reservation_id):
    """API: conductor llegó al vehículo"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT driver_id, parking_id FROM reservations WHERE id = ?', (reservation_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404
        driver_id, parking_id = row[0], row[1]
        if driver_id != session['user_id']:
            conn.close()
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        cur.execute('SELECT owner_id FROM parkings WHERE id = ?', (parking_id,))
        parking_row = cur.fetchone()
        if not parking_row:
            conn.close()
            return jsonify({'success': False, 'error': 'Parqueadero no encontrado'}), 404
        owner_id = parking_row[0]
        conn.close()
        add_notification(
            user_id=owner_id,
            type='at_vehicle',
            message='El conductor llegó a su vehículo',
            reservation_id=reservation_id,
            owner_id=owner_id,
            extra_data={'driver_id': driver_id}
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/<int:reservation_id>/approve-extra-time', methods=['POST'])
def approve_extra_time(reservation_id):
    """API: aprobar tiempo extra"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        data = request.get_json() or {}
        extra_minutes = data.get('extra_minutes', 0)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''SELECT r.driver_id, r.duration_minutes, p.owner_id 
                       FROM reservations r 
                       JOIN parkings p ON r.parking_id = p.id 
                       WHERE r.id = ?''', (reservation_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404
        driver_id, current_duration, owner_id = row
        if owner_id != session['user_id']:
            conn.close()
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        cur.execute('SELECT name FROM users WHERE id = ?', (owner_id,))
        owner_row = cur.fetchone()
        owner_name = owner_row[0] if owner_row else 'Arrendador'
        new_duration = current_duration + extra_minutes
        cur.execute('UPDATE reservations SET duration_minutes = ? WHERE id = ?', (new_duration, reservation_id))
        conn.commit()
        conn.close()
        try:
            delete_notifications_for_reservation(reservation_id, types_to_remove=['extra_time_request'], user_id=owner_id)
        except Exception:
            pass
        try:
            conn2 = get_connection()
            cur2 = conn2.cursor()
            cur2.execute('SELECT occupied_since FROM parkings p JOIN reservations r ON p.id = r.parking_id WHERE r.id = ?', (reservation_id,))
            occ_row = cur2.fetchone()
            occupied_since = occ_row[0] if occ_row else None
            cur2.execute('SELECT p.name FROM parkings p JOIN reservations r ON p.id = r.parking_id WHERE r.id = ?', (reservation_id,))
            park_row = cur2.fetchone()
            parking_name = park_row[0] if park_row else 'el parqueadero'
            import json
            new_extra_data = json.dumps({
                'parking_name': parking_name,
                'duration_minutes': new_duration,
                'occupied_since': occupied_since
            })
            cur2.execute('UPDATE notifications SET extra_data = ? WHERE reservation_id = ? AND user_id = ? AND type = ?', 
                        (new_extra_data, reservation_id, driver_id, 'vehicle_parked'))
            conn2.commit()
            conn2.close()
        except Exception as e:
            print(f"Error actualizando notificación vehicle_parked: {e}")
        add_notification(
            user_id=driver_id,
            type='extra_time_approved',
            message=f'Se aprobaron {extra_minutes} minutos adicionales',
            reservation_id=reservation_id,
            extra_data={'extra_minutes': extra_minutes, 'owner_name': owner_name}
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/<int:reservation_id>/reject-extra-time', methods=['POST'])
def reject_extra_time(reservation_id):
    """API: rechazar tiempo extra"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''SELECT r.driver_id, p.owner_id 
                       FROM reservations r 
                       JOIN parkings p ON r.parking_id = p.id 
                       WHERE r.id = ?''', (reservation_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404
        driver_id, owner_id = row
        if owner_id != session['user_id']:
            conn.close()
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        cur.execute('SELECT name FROM users WHERE id = ?', (owner_id,))
        owner_row = cur.fetchone()
        owner_name = owner_row[0] if owner_row else 'Arrendador'
        cur.execute('UPDATE reservations SET penalty_active = 1 WHERE id = ?', (reservation_id,))
        conn.commit()
        conn.close()
        try:
            delete_notifications_for_reservation(reservation_id, types_to_remove=['extra_time_request'], user_id=owner_id)
        except Exception:
            pass
        add_notification(
            user_id=driver_id,
            type='extra_time_rejected',
            message='Tu solicitud de tiempo extra fue rechazada. Se aplicará multa de $500 cada 5 min al exceder tu tiempo.',
            reservation_id=reservation_id,
            extra_data={'owner_name': owner_name}
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/<int:reservation_id>/clear-vehicle-parked', methods=['POST'])
def clear_vehicle_parked(reservation_id):
    """API: arrendador confirma llegada"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''SELECT r.driver_id, p.owner_id 
                       FROM reservations r 
                       JOIN parkings p ON r.parking_id = p.id 
                       WHERE r.id = ?''', (reservation_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404
        driver_id, owner_id = row
        if owner_id != session['user_id']:
            conn.close()
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        conn.close()
        try:
            delete_notifications_for_reservation(reservation_id, types_to_remove=['vehicle_parked'], user_id=driver_id)
        except Exception as e:
            print(f"Error eliminando vehicle_parked: {e}")
        try:
            delete_notifications_for_reservation(reservation_id, types_to_remove=['at_vehicle'], user_id=owner_id)
        except Exception as e:
            print(f"Error eliminando at_vehicle: {e}")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/<int:reservation_id>/vehicle-not-arrived', methods=['POST'])
def vehicle_not_arrived(reservation_id):
    """API: conductor no ha llegado"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT owner_id FROM reservations WHERE id = ?', (reservation_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404
        if row[0] != session['user_id']:
            conn.close()
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        cur.execute('UPDATE notifications SET status = ? WHERE reservation_id = ? AND type = ?', 
                    ('read', reservation_id, 'at_vehicle'))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reservations/<int:reservation_id>', methods=['GET'])
def get_reservation_details(reservation_id):
    """API: obtener detalles de una reserva"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        reservation = get_reservation(reservation_id)
        if not reservation:
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT owner_id, occupied_since FROM parkings WHERE id = ?', (reservation['parking_id'],))
        parking = cursor.fetchone()
        conn.close()
        if not (reservation['driver_id'] == session['user_id'] or (parking and parking[0] == session['user_id'])):
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        if parking and len(parking) > 1:
            reservation['occupied_since'] = parking[1]
        return jsonify({
            'success': True,
            'reservation': reservation,
            'penalty_amount': reservation.get('penalty_amount', 0) or 0,
            'penalty_active': reservation.get('penalty_active', 0) or 0
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reservations_bp.route('/api/reviews/create', methods=['POST'])
def create_review():
    """API: crear una calificación y eliminar notificaciones de la reserva"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    
    try:
        data = request.get_json()
        reservation_id = data.get('reservation_id')
        target_user_id = data.get('target_user_id')
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        if not reservation_id or not target_user_id or not rating:
            return jsonify({'success': False, 'error': 'Faltan datos requeridos'}), 400
        
        # Validar que el rating sea entre 1 y 5
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'success': False, 'error': 'Rating debe ser entre 1 y 5'}), 400
        
        # Obtener la reserva para verificar permisos y obtener parking_id
        reservation = get_reservation(reservation_id)
        if not reservation:
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404
        
        # Verificar que el usuario es parte de la reserva
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT owner_id FROM parkings WHERE id = ?', (reservation['parking_id'],))
        parking = cursor.fetchone()
        conn.close()
        
        if not parking:
            return jsonify({'success': False, 'error': 'Parqueadero no encontrado'}), 404
        
        owner_id = parking[0]
        driver_id = reservation['driver_id']
        
        # Verificar que el usuario es conductor o arrendador de esta reserva
        if session['user_id'] not in [driver_id, owner_id]:
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        
        # Agregar review
        add_review(
            reviewer_id=session['user_id'],
            driver_id=target_user_id,
            parking_id=reservation['parking_id'],
            rating=rating,
            comment=comment
        )
        
        # Actualizar rating promedio del usuario
        update_user_rating(target_user_id)
        
        # Eliminar notificaciones de esta reserva
        delete_notifications_for_reservation(reservation_id)
        
        return jsonify({'success': True, 'message': 'Calificación guardada exitosamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
