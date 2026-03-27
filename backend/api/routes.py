"""
Endpointy REST API SeeSky.

Obejmuje: autentykacje (JWT), konfiguracje teleskopu,
katalog gwiazd, kolejke obserwacji, tracking i kalibracje.
"""

import functools
import time
from datetime import datetime, timezone, timedelta

import jwt
from flask import Blueprint, request, jsonify, current_app

import config
from database.models import (
    get_config, update_config,
    get_stars, get_star,
    get_queue, add_observation, delete_observation,
    update_observation, get_next_observation,
    update_observation_status,
    update_calibration, reset_calibration,
)
from tracking.position import calculate_alt_az, get_current_position
from tracking.tracker import tracking_loop

api_bp = Blueprint("api", __name__)

# --- Zbior uniewaznionych tokenow (in-memory, resetuje sie po restarcie) ---
_revoked_tokens: set[str] = set()


# --- Dekorator autoryzacji JWT ---

def token_required(f):
    """Dekorator wymagajacy poprawnego tokena JWT."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "TOKEN_MISSING", "message": "Brak naglowka Authorization"}), 401

        token = auth_header[7:]
        if token in _revoked_tokens:
            return jsonify({"error": "TOKEN_EXPIRED", "message": "Token zostal uniewaziony"}), 401

        try:
            payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "TOKEN_EXPIRED", "message": "Token JWT wygasl"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "TOKEN_MISSING", "message": "Nieprawidlowy token JWT"}), 401

        return f(*args, **kwargs)
    return decorated


# ==================== AUTENTYKACJA ====================

@api_bp.route("/auth/login", methods=["POST"])
def login():
    """Logowanie i wydanie tokena JWT."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "BAD_REQUEST", "message": "Brak danych JSON"}), 400

    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "BAD_REQUEST", "message": "Pola 'username' i 'password' sa wymagane"}), 400

    if username != config.DEFAULT_USERNAME or password != config.DEFAULT_PASSWORD:
        return jsonify({"error": "INVALID_CREDENTIALS", "message": "Nieprawidlowa nazwa uzytkownika lub haslo"}), 401

    payload = {
        "sub": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=config.JWT_EXPIRATION_SECONDS),
    }
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")

    return jsonify({
        "token": token,
        "expires_in": config.JWT_EXPIRATION_SECONDS,
        "user": {"id": 1, "username": username},
    }), 200


@api_bp.route("/auth/logout", methods=["POST"])
@token_required
def logout():
    """Wylogowanie - uniewaznij token."""
    token = request.headers.get("Authorization", "")[7:]
    _revoked_tokens.add(token)
    return jsonify({"message": "Wylogowano pomyslnie"}), 200


# ==================== KONFIGURACJA TELESKOPU ====================

@api_bp.route("/config", methods=["GET"])
@token_required
def get_telescope_config():
    """Pobierz konfiguracje teleskopu."""
    cfg = get_config()
    return jsonify(cfg), 200


@api_bp.route("/config", methods=["PUT"])
@token_required
def update_telescope_config():
    """Zaktualizuj konfiguracje teleskopu."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "BAD_REQUEST", "message": "Brak danych JSON"}), 400

    # Walidacja zakresow
    if "latitude" in data and not (-90 <= data["latitude"] <= 90):
        return jsonify({"error": "VALIDATION_ERROR", "message": "Latitude musi byc w zakresie [-90, 90]"}), 400
    if "longitude" in data and not (-180 <= data["longitude"] <= 180):
        return jsonify({"error": "VALIDATION_ERROR", "message": "Longitude musi byc w zakresie [-180, 180]"}), 400
    if "tracking_interval_seconds" in data and data["tracking_interval_seconds"] <= 0:
        return jsonify({"error": "VALIDATION_ERROR", "message": "Interwal musi byc wiekszy od 0"}), 400

    cfg = update_config(data)
    return jsonify({"message": "Konfiguracja zaktualizowana pomyslnie", "config": cfg}), 200


# ==================== KATALOG GWIAZD ====================

@api_bp.route("/stars", methods=["GET"])
@token_required
def list_stars():
    """Pobierz liste gwiazd z filtrowaniem i paginacja."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search")
    min_mag = request.args.get("min_magnitude", type=float)
    max_mag = request.args.get("max_magnitude", type=float)
    constellation = request.args.get("constellation")

    if page < 1:
        return jsonify({"error": "BAD_REQUEST", "message": "Numer strony musi byc >= 1"}), 400
    if per_page < 1 or per_page > 100:
        return jsonify({"error": "BAD_REQUEST", "message": "per_page musi byc w zakresie [1, 100]"}), 400

    result = get_stars(
        page=page, per_page=per_page,
        search=search, min_mag=min_mag, max_mag=max_mag,
        constellation=constellation,
    )
    return jsonify(result), 200


@api_bp.route("/stars/<int:star_id>", methods=["GET"])
@token_required
def get_star_detail(star_id):
    """Pobierz szczegoly gwiazdy."""
    star = get_star(star_id)
    if star is None:
        return jsonify({"error": "NOT_FOUND", "message": f"Gwiazda o id {star_id} nie istnieje"}), 404
    return jsonify(star), 200


@api_bp.route("/stars/<int:star_id>/position", methods=["GET"])
@token_required
def get_star_position(star_id):
    """Oblicz aktualna pozycje gwiazdy na niebie."""
    star = get_star(star_id)
    if star is None:
        return jsonify({"error": "NOT_FOUND", "message": f"Gwiazda o id {star_id} nie istnieje"}), 404

    cfg = get_config()
    if not cfg:
        return jsonify({"error": "INTERNAL_ERROR", "message": "Brak konfiguracji teleskopu"}), 500

    pos = get_current_position(star, cfg)
    pos["star_id"] = star_id
    pos["star_name"] = star.get("proper_name")
    return jsonify(pos), 200


# ==================== KOLEJKA OBSERWACJI ====================

@api_bp.route("/queue", methods=["GET"])
@token_required
def list_queue():
    """Pobierz kolejke obserwacji."""
    queue = get_queue()
    return jsonify({"queue": queue, "total": len(queue)}), 200


@api_bp.route("/queue", methods=["POST"])
@token_required
def add_to_queue():
    """Dodaj obserwacje do kolejki."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "BAD_REQUEST", "message": "Brak danych JSON"}), 400

    star_id = data.get("star_id")
    if star_id is None:
        return jsonify({"error": "BAD_REQUEST", "message": "Pole 'star_id' jest wymagane"}), 400

    # Sprawdz czy gwiazda istnieje
    star = get_star(star_id)
    if star is None:
        return jsonify({"error": "NOT_FOUND", "message": f"Gwiazda o id {star_id} nie istnieje"}), 404

    duration = data.get("duration_minutes", 30)
    priority = data.get("priority", 0)

    obs = add_observation(star_id, duration_minutes=duration, priority=priority)
    return jsonify({"message": "Obserwacja dodana do kolejki", "observation": obs}), 201


@api_bp.route("/queue/<int:obs_id>", methods=["DELETE"])
@token_required
def remove_from_queue(obs_id):
    """Usun obserwacje z kolejki."""
    try:
        deleted = delete_observation(obs_id)
    except ValueError as e:
        return jsonify({"error": "BAD_REQUEST", "message": str(e)}), 400

    if not deleted:
        return jsonify({"error": "NOT_FOUND", "message": f"Obserwacja o id {obs_id} nie istnieje"}), 404

    return jsonify({"message": "Obserwacja usunieta z kolejki", "deleted_id": obs_id}), 200


@api_bp.route("/queue/<int:obs_id>", methods=["PUT"])
@token_required
def update_queue_item(obs_id):
    """Zaktualizuj parametry obserwacji."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "BAD_REQUEST", "message": "Brak danych JSON"}), 400

    try:
        obs = update_observation(obs_id, data)
    except ValueError as e:
        return jsonify({"error": "BAD_REQUEST", "message": str(e)}), 400

    if obs is None:
        return jsonify({"error": "NOT_FOUND", "message": f"Obserwacja o id {obs_id} nie istnieje"}), 404

    return jsonify({"message": "Obserwacja zaktualizowana", "observation": obs}), 200


# ==================== TRACKING ====================

@api_bp.route("/tracking/status", methods=["GET"])
@token_required
def tracking_status():
    """Pobierz aktualny status trackingu."""
    status = tracking_loop.get_status()
    return jsonify(status), 200


@api_bp.route("/tracking/start", methods=["POST"])
@token_required
def tracking_start():
    """Rozpocznij tracking nastepnej obserwacji z kolejki."""
    if tracking_loop.is_tracking:
        return jsonify({"error": "TRACKING_ACTIVE", "message": "Tracking jest juz aktywny"}), 400

    obs = get_next_observation()
    if obs is None:
        return jsonify({"error": "QUEUE_EMPTY", "message": "Kolejka obserwacji jest pusta"}), 400

    cfg = get_config()
    if not cfg:
        return jsonify({"error": "INTERNAL_ERROR", "message": "Brak konfiguracji teleskopu"}), 500

    # Sprawdz czy gwiazda jest nad horyzontem
    pos = get_current_position({"ra": obs["ra"], "dec": obs["dec"]}, cfg)
    if not pos["is_above_horizon"]:
        return jsonify({
            "error": "STAR_BELOW_HORIZON",
            "message": f"Gwiazda {obs.get('star_name', obs['star_id'])} jest pod horyzontem (alt={pos['alt']})",
        }), 400

    # Ustaw status na tracking
    update_observation_status(obs["id"], "tracking")

    # Uruchom petle trackingowa
    tracking_loop.start(observation=obs, cfg=cfg)

    return jsonify({
        "message": "Tracking rozpoczety",
        "observation": {
            "id": obs["id"],
            "star_id": obs["star_id"],
            "star_name": obs.get("star_name"),
            "duration_minutes": obs["duration_minutes"],
            "target_alt": round(pos["alt"], 4),
            "target_az": round(pos["az"], 4),
        },
    }), 200


@api_bp.route("/tracking/stop", methods=["POST"])
@token_required
def tracking_stop():
    """Zatrzymaj tracking."""
    if not tracking_loop.is_tracking:
        return jsonify({"error": "TRACKING_INACTIVE", "message": "Tracking nie jest aktywny"}), 400

    obs = tracking_loop.observation
    result = tracking_loop.stop()

    # Ustaw status obserwacji na stopped
    if result.get("observation_id"):
        update_observation_status(result["observation_id"], "stopped")

    return jsonify({
        "message": "Tracking zatrzymany",
        "observation": {
            "id": result.get("observation_id"),
            "star_name": obs.get("star_name") if obs else None,
            "elapsed_time": result.get("elapsed_time"),
            "status": "stopped",
        },
    }), 200


@api_bp.route("/tracking/pause", methods=["POST"])
@token_required
def tracking_pause():
    """Wstrzymaj tracking."""
    if not tracking_loop.is_tracking:
        return jsonify({"error": "TRACKING_INACTIVE", "message": "Tracking nie jest aktywny"}), 400

    try:
        tracking_loop.pause()
    except RuntimeError as e:
        return jsonify({"error": "BAD_REQUEST", "message": str(e)}), 400

    status = tracking_loop.get_status()
    return jsonify({
        "message": "Tracking wstrzymany",
        "observation": {
            "id": status["current_star"]["id"] if status["current_star"] else None,
            "star_name": status["current_star"]["name"] if status["current_star"] else None,
            "elapsed_time": status["elapsed_time"],
            "remaining_time": status["remaining_time"],
            "status": "paused",
        },
    }), 200


@api_bp.route("/tracking/resume", methods=["POST"])
@token_required
def tracking_resume():
    """Wznow tracking."""
    if not tracking_loop.is_tracking:
        return jsonify({"error": "TRACKING_INACTIVE", "message": "Tracking nie jest aktywny"}), 400

    try:
        tracking_loop.resume()
    except RuntimeError as e:
        return jsonify({"error": "BAD_REQUEST", "message": str(e)}), 400

    status = tracking_loop.get_status()
    return jsonify({
        "message": "Tracking wznowiony",
        "status": status,
    }), 200


# ==================== KALIBRACJA ====================

@api_bp.route("/calibration/status", methods=["GET"])
@token_required
def calibration_status():
    """Pobierz status kalibracji."""
    cfg = get_config()
    return jsonify({
        "is_calibrated": bool(cfg.get("is_calibrated")),
        "last_calibration_time": cfg.get("last_calibration_time"),
        "offset_az": cfg.get("calibration_offset_az", 0.0),
        "offset_alt": cfg.get("calibration_offset_alt", 0.0),
    }), 200


@api_bp.route("/calibration/reset", methods=["POST"])
@token_required
def calibration_reset():
    """Resetuj kalibracje."""
    if tracking_loop.is_tracking:
        return jsonify({"error": "TRACKING_ACTIVE", "message": "Nie mozna zresetowac podczas aktywnego trackingu"}), 400

    reset_calibration()
    return jsonify({
        "message": "Teleskop zresetowany do pozycji (0, 0)",
        "position": {"alt": 0.0, "az": 0.0},
    }), 200


@api_bp.route("/calibration/polaris", methods=["POST"])
@token_required
def calibration_polaris():
    """Kalibracja na Polaris."""
    if tracking_loop.is_tracking:
        return jsonify({"error": "TRACKING_ACTIVE", "message": "Nie mozna kalibrowac podczas aktywnego trackingu"}), 400

    cfg = get_config()

    # Polaris: RA=37.9546 deg, Dec=89.2641 deg (J2000)
    polaris_ra = 37.9546
    polaris_dec = 89.2641

    pos = get_current_position({"ra": polaris_ra, "dec": polaris_dec}, cfg)
    if not pos["is_above_horizon"]:
        return jsonify({
            "error": "STAR_BELOW_HORIZON",
            "message": "Polaris jest pod horyzontem - kalibracja niemozliwa",
        }), 400

    # Teoretyczna pozycja Polaris (bez kalibracji) - oblicz bez offsetow
    alt_true, az_true = calculate_alt_az(
        ra=polaris_ra, dec=polaris_dec,
        lat=cfg["latitude"], lon=cfg["longitude"], alt=cfg["altitude"],
        pressure=cfg.get("pressure", 1013.25),
        temperature=cfg.get("temperature", 10.0),
        humidity=cfg.get("humidity", 0.5),
        wavelength=cfg.get("wavelength", 210000.0),
    )

    # Znana pozycja Polaris: azymut ~0 (polnoc), elewacja ~= szerokosc geo
    # Offset = roznica miedzy pozycja obliczona a rzeczywista
    # W praktyce uzytkownik powinien wcelowac recznie, ale tu symulujemy
    # ze teleskop wskazuje (0, latitude) i obliczamy offsety
    expected_alt = cfg["latitude"]
    expected_az = 0.0

    offset_az = expected_az - az_true
    offset_alt = expected_alt - alt_true

    update_calibration(offset_az, offset_alt)
    cfg = get_config()

    return jsonify({
        "message": "Kalibracja na Gwiazde Polnocna zakonczona pomyslnie",
        "calibration": {
            "is_calibrated": True,
            "last_calibration_time": cfg.get("last_calibration_time"),
            "offset_az": round(offset_az, 4),
            "offset_alt": round(offset_alt, 4),
        },
    }), 200
