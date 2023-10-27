# 3rd parth dependencies
from flask import Flask
from routes import blueprint
import datetime
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required


def create_app():
    app = Flask(__name__)
    app.register_blueprint(blueprint)
    # Atur secret key untuk JWT (harus aman dan rahasia)
    app.config['JWT_SECRET_KEY'] = 'da02be53335e4e719ae0f46c55084881'
    # Atur waktu kedaluwarsa token menjadi 3 menit
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(minutes=10)

    # Inisialisasi Flask-JWT-Extended
    jwt = JWTManager(app)
    return app
