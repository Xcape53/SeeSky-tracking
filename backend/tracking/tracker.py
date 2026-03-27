"""
Petla trackingowa - silnik sledzenia obiektow niebieskich.

Cyklicznie oblicza pozycje celu i generuje delty katowe
dla silnikow teleskopu. Obsluguje start/stop/pause
i interpolacje predykcyjna.
"""

import threading
import time
from datetime import datetime, timezone

from astropy.time import Time
import astropy.units as u

from astropy.coordinates import EarthLocation

from tracking.position import calculate_alt_az, normalize_delta_az, angular_distance


class TrackingLoop:
    """Petla sledzenia obiektu niebieskiego."""

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._running = False
        self._paused = False
        self._lock = threading.Lock()

        # Aktualny stan
        self.observation: dict | None = None
        self.current_alt = 0.0
        self.current_az = 0.0
        self.target_alt: float | None = None
        self.target_az: float | None = None
        self.delta_alt: float | None = None
        self.delta_az: float | None = None
        self.velocity_alt = 0.0
        self.velocity_az = 0.0
        self.start_time: float | None = None
        self.elapsed_seconds = 0

        # Konfiguracja (ustawiana przy starcie)
        self._cfg: dict = {}

    @property
    def is_tracking(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    def start(self, observation: dict, cfg: dict):
        """
        Rozpoczyna sledzenie obserwacji.

        Args:
            observation: Slownik z danymi obserwacji (star_id, ra, dec, duration_minutes).
            cfg: Slownik konfiguracji teleskopu.
        """
        with self._lock:
            if self._running:
                raise RuntimeError("Tracking jest juz aktywny")

            self.observation = observation
            self._cfg = cfg

            # Oblicz poczatkowa pozycje celu
            alt, az = calculate_alt_az(
                ra=observation["ra"],
                dec=observation["dec"],
                lat=cfg["latitude"],
                lon=cfg["longitude"],
                alt=cfg["altitude"],
                pressure=cfg.get("pressure", 1013.25),
                temperature=cfg.get("temperature", 10.0),
                humidity=cfg.get("humidity", 0.5),
                wavelength=cfg.get("wavelength", 210000.0),
            )

            # Zastosuj offsety kalibracyjne
            az += cfg.get("calibration_offset_az", 0.0)
            alt += cfg.get("calibration_offset_alt", 0.0)

            self.current_alt = alt
            self.current_az = az
            self.target_alt = alt
            self.target_az = az
            self.delta_alt = 0.0
            self.delta_az = 0.0
            self.start_time = time.time()
            self.elapsed_seconds = 0
            self._running = True
            self._paused = False

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> dict:
        """Zatrzymuje sledzenie. Zwraca podsumowanie."""
        with self._lock:
            if not self._running:
                raise RuntimeError("Tracking nie jest aktywny")
            self._running = False
            self._paused = False

        if self._thread:
            self._thread.join(timeout=5)

        elapsed = self.elapsed_seconds
        obs = self.observation
        self.observation = None
        self.target_alt = None
        self.target_az = None
        self.delta_alt = None
        self.delta_az = None

        return {
            "elapsed_time": elapsed,
            "status": "stopped",
            "observation_id": obs["id"] if obs else None,
        }

    def pause(self):
        """Wstrzymuje sledzenie."""
        with self._lock:
            if not self._running:
                raise RuntimeError("Tracking nie jest aktywny")
            if self._paused:
                raise RuntimeError("Tracking jest juz wstrzymany")
            self._paused = True

    def resume(self):
        """Wznawia sledzenie."""
        with self._lock:
            if not self._running:
                raise RuntimeError("Tracking nie jest aktywny")
            if not self._paused:
                raise RuntimeError("Tracking nie jest wstrzymany")
            self._paused = False

    def get_status(self) -> dict:
        """Zwraca aktualny stan sledzenia."""
        with self._lock:
            obs = self.observation
            duration = obs["duration_minutes"] * 60 if obs else None
            remaining = None
            if duration is not None:
                remaining = max(0, duration - self.elapsed_seconds)

            # Oblicz LST i HA jesli mamy konfiguracje i obserwacje
            lst_hours = None
            ha_hours = None
            ang_dist = None
            utc_iso = None
            if self._cfg and self._running:
                try:
                    now = Time.now()
                    utc_iso = now.iso
                    loc = EarthLocation(
                        lat=self._cfg["latitude"] * u.deg,
                        lon=self._cfg["longitude"] * u.deg,
                        height=self._cfg.get("altitude", 0) * u.m,
                    )
                    lst = now.sidereal_time("apparent", longitude=loc.lon)
                    lst_hours = round(float(lst.hour), 6)
                    if obs:
                        ra_hours = obs["ra"] / 15.0
                        ha = lst_hours - ra_hours
                        if ha < -12:
                            ha += 24
                        elif ha > 12:
                            ha -= 24
                        ha_hours = round(ha, 6)
                except Exception:
                    pass

            # Odleglosc katowa miedzy aktualna a docelowa pozycja
            if (self.target_alt is not None and self.target_az is not None
                    and self.current_alt is not None):
                try:
                    ang_dist = round(angular_distance(
                        self.current_alt, self.current_az,
                        self.target_alt, self.target_az), 6)
                except Exception:
                    pass

            return {
                "is_tracking": self._running,
                "is_paused": self._paused,
                "current_star": {
                    "id": obs["star_id"],
                    "name": obs.get("star_name", obs.get("proper_name")),
                    "ra": obs["ra"],
                    "dec": obs["dec"],
                    "constellation": obs.get("constellation", None),
                    "magnitude": obs.get("mag", None),
                } if obs else None,
                "current_alt": round(self.current_alt, 4),
                "current_az": round(self.current_az, 4),
                "target_alt": round(self.target_alt, 4) if self.target_alt is not None else None,
                "target_az": round(self.target_az, 4) if self.target_az is not None else None,
                "elapsed_time": self.elapsed_seconds,
                "remaining_time": remaining,
                "delta_alt": round(self.delta_alt, 6) if self.delta_alt is not None else None,
                "delta_az": round(self.delta_az, 6) if self.delta_az is not None else None,
                "velocity_alt": round(self.velocity_alt, 6),
                "velocity_az": round(self.velocity_az, 6),
                "angular_distance": ang_dist,
                "lst_hours": lst_hours,
                "hour_angle": ha_hours,
                "utc_time": utc_iso,
            }

    def _loop(self):
        """Glowna petla sledzenia."""
        interval = self._cfg.get("tracking_interval_seconds", 2.0)
        obs = self.observation
        duration_s = obs["duration_minutes"] * 60

        cfg = self._cfg
        atm_params = {
            "pressure": cfg.get("pressure", 1013.25),
            "temperature": cfg.get("temperature", 10.0),
            "humidity": cfg.get("humidity", 0.5),
            "wavelength": cfg.get("wavelength", 210000.0),
        }

        next_step = time.time()

        while self._running:
            now = time.time()
            self.elapsed_seconds = int(now - self.start_time)

            # Sprawdz czy minelo
            if self.elapsed_seconds >= duration_s:
                with self._lock:
                    self._running = False
                break

            # Czekaj do nastepnego kroku
            if now < next_step:
                sleep_time = next_step - now
                if sleep_time > 0:
                    time.sleep(min(sleep_time, 0.5))
                    if not self._running:
                        break
                continue

            next_step += interval

            # Nie obliczaj jesli pauza
            if self._paused:
                continue

            # Oblicz aktualna pozycje celu
            obs_time = Time.now()
            alt_cel, az_cel = calculate_alt_az(
                ra=obs["ra"], dec=obs["dec"],
                lat=cfg["latitude"], lon=cfg["longitude"], alt=cfg["altitude"],
                obs_time=obs_time, **atm_params,
            )
            az_cel += cfg.get("calibration_offset_az", 0.0)
            alt_cel += cfg.get("calibration_offset_alt", 0.0)

            # Interpolacja predykcyjna
            obs_time_next = obs_time + interval * u.s
            alt_pred, az_pred = calculate_alt_az(
                ra=obs["ra"], dec=obs["dec"],
                lat=cfg["latitude"], lon=cfg["longitude"], alt=cfg["altitude"],
                obs_time=obs_time_next, **atm_params,
            )
            az_pred += cfg.get("calibration_offset_az", 0.0)
            alt_pred += cfg.get("calibration_offset_alt", 0.0)

            with self._lock:
                # Delty
                self.delta_alt = alt_cel - self.current_alt
                self.delta_az = normalize_delta_az(az_cel - self.current_az)

                # Predkosci katowe
                self.velocity_alt = (alt_pred - alt_cel) / interval
                self.velocity_az = normalize_delta_az(az_pred - az_cel) / interval

                # Aktualizuj pozycje
                self.target_alt = alt_cel
                self.target_az = az_cel
                self.current_alt = alt_cel
                self.current_az = az_cel


# Singleton — jedna petla trackingowa na caly backend
tracking_loop = TrackingLoop()
