"""
Modul obliczen astronomicznych.

Transformacja wspolrzednych rownokowych (RA/Dec) na horyzontalne (Alt/Az)
z uwzglednieniem lokalizacji obserwatora, czasu i refrakcji atmosferycznej.
"""

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u
import numpy as np


def calculate_alt_az(
    ra: float,
    dec: float,
    lat: float,
    lon: float,
    alt: float,
    obs_time: Time | None = None,
    pressure: float = 1013.25,
    temperature: float = 10.0,
    humidity: float = 0.5,
    wavelength: float = 210000.0,
) -> tuple[float, float]:
    """
    Oblicza wspolrzedne horyzontalne (Alt/Az) z korekcja refrakcji.

    Args:
        ra: Rektascensja w stopniach (0-360).
        dec: Deklinacja w stopniach (-90 do +90).
        lat: Szerokosc geograficzna obserwatora.
        lon: Dlugosc geograficzna obserwatora.
        alt: Wysokosc n.p.m. obserwatora w metrach.
        obs_time: Czas obserwacji (domyslnie: teraz).
        pressure: Cisnienie atmosferyczne w hPa.
        temperature: Temperatura w Celsjuszach.
        humidity: Wilgotnosc wzgledna 0-1.
        wavelength: Dlugosc fali obserwacji w nm.

    Returns:
        Krotka (altitude_deg, azimuth_deg).
    """
    if obs_time is None:
        obs_time = Time.now()

    target = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
    location = EarthLocation(
        lat=lat * u.deg, lon=lon * u.deg, height=alt * u.m,
    )
    altaz_frame = AltAz(
        obstime=obs_time,
        location=location,
        pressure=pressure * u.hPa,
        temperature=temperature * u.deg_C,
        relative_humidity=humidity,
        obswl=wavelength * u.nm,
    )
    result = target.transform_to(altaz_frame)
    return float(result.alt.deg), float(result.az.deg)


def get_current_position(star: dict, cfg: dict) -> dict:
    """
    Oblicza aktualna pozycje gwiazdy na niebie.

    Args:
        star: Slownik z polami ra, dec.
        cfg: Slownik konfiguracji teleskopu.

    Returns:
        Slownik z alt, az, is_above_horizon, calculated_at.
    """
    obs_time = Time.now()
    alt_deg, az_deg = calculate_alt_az(
        ra=star["ra"],
        dec=star["dec"],
        lat=cfg["latitude"],
        lon=cfg["longitude"],
        alt=cfg["altitude"],
        obs_time=obs_time,
        pressure=cfg.get("pressure", 1013.25),
        temperature=cfg.get("temperature", 10.0),
        humidity=cfg.get("humidity", 0.5),
        wavelength=cfg.get("wavelength", 210000.0),
    )

    # Zastosuj offsety kalibracyjne
    az_deg += cfg.get("calibration_offset_az", 0.0)
    alt_deg += cfg.get("calibration_offset_alt", 0.0)

    return {
        "alt": round(alt_deg, 4),
        "az": round(az_deg, 4),
        "is_above_horizon": alt_deg > 0,
        "calculated_at": obs_time.iso,
    }


def angular_distance(alt1: float, az1: float, alt2: float, az2: float) -> float:
    """Oblicza odleglosc katowa miedzy dwoma punktami na sferze (haversine)."""
    alt1_r = np.radians(alt1)
    alt2_r = np.radians(alt2)
    dalt = np.radians(alt2 - alt1)
    daz = np.radians(az2 - az1)

    a = np.sin(dalt / 2) ** 2 + np.cos(alt1_r) * np.cos(alt2_r) * np.sin(daz / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return float(np.degrees(c))


def normalize_delta_az(delta: float) -> float:
    """Normalizuje roznice azymutu do zakresu [-180, +180]."""
    while delta > 180:
        delta -= 360
    while delta < -180:
        delta += 360
    return delta


def is_above_horizon(alt_deg: float) -> bool:
    """Sprawdza czy obiekt jest nad horyzontem."""
    return alt_deg > 0
