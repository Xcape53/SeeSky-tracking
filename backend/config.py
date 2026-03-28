"""
Centralna konfiguracja aplikacji SeeSky.

Zawiera domyslne wartosci dla lokalizacji obserwatorium,
interwalow petli trackingowej, sciezek do bazy danych
i portow serwerowych. Wartosci moga byc nadpisane
przez zmienne srodowiskowe.
"""

import os
from pathlib import Path


# Sciezki
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = str(BASE_DIR / "database" / "star_catalog.db")

# Serwer Flask
FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

# JWT
SECRET_KEY = os.environ.get("SECRET_KEY", "seesky-dev-secret-change-in-production")
JWT_EXPIRATION_SECONDS = 3600

# Domyslne konto operatora
DEFAULT_USERNAME = os.environ.get("SEESKY_USER", "operator")
DEFAULT_PASSWORD = os.environ.get("SEESKY_PASS", "seesky123")

# Domyslna lokalizacja obserwatora: Wroclaw, Polska
DEFAULT_LATITUDE = 51.1079
DEFAULT_LONGITUDE = 17.0385
DEFAULT_ALTITUDE = 120.0  # metry n.p.m.

# Parametry trackingu
TRACKING_INTERVAL_SECONDS = 2.0
DEFAULT_OBSERVATION_DURATION_MINUTES = 30

# Parametry atmosferyczne (korekcja refrakcji)
DEFAULT_PRESSURE = 1013.25      # hPa
DEFAULT_TEMPERATURE = 10.0      # Celsius
DEFAULT_HUMIDITY = 0.5          # 0-1
DEFAULT_WAVELENGTH = 210000.0   # nm (~21cm linia wodoru HI)
