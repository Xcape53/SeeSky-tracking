"""
Warstwa dostepu do bazy danych SQLite.

Zapewnia funkcje do odczytu katalogu gwiazd, zarzadzania kolejka
obserwacji i przechowywania konfiguracji teleskopu.
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

import config


def get_db() -> sqlite3.Connection:
    """Zwraca polaczenie do bazy danych z row_factory."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Tworzy dodatkowe tabele (konfiguracja, kolejka) jesli nie istnieja."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS telescope_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            latitude REAL NOT NULL DEFAULT 51.1079,
            longitude REAL NOT NULL DEFAULT 17.0385,
            altitude REAL NOT NULL DEFAULT 120.0,
            tracking_interval_seconds REAL NOT NULL DEFAULT 2.0,
            default_observation_duration_minutes INTEGER NOT NULL DEFAULT 30,
            pressure REAL NOT NULL DEFAULT 1013.25,
            temperature REAL NOT NULL DEFAULT 10.0,
            humidity REAL NOT NULL DEFAULT 0.5,
            wavelength REAL NOT NULL DEFAULT 210000.0,
            calibration_offset_az REAL NOT NULL DEFAULT 0.0,
            calibration_offset_alt REAL NOT NULL DEFAULT 0.0,
            is_calibrated INTEGER NOT NULL DEFAULT 0,
            last_calibration_time TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            star_id INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 30,
            priority INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'waiting',
            position_in_queue INTEGER,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            FOREIGN KEY (star_id) REFERENCES stars(id)
        )
    """)

    # Wstaw domyslna konfiguracje jesli nie istnieje
    cur.execute("SELECT COUNT(*) FROM telescope_config")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO telescope_config (id, latitude, longitude, altitude)
            VALUES (1, ?, ?, ?)
        """, (config.DEFAULT_LATITUDE, config.DEFAULT_LONGITUDE, config.DEFAULT_ALTITUDE))

    conn.commit()
    conn.close()


# --- Konfiguracja teleskopu ---

def get_config() -> dict:
    """Pobiera konfiguracje teleskopu."""
    conn = get_db()
    row = conn.execute("SELECT * FROM telescope_config WHERE id = 1").fetchone()
    conn.close()
    if row is None:
        return {}
    return dict(row)


def update_config(data: dict) -> dict:
    """Aktualizuje konfiguracje teleskopu. Zwraca zaktualizowana konfiguracje."""
    allowed = [
        "latitude", "longitude", "altitude",
        "tracking_interval_seconds", "default_observation_duration_minutes",
        "pressure", "temperature", "humidity", "wavelength",
    ]
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return get_config()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values())

    conn = get_db()
    conn.execute(f"UPDATE telescope_config SET {set_clause} WHERE id = 1", values)
    conn.commit()
    conn.close()
    return get_config()


# --- Katalog gwiazd ---

def get_stars(page=1, per_page=20, search=None, min_mag=None, max_mag=None, constellation=None) -> dict:
    """Pobiera liste gwiazd z filtrowaniem i paginacja."""
    conn = get_db()

    where_clauses = []
    params = []

    if search:
        where_clauses.append("proper_name LIKE ?")
        params.append(f"%{search}%")
    if min_mag is not None:
        where_clauses.append("magnitude >= ?")
        params.append(min_mag)
    if max_mag is not None:
        where_clauses.append("magnitude <= ?")
        params.append(max_mag)
    if constellation:
        where_clauses.append("constellation = ?")
        params.append(constellation)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Policz total
    count_row = conn.execute(
        f"SELECT COUNT(*) FROM stars WHERE {where_sql}", params
    ).fetchone()
    total = count_row[0]

    # Pobierz strone
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""SELECT id, hyg_id, proper_name, ra, dec, magnitude,
                   spectral_type, constellation, distance_ly
            FROM stars WHERE {where_sql}
            ORDER BY CASE WHEN proper_name IS NOT NULL THEN 0 ELSE 1 END, magnitude
            LIMIT ? OFFSET ?""",
        params + [per_page, offset],
    ).fetchall()

    conn.close()

    stars = []
    for r in rows:
        stars.append({
            "id": r["id"],
            "name": r["proper_name"],
            "constellation": r["constellation"],
            "magnitude": r["magnitude"],
            "ra": r["ra"],
            "dec": r["dec"],
            "spectral_type": r["spectral_type"],
            "distance_ly": r["distance_ly"],
        })

    return {
        "stars": stars,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        },
    }


def get_star(star_id: int) -> dict | None:
    """Pobiera szczegoly gwiazdy po ID."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM stars WHERE id = ?", (star_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


# --- Kolejka obserwacji ---

def get_queue() -> list[dict]:
    """Pobiera kolejke obserwacji (status waiting), posortowana wg priorytetu."""
    conn = get_db()
    rows = conn.execute("""
        SELECT o.*, s.proper_name as star_name
        FROM observations o
        LEFT JOIN stars s ON o.star_id = s.id
        WHERE o.status = 'waiting'
        ORDER BY o.priority DESC, o.created_at ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_observation(star_id: int, duration_minutes: int = 30, priority: int = 0) -> dict:
    """Dodaje obserwacje do kolejki."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO observations (star_id, duration_minutes, priority, status, created_at)
           VALUES (?, ?, ?, 'waiting', ?)""",
        (star_id, duration_minutes, priority, now),
    )
    obs_id = cur.lastrowid
    conn.commit()

    row = conn.execute("""
        SELECT o.*, s.proper_name as star_name
        FROM observations o
        LEFT JOIN stars s ON o.star_id = s.id
        WHERE o.id = ?
    """, (obs_id,)).fetchone()
    conn.close()
    return dict(row)


def delete_observation(obs_id: int) -> bool:
    """Usuwa obserwacje z kolejki (tylko waiting)."""
    conn = get_db()
    row = conn.execute("SELECT status FROM observations WHERE id = ?", (obs_id,)).fetchone()
    if row is None:
        conn.close()
        return False
    if row["status"] != "waiting":
        conn.close()
        raise ValueError("Nie mozna usunac obserwacji, ktora nie jest w stanie waiting")

    conn.execute("DELETE FROM observations WHERE id = ?", (obs_id,))
    conn.commit()
    conn.close()
    return True


def update_observation(obs_id: int, data: dict) -> dict | None:
    """Aktualizuje parametry obserwacji (tylko waiting)."""
    conn = get_db()
    row = conn.execute("SELECT status FROM observations WHERE id = ?", (obs_id,)).fetchone()
    if row is None:
        conn.close()
        return None
    if row["status"] != "waiting":
        conn.close()
        raise ValueError("Nie mozna modyfikowac obserwacji, ktora nie jest w stanie waiting")

    allowed = ["duration_minutes", "priority"]
    updates = {k: v for k, v in data.items() if k in allowed}
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values())
        conn.execute(f"UPDATE observations SET {set_clause} WHERE id = ?", values + [obs_id])
        conn.commit()

    row = conn.execute("""
        SELECT o.*, s.proper_name as star_name
        FROM observations o
        LEFT JOIN stars s ON o.star_id = s.id
        WHERE o.id = ?
    """, (obs_id,)).fetchone()
    conn.close()
    return dict(row)


def get_next_observation() -> dict | None:
    """Pobiera nastepna obserwacje z kolejki (najwyzszy priorytet)."""
    conn = get_db()
    row = conn.execute("""
        SELECT o.*, s.proper_name as star_name, s.ra, s.dec
        FROM observations o
        LEFT JOIN stars s ON o.star_id = s.id
        WHERE o.status = 'waiting'
        ORDER BY o.priority DESC, o.created_at ASC
        LIMIT 1
    """).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def update_observation_status(obs_id: int, status: str):
    """Zmienia status obserwacji."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()

    if status == "tracking":
        conn.execute(
            "UPDATE observations SET status = ?, started_at = ? WHERE id = ?",
            (status, now, obs_id),
        )
    elif status in ("completed", "stopped"):
        conn.execute(
            "UPDATE observations SET status = ?, finished_at = ? WHERE id = ?",
            (status, now, obs_id),
        )
    else:
        conn.execute(
            "UPDATE observations SET status = ? WHERE id = ?",
            (status, obs_id),
        )
    conn.commit()
    conn.close()


# --- Kalibracja ---

def update_calibration(offset_az: float, offset_alt: float):
    """Zapisuje offsety kalibracyjne."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.execute("""
        UPDATE telescope_config
        SET calibration_offset_az = ?, calibration_offset_alt = ?,
            is_calibrated = 1, last_calibration_time = ?
        WHERE id = 1
    """, (offset_az, offset_alt, now))
    conn.commit()
    conn.close()


def reset_calibration():
    """Resetuje kalibracje."""
    conn = get_db()
    conn.execute("""
        UPDATE telescope_config
        SET calibration_offset_az = 0, calibration_offset_alt = 0,
            is_calibrated = 0, last_calibration_time = NULL
        WHERE id = 1
    """)
    conn.commit()
    conn.close()
