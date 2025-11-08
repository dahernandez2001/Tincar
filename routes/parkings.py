from flask import Blueprint, request, session, jsonify
import os
import time as _time
from werkzeug.utils import secure_filename

from models import (
    get_connection,
    add_parking,
    get_parking,
    update_parking,
    delete_parking,
    get_active_parkings,
    get_parkings_by_owner,
    add_reservation,
    add_notification
)
from utils.geocode import geocode_location

parkings_bp = Blueprint('parkings', __name__)


@parkings_bp.route('/parkings/create', methods=['POST'])
def create_parking():
    if 'user_id' not in session:
        return {'error': 'not authenticated'}, 401
    owner_id = session['user_id']
    form = request.form
    name = form.get('name') or form.get('garage_name')
    if not name or not name.strip():
        return jsonify({'success': False, 'error': 'El nombre del parqueadero es obligatorio.'}), 400
    phone = form.get('phone')
    email = form.get('email')
    address = form.get('address')
    department = form.get('department')
    city = form.get('city')
    housing_type = form.get('housing_type')
    size = form.get('size')
    features = form.get('features')
    image_path = None
    if 'image' in request.files:
        img = request.files.get('image')
        if img and img.filename:
            uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            filename = secure_filename(img.filename)
            unique_name = f"{int(_time.time())}_{filename}"
            save_path = os.path.join(uploads_dir, unique_name)
            img.save(save_path)
            image_path = f"/static/uploads/{unique_name}"

    try:
        latitude_raw = form.get('latitude') or None
        longitude_raw = form.get('longitude') or None
        try:
            latitude = float(latitude_raw) if latitude_raw not in (None, '', 'None') else None
        except Exception:
            latitude = None
        try:
            longitude = float(longitude_raw) if longitude_raw not in (None, '', 'None') else None
        except Exception:
            longitude = None
        if (latitude is None or longitude is None) and (department or city or address):
            g_lat, g_lon = geocode_location(department=department, city=city, address=address, country_hint=None)
            if g_lat is not None and g_lon is not None:
                if latitude is None:
                    latitude = g_lat
                if longitude is None:
                    longitude = g_lon
        parking = add_parking(owner_id=owner_id, name=name, phone=phone, email=email, address=address,
                              department=department, city=city, housing_type=housing_type, size=size,
                              features=features, image_path=image_path, latitude=latitude, longitude=longitude, active=1)
        if not parking:
            return jsonify({'success': False, 'error': 'No se pudo crear el parqueadero'}), 500
        try:
            full = get_parking(parking['id'])
        except Exception:
            full = None
        resp = {'success': True, 'parking': full or parking}
        if not full or full.get('latitude') is None or full.get('longitude') is None:
            resp['geocode_failed'] = True
            resp['message'] = 'No se pudieron obtener coordenadas desde la dirección; por favor añade latitud/longitud manualmente si es necesario.'
        return jsonify(resp)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@parkings_bp.route('/parkings/<int:parking_id>/active', methods=['POST'])
def set_parking_active(parking_id):
    if 'user_id' not in session:
        return {'error': 'not authenticated'}, 401
    data = request.get_json(silent=True) or {}
    if not data and request.form.get('active') is not None:
        val = request.form.get('active')
        data['active'] = val.lower() in ('1','true','yes','on')
    if 'active' not in data:
        return {'error': 'missing active'}, 400
    try:
        active_value = 1 if bool(data['active']) else 0
        conn = get_connection()
        cur = conn.cursor()
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


@parkings_bp.route('/parkings/<int:parking_id>', methods=['GET'])
def parking_detail(parking_id):
    if 'user_id' not in session:
        return jsonify({'error':'not authenticated'}), 401
    try:
        p = get_parking(parking_id)
        if not p:
            return jsonify({'error':'not found'}), 404
        if p['owner_id'] != session['user_id']:
            return jsonify({'error':'forbidden'}), 403
        return jsonify({'success': True, 'parking': p})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@parkings_bp.route('/parkings/<int:parking_id>/update', methods=['POST'])
def parking_update(parking_id):
    if 'user_id' not in session:
        return jsonify({'error':'not authenticated'}), 401
    form = request.form
    data = {}
    for key in ['name','phone','email','address','department','city','housing_type','size','features']:
        if key in form:
            data[key] = form.get(key)
    for key in ['latitude','longitude']:
        if key in form:
            raw = form.get(key)
            try:
                data[key] = float(raw) if raw not in (None, '', 'None') else None
            except ValueError:
                data[key] = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT owner_id FROM parkings WHERE id = ?', (parking_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return {'error': 'not found'}, 404
        if row[0] != session['user_id']:
            conn.close()
            return {'error': 'forbidden'}, 403
        set_clause = ', '.join(f"{k} = ?" for k in data.keys())
        cur.execute(f'UPDATE parkings SET {set_clause} WHERE id = ?', (*data.values(), parking_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@parkings_bp.route('/api/parkings/active', methods=['GET'])
def api_get_active_parkings():
    try:
        parkings = get_active_parkings()
        bbox = request.args.get('bbox')
        if bbox:
            try:
                parts = [float(x) for x in bbox.split(',')]
                if len(parts) == 4:
                    minLat, minLng, maxLat, maxLng = parts
                    def in_bbox(p):
                        try:
                            lat = float(p.get('latitude'))
                            lng = float(p.get('longitude'))
                        except Exception:
                            return False
                        return lat >= minLat and lat <= maxLat and lng >= minLng and lng <= maxLng
                    parkings = [p for p in parkings if in_bbox(p)]
            except Exception:
                pass
        result = [{
            'id': p['id'],
            'name': p['name'],
            'phone': p.get('phone'),
            'email': p.get('email'),
            'address': p.get('address'),
            'department': p.get('department'),
            'city': p.get('city'),
            'housing_type': p.get('housing_type'),
            'size': p.get('size'),
            'features': p.get('features'),
            'image_path': p.get('image_path'),
            'latitude': p.get('latitude'),
            'longitude': p.get('longitude'),
            'owner_id': p.get('owner_id'),
            'status': 'Libre'
        } for p in parkings]
        return jsonify({'success': True, 'parkings': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@parkings_bp.route('/api/parkings/<int:parking_id>/delete', methods=['POST'])
def api_delete_parking(parking_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    parking = get_parking(parking_id)
    if not parking:
        return jsonify({'success': False, 'error': 'Parqueadero no encontrado'}), 404
    if parking['owner_id'] != session['user_id']:
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    try:
        delete_parking(parking_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@parkings_bp.route('/api/parkings/<int:parking_id>', methods=['GET'])
def api_get_parking(parking_id):
    try:
        p = get_parking(parking_id)
        if not p:
            return jsonify({'success': False, 'error': 'Parqueadero no encontrado'}), 404
        return jsonify({
            'id': p['id'],
            'name': p['name'],
            'phone': p.get('phone'),
            'email': p.get('email'),
            'address': p.get('address'),
            'department': p.get('department'),
            'city': p.get('city'),
            'housing_type': p.get('housing_type'),
            'size': p.get('size'),
            'features': p.get('features'),
            'image_path': p.get('image_path'),
            'latitude': p.get('latitude'),
            'longitude': p.get('longitude'),
            'owner_id': p.get('owner_id'),
            'status': 'Libre'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@parkings_bp.route('/api/parkings/<int:parking_id>/reserve', methods=['POST'])
def api_reserve_parking(parking_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    data = request.get_json(silent=True) or {}
    required_fields = ['start_time', 'end_time']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'error': 'Faltan datos requeridos.'}), 400
    try:
        reservation_id = add_reservation(driver_id=session['user_id'], parking_id=parking_id,
                                        start_time=data['start_time'], end_time=data['end_time'])
        if not reservation_id:
            return jsonify({'success': False, 'error': 'No se pudo crear la reserva.'}), 500
        return jsonify({'success': True, 'reservation_id': reservation_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@parkings_bp.route('/api/parkings/nearby', methods=['GET'])
def api_get_nearby_parkings():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    radius = request.args.get('radius', default=500, type=int)
    if not lat or not lon:
        return jsonify({'success': False, 'error': 'Faltan latitud y/o longitud.'}), 400
    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        return jsonify({'success': False, 'error': 'Latitud y longitud deben ser números.'}), 400
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, address, latitude, longitude, owner_id
            FROM parkings
            WHERE active = 1 AND latitude IS NOT NULL AND longitude IS NOT NULL
            AND (6371000 * acos(
                cos(radians(?)) * cos(radians(latitude)) *
                cos(radians(longitude) - radians(?)) +
                sin(radians(?)) * sin(radians(latitude))
            )) <= ?
        ''', (lat, lon, lat, radius))
        parkings = cursor.fetchall()
        conn.close()
        return jsonify([{
            'id': p['id'],
            'name': p['name'],
            'address': p['address'],
            'latitude': p['latitude'],
            'longitude': p['longitude'],
            'owner_id': p['owner_id'],
            'status': 'Libre'
        } for p in parkings])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@parkings_bp.route('/api/owner/parkings', methods=['GET'])
def api_owner_parkings():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        parkings = get_parkings_by_owner(session['user_id'])
        return jsonify({'success': True, 'parkings': parkings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
