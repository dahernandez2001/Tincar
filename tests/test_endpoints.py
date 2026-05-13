"""
Tests básicos para verificar endpoints de la aplicación Tincar.
Valida que los endpoints públicos respondan 200 y los protegidos requieran autenticación.
"""
import pytest
from app import app, socketio


@pytest.fixture
def client():
    """Cliente de prueba de Flask con contexto de aplicación."""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_client(client):
    """Cliente de prueba con sesión de conductor autenticado."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['user_name'] = 'Test Driver'
        sess['name'] = 'Test Driver'
        sess['email'] = 'driver@test.com'
        sess['role'] = 'conductor'
    return client


@pytest.fixture
def authenticated_landlord(client):
    """Cliente de prueba con sesión de arrendador autenticado."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['user_name'] = 'Test Landlord'
        sess['name'] = 'Test Landlord'
        sess['email'] = 'landlord@test.com'
        sess['role'] = 'arrendador'
    return client


# ============= Tests de importación y configuración =============

def test_app_imports():
    """Verifica que la aplicación se importe correctamente."""
    assert app is not None
    assert app.name == 'app'


def test_blueprints_registered():
    """Verifica que todos los blueprints estén registrados."""
    blueprints = list(app.blueprints.keys())
    assert 'auth' in blueprints
    assert 'driver' in blueprints
    assert 'parkings' in blueprints
    assert 'reservations' in blueprints
    assert 'notifications' in blueprints


# ============= Tests de endpoints públicos =============

def test_home_page(client):
    """La página de inicio debe ser accesible públicamente."""
    response = client.get('/')
    assert response.status_code == 200


def test_servicios_page(client):
    """La página de servicios debe ser accesible públicamente."""
    response = client.get('/servicios')
    assert response.status_code == 200


def test_login_page(client):
    """La página de login debe ser accesible públicamente."""
    response = client.get('/login')
    assert response.status_code == 200


def test_register_page(client):
    """La página de registro debe ser accesible públicamente."""
    response = client.get('/register')
    assert response.status_code == 200


# ============= Tests de endpoints protegidos (sin autenticación) =============

def test_dashboard_requires_auth(client):
    """El dashboard debe redirigir a login sin autenticación."""
    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code in [302, 401]


def test_profile_requires_auth(client):
    """El perfil debe requerir autenticación."""
    response = client.get('/profile', follow_redirects=False)
    assert response.status_code in [302, 401]


def test_driver_index_requires_auth(client):
    """El índice de conductor debe requerir autenticación."""
    response = client.get('/driver', follow_redirects=False)
    assert response.status_code in [302, 401]


def test_driver_profile_requires_auth(client):
    """El perfil de conductor debe requerir autenticación."""
    response = client.get('/driver/profile', follow_redirects=False)
    assert response.status_code in [302, 401]


def test_landlord_dashboard_requires_auth(client):
    """El dashboard de arrendador debe requerir autenticación."""
    response = client.get('/landlord', follow_redirects=False)
    assert response.status_code in [302, 401]


# ============= Tests de APIs protegidas (sin autenticación) =============

def test_api_driver_profile_requires_auth(client):
    """API de perfil de conductor debe requerir autenticación."""
    response = client.get('/api/driver/profile/1')
    # Debe denegar acceso (401 Unauthorized o 403 Forbidden)
    assert response.status_code in [401, 403]


def test_api_reservations_requires_auth(client):
    """API de crear reserva debe requerir autenticación."""
    response = client.post('/api/reservations', json={'parking_id': 1, 'duration_minutes': 10})
    assert response.status_code == 401
    data = response.get_json()
    assert data['success'] is False


def test_api_notifications_requires_auth(client):
    """API de notificaciones debe requerir autenticación."""
    response = client.get('/api/notifications')
    assert response.status_code == 401
    data = response.get_json()
    assert data['success'] is False


# ============= Tests con autenticación (conductor) =============

def test_driver_index_with_auth(authenticated_client):
    """El índice de conductor debe ser accesible con autenticación."""
    response = authenticated_client.get('/driver')
    assert response.status_code == 200


def test_driver_profile_with_auth(authenticated_client):
    """El perfil de conductor debe ser accesible con autenticación."""
    response = authenticated_client.get('/driver/profile', follow_redirects=True)
    # Puede devolver 200 o redirigir si no hay perfil en DB (302)
    assert response.status_code in [200, 302]


def test_dashboard_with_auth(authenticated_client):
    """El dashboard debe ser accesible con autenticación."""
    response = authenticated_client.get('/dashboard')
    # Puede redirigir si no hay datos en DB, o mostrar página
    assert response.status_code in [200, 302]


def test_api_notifications_with_auth(authenticated_client):
    """API de notificaciones debe funcionar con autenticación."""
    response = authenticated_client.get('/api/notifications')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert 'notifications' in data


# ============= Tests con autenticación (arrendador) =============

def test_landlord_dashboard_with_auth(authenticated_landlord):
    """El dashboard de arrendador debe ser accesible con autenticación."""
    response = authenticated_landlord.get('/landlord')
    # Puede redirigir si no hay datos en DB, o mostrar página
    assert response.status_code in [200, 302]


def test_api_owner_parkings_with_auth(authenticated_landlord):
    """API de parqueaderos del owner debe funcionar con autenticación."""
    response = authenticated_landlord.get('/api/owner/parkings')
    assert response.status_code == 200
    data = response.get_json()
    assert 'parkings' in data


# ============= Tests de rutas que no existen =============

def test_nonexistent_route(client):
    """Rutas inexistentes deben devolver 404."""
    response = client.get('/ruta-que-no-existe')
    assert response.status_code == 404


# ============= Tests de métodos HTTP incorrectos =============

def test_get_on_post_only_endpoint(client):
    """GET en endpoint POST-only debe devolver 405."""
    response = client.get('/api/reservations')
    # Puede devolver 401 si requiere auth antes de validar método
    assert response.status_code in [401, 405]
