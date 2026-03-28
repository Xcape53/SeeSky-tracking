"""
Glowna aplikacja Flask - SeeSky Tracking API.

Uruchamia serwer REST API z autentykacja JWT,
obsluga katalogu gwiazd, kolejki obserwacji,
trackingu i kalibracji.
"""

import sys
from pathlib import Path

# Dodaj katalog backend do PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask
from flask_cors import CORS

import config
from database.models import init_db
from api.routes import api_bp


def create_app():
    """Tworzy i konfiguruje aplikacje Flask."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY

    # CORS - pozwol frontendowi na komunikacje
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Inicjalizuj baze danych
    init_db()

    # Zarejestruj blueprint z endpointami API
    app.register_blueprint(api_bp, url_prefix="/api")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
