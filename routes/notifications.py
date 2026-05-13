"""
Blueprint para manejar todas las rutas y APIs relacionadas con notificaciones.
Extraído de app.py para mejor organización y mantenibilidad.
"""
from flask import Blueprint, request, session, jsonify
from models import get_connection, get_notifications_by_user

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/api/notifications', methods=['GET'])
def get_notifications():
    """API: obtener todas las notificaciones del usuario"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        notifications = get_notifications_by_user(session['user_id'])
        return jsonify({'success': True, 'notifications': notifications})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@notifications_bp.route('/api/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    """API: marcar notificaciones como leídas"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        data = request.get_json() or {}
        notification_ids = data.get('notification_ids', [])
        if not notification_ids:
            return jsonify({'success': False, 'error': 'No se proporcionaron IDs'}), 400
        conn = get_connection()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(notification_ids))
        cursor.execute(f'UPDATE notifications SET status = ? WHERE id IN ({placeholders}) AND user_id = ?',
                      ['read'] + notification_ids + [session['user_id']])
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@notifications_bp.route('/api/notifications/clear', methods=['POST'])
def clear_notifications():
    """API: eliminar todas las notificaciones del usuario"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'not authenticated'}), 401
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM notifications WHERE user_id = ?', (session['user_id'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
