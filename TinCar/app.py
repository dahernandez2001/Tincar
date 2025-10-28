from flask import Flask
from app.routes.auth import bp as auth_bp
from app.models import db
from app.config import Config

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    db.init_app(app)

    # Registrar blueprint de autenticación
    app.register_blueprint(auth_bp)

    @app.route('/')
    def index():
        return "Bienvenido a TinCar (inicio provisional)"

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
