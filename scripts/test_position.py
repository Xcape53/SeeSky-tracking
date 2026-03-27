#!/usr/bin/env python3
"""
Skrypt testowy do obliczania pozycji gwiazdy na niebie (Alt/Az).

Wykorzystuje bibliotekę astropy do transformacji współrzędnych
równikowych (RA/Dec) na horyzontalne (Alt/Az) dla podanej
lokalizacji obserwatora.

Użycie:
    python test_position.py --ra 83.633 --dec 22.0145
    python test_position.py --name "Polaris"
    python test_position.py --ra 279.23 --dec 38.78 --lat 52.0 --lon 21.0 --alt 100
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone

try:
    from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_body
    from astropy.time import Time
    import astropy.units as u
    import numpy as np
except ImportError:
    print("BŁĄD: Wymagana biblioteka astropy nie jest zainstalowana.", file=sys.stderr)
    print("Zainstaluj: pip install astropy numpy", file=sys.stderr)
    sys.exit(1)


# Domyślna lokalizacja obserwatora: Wrocław, Polska
DOMYSLNA_SZEROKOSC = 51.1079    # stopnie N
DOMYSLNA_DLUGOSC = 17.0385      # stopnie E
DOMYSLNA_WYSOKOSC = 120.0       # metry n.p.m.

# Domyślne parametry atmosferyczne (korekcja refrakcji)
DOMYSLNE_CISNIENIE = 1013.25    # hPa (ciśnienie na poziomie morza)
DOMYSLNA_TEMPERATURA = 10.0     # °C
DOMYSLNA_WILGOTNOSC = 0.5       # 0-1 (50%)
DOMYSLNA_DLUGOSC_FALI = 210000.0  # nm (~21cm linia wodoru HI)

# Znane gwiazdy - słownik nazwa -> (RA_stopnie, Dec_stopnie)
# Pozwala na szybkie wyszukiwanie bez bazy danych
ZNANE_GWIAZDY = {
    "polaris":      (37.9546, 89.2641),
    "sirius":       (101.287, -16.7161),
    "betelgeuse":   (88.7929, 7.4070),
    "rigel":        (78.6345, -8.2016),
    "vega":         (279.2347, 38.7837),
    "altair":       (297.6958, 8.8683),
    "deneb":        (310.3580, 45.2803),
    "arcturus":     (213.9153, 19.1824),
    "capella":      (79.1723, 45.9980),
    "procyon":      (114.8257, 5.2250),
    "aldebaran":    (68.9802, 16.5093),
    "antares":      (247.3519, -26.4320),
    "spica":        (201.2983, -11.1614),
    "fomalhaut":    (344.4127, -29.6222),
    "regulus":      (152.0929, 11.9672),
    "castor":       (113.6497, 31.8883),
    "pollux":       (116.3289, 28.0262),
    "dubhe":        (165.9319, 61.7510),
    "merak":        (165.4603, 56.3824),
    "mizar":        (200.9814, 54.9254),
}


def znajdz_gwiazde_po_nazwie(nazwa: str) -> tuple[float, float] | None:
    """
    Wyszukuje współrzędne gwiazdy po nazwie własnej.

    Przeszukuje wbudowany słownik znanych gwiazd.

    Args:
        nazwa: Nazwa gwiazdy (bez rozróżniania wielkości liter).

    Returns:
        Krotka (RA, Dec) w stopniach lub None jeśli nie znaleziono.
    """
    klucz = nazwa.lower().strip()
    if klucz in ZNANE_GWIAZDY:
        return ZNANE_GWIAZDY[klucz]
    return None


def oblicz_alt_az(
    ra_deg: float,
    dec_deg: float,
    czas: Time,
    lokalizacja: EarthLocation,
    cisnienie: float = DOMYSLNE_CISNIENIE,
    temperatura: float = DOMYSLNA_TEMPERATURA,
    wilgotnosc: float = DOMYSLNA_WILGOTNOSC,
    dlugosc_fali: float = DOMYSLNA_DLUGOSC_FALI,
) -> tuple[float, float]:
    """
    Oblicza współrzędne horyzontalne (Alt/Az) obiektu z korekcją refrakcji.

    Uwzględnia refrakcję atmosferyczną, co jest istotne szczególnie
    przy niskich wysokościach (< 15°), gdzie błąd może sięgać ~0.5°.
    Parametr obswl (długość fali) jest kluczowy dla radioteleskopów,
    ponieważ refrakcja radiowa różni się od optycznej.

    Args:
        ra_deg: Rektascensja w stopniach.
        dec_deg: Deklinacja w stopniach.
        czas: Czas obserwacji (obiekt astropy Time).
        lokalizacja: Lokalizacja obserwatora.
        cisnienie: Ciśnienie atmosferyczne w hPa (domyślnie: 1013.25).
        temperatura: Temperatura w °C (domyślnie: 10.0).
        wilgotnosc: Wilgotność względna 0-1 (domyślnie: 0.5).
        dlugosc_fali: Długość fali obserwacji w nm (domyślnie: 210000 = 21cm HI).

    Returns:
        Krotka (altitude, azimuth) w stopniach.
    """
    # Utwórz obiekt SkyCoord z współrzędnymi równikowymi
    cel = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")

    # Zdefiniuj układ współrzędnych horyzontalnych z korekcją refrakcji
    ramka_altaz = AltAz(
        obstime=czas,
        location=lokalizacja,
        pressure=cisnienie * u.hPa,
        temperature=temperatura * u.deg_C,
        relative_humidity=wilgotnosc,
        obswl=dlugosc_fali * u.nm,
    )

    # Transformacja
    cel_altaz = cel.transform_to(ramka_altaz)

    return cel_altaz.alt.deg, cel_altaz.az.deg


def znajdz_czas_wschodu_zachodu(
    ra_deg: float,
    dec_deg: float,
    lokalizacja: EarthLocation,
    czas_start: Time,
    czy_nad_horyzontem: bool,
    cisnienie: float = DOMYSLNE_CISNIENIE,
    temperatura: float = DOMYSLNA_TEMPERATURA,
    wilgotnosc: float = DOMYSLNA_WILGOTNOSC,
    dlugosc_fali: float = DOMYSLNA_DLUGOSC_FALI,
) -> str:
    """
    Szacuje czas do następnego wschodu lub zachodu obiektu.

    Sprawdza pozycję obiektu w 5-minutowych krokach przez następne 24h.
    Uwzględnia refrakcję atmosferyczną.

    Args:
        ra_deg: Rektascensja w stopniach.
        dec_deg: Deklinacja w stopniach.
        lokalizacja: Lokalizacja obserwatora.
        czas_start: Aktualny czas.
        czy_nad_horyzontem: Czy obiekt jest teraz nad horyzontem.
        cisnienie: Ciśnienie atmosferyczne w hPa.
        temperatura: Temperatura w °C.
        wilgotnosc: Wilgotność względna 0-1.
        dlugosc_fali: Długość fali obserwacji w nm.

    Returns:
        Tekst opisujący czas do wschodu/zachodu.
    """
    cel = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")

    # Sprawdzaj co 5 minut przez 24 godziny
    kroki = 288  # 24h * 12 kroków/h
    delta_min = 5

    for i in range(1, kroki + 1):
        czas_sprawdzenia = czas_start + timedelta(minutes=i * delta_min)
        czas_astropy = Time(czas_sprawdzenia.to_datetime(timezone=timezone.utc))
        ramka = AltAz(
            obstime=czas_astropy,
            location=lokalizacja,
            pressure=cisnienie * u.hPa,
            temperature=temperatura * u.deg_C,
            relative_humidity=wilgotnosc,
            obswl=dlugosc_fali * u.nm,
        )
        alt = cel.transform_to(ramka).alt.deg

        # Szukamy zmiany stanu (nad/pod horyzontem)
        if czy_nad_horyzontem and alt < 0:
            minuty = i * delta_min
            godziny = minuty // 60
            reszta_min = minuty % 60
            return f"Zachód za ok. {godziny}h {reszta_min}min"
        elif not czy_nad_horyzontem and alt > 0:
            minuty = i * delta_min
            godziny = minuty // 60
            reszta_min = minuty % 60
            return f"Wschód za ok. {godziny}h {reszta_min}min"

    # Obiekt nie zmienia stanu w ciągu 24h (np. Polaris na dużych szerokościach)
    if czy_nad_horyzontem:
        return "Obiekt cyrkulumpolarny - nie zachodzi w ciągu 24h"
    else:
        return "Obiekt nie wschodzi w ciągu 24h (poniżej horyzontu)"


def wyswietl_trajektorie(
    ra_deg: float,
    dec_deg: float,
    lokalizacja: EarthLocation,
    czas_start: Time,
    liczba_punktow: int = 10,
    czas_trwania_min: int = 30,
    cisnienie: float = DOMYSLNE_CISNIENIE,
    temperatura: float = DOMYSLNA_TEMPERATURA,
    wilgotnosc: float = DOMYSLNA_WILGOTNOSC,
    dlugosc_fali: float = DOMYSLNA_DLUGOSC_FALI,
) -> None:
    """
    Wyświetla trajektorię obiektu - pozycje w kolejnych chwilach czasu.

    Pokazuje jak obiekt przesuwa się po niebie w zadanym okresie.
    Uwzględnia refrakcję atmosferyczną.

    Args:
        ra_deg: Rektascensja w stopniach.
        dec_deg: Deklinacja w stopniach.
        lokalizacja: Lokalizacja obserwatora.
        czas_start: Czas początkowy.
        liczba_punktow: Liczba punktów trajektorii.
        czas_trwania_min: Czas trwania w minutach.
        cisnienie: Ciśnienie atmosferyczne w hPa.
        temperatura: Temperatura w °C.
        wilgotnosc: Wilgotność względna 0-1.
        dlugosc_fali: Długość fali obserwacji w nm.
    """
    print(f"\n--- Trajektoria przez następne {czas_trwania_min} minut ({liczba_punktow} punktów) ---")
    print(f"{'Czas (UTC)':<22} {'Alt [°]':>10} {'Az [°]':>10} {'Nad horyzontem':>16}")
    print("-" * 62)

    # Oblicz pozycję w każdym punkcie czasowym
    for i in range(liczba_punktow):
        delta = timedelta(minutes=i * czas_trwania_min / (liczba_punktow - 1))
        czas = czas_start + delta
        alt, az = oblicz_alt_az(
            ra_deg, dec_deg, czas, lokalizacja,
            cisnienie, temperatura, wilgotnosc, dlugosc_fali,
        )

        czas_str = czas.to_datetime(timezone=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        status = "TAK" if alt > 0 else "NIE"

        print(f"{czas_str:<22} {alt:>10.4f} {az:>10.4f} {status:>16}")


def main():
    """Główna funkcja skryptu - parsowanie argumentów i obliczenia pozycji."""
    parser = argparse.ArgumentParser(
        description=(
            "Oblicza aktualną pozycję gwiazdy na niebie (Alt/Az) "
            "dla podanej lokalizacji obserwatora. System SeeSky."
        ),
        epilog=(
            "Przykłady:\n"
            "  python test_position.py --name Polaris\n"
            "  python test_position.py --ra 83.633 --dec 22.0145\n"
            "  python test_position.py --name Vega --lat 52.0 --lon 21.0\n"
            "  python test_position.py --ra 279.23 --dec 38.78 --points 20 --duration 60\n"
            "\nDostępne nazwy gwiazd: " + ", ".join(sorted(ZNANE_GWIAZDY.keys()))
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Grupa współrzędnych celu (nazwa LUB RA/Dec)
    cel_grupa = parser.add_argument_group("Cel obserwacji (podaj --name LUB --ra i --dec)")
    cel_grupa.add_argument(
        "--name", "-n",
        help="Nazwa gwiazdy (np. Polaris, Sirius, Vega)",
    )
    cel_grupa.add_argument(
        "--ra",
        type=float,
        help="Rektascensja w stopniach (0-360)",
    )
    cel_grupa.add_argument(
        "--dec",
        type=float,
        help="Deklinacja w stopniach (-90 do +90)",
    )

    # Lokalizacja obserwatora
    lok_grupa = parser.add_argument_group("Lokalizacja obserwatora")
    lok_grupa.add_argument(
        "--lat",
        type=float,
        default=DOMYSLNA_SZEROKOSC,
        help=f"Szerokość geograficzna [°N] (domyślnie: {DOMYSLNA_SZEROKOSC} - Wrocław)",
    )
    lok_grupa.add_argument(
        "--lon",
        type=float,
        default=DOMYSLNA_DLUGOSC,
        help=f"Długość geograficzna [°E] (domyślnie: {DOMYSLNA_DLUGOSC} - Wrocław)",
    )
    lok_grupa.add_argument(
        "--alt",
        type=float,
        default=DOMYSLNA_WYSOKOSC,
        help=f"Wysokość n.p.m. [m] (domyślnie: {DOMYSLNA_WYSOKOSC})",
    )

    # Parametry trajektorii
    traj_grupa = parser.add_argument_group("Parametry trajektorii")
    traj_grupa.add_argument(
        "--points",
        type=int,
        default=10,
        help="Liczba punktów trajektorii (domyślnie: 10)",
    )
    traj_grupa.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Czas trwania trajektorii w minutach (domyślnie: 30)",
    )

    # Parametry atmosferyczne (korekcja refrakcji)
    atm_grupa = parser.add_argument_group("Parametry atmosferyczne (korekcja refrakcji)")
    atm_grupa.add_argument(
        "--pressure",
        type=float,
        default=DOMYSLNE_CISNIENIE,
        help=f"Ciśnienie atmosferyczne [hPa] (domyślnie: {DOMYSLNE_CISNIENIE})",
    )
    atm_grupa.add_argument(
        "--temperature",
        type=float,
        default=DOMYSLNA_TEMPERATURA,
        help=f"Temperatura [°C] (domyślnie: {DOMYSLNA_TEMPERATURA})",
    )
    atm_grupa.add_argument(
        "--humidity",
        type=float,
        default=DOMYSLNA_WILGOTNOSC,
        help=f"Wilgotność względna 0-1 (domyślnie: {DOMYSLNA_WILGOTNOSC})",
    )
    atm_grupa.add_argument(
        "--wavelength",
        type=float,
        default=DOMYSLNA_DLUGOSC_FALI,
        help=f"Długość fali obserwacji [nm] (domyślnie: {DOMYSLNA_DLUGOSC_FALI} = 21cm HI)",
    )

    args = parser.parse_args()

    # Określ współrzędne celu
    if args.name:
        wynik = znajdz_gwiazde_po_nazwie(args.name)
        if wynik is None:
            print(f"BŁĄD: Nie znaleziono gwiazdy: '{args.name}'", file=sys.stderr)
            print(f"Dostępne nazwy: {', '.join(sorted(ZNANE_GWIAZDY.keys()))}", file=sys.stderr)
            sys.exit(1)
        ra_deg, dec_deg = wynik
        nazwa_celu = args.name.capitalize()
    elif args.ra is not None and args.dec is not None:
        ra_deg = args.ra
        dec_deg = args.dec
        nazwa_celu = f"RA={ra_deg:.4f}° Dec={dec_deg:.4f}°"
    else:
        print("BŁĄD: Podaj nazwę gwiazdy (--name) lub współrzędne (--ra i --dec).", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # Walidacja wartości
    if not (0 <= ra_deg <= 360):
        print(f"BŁĄD: RA musi być w zakresie 0-360° (podano: {ra_deg})", file=sys.stderr)
        sys.exit(1)
    if not (-90 <= dec_deg <= 90):
        print(f"BŁĄD: Dec musi być w zakresie -90 do +90° (podano: {dec_deg})", file=sys.stderr)
        sys.exit(1)

    # Lokalizacja obserwatora
    lokalizacja = EarthLocation(
        lat=args.lat * u.deg,
        lon=args.lon * u.deg,
        height=args.alt * u.m,
    )

    # Aktualny czas UTC
    czas_teraz = Time.now()

    print("=" * 60)
    print("SeeSky - Test obliczania pozycji")
    print("=" * 60)
    print()
    print(f"Cel:            {nazwa_celu}")
    print(f"RA:             {ra_deg:.4f}° ({ra_deg / 15:.4f}h)")
    print(f"Dec:            {dec_deg:+.4f}°")
    print()
    print(f"Obserwator:     {args.lat:.4f}°N, {args.lon:.4f}°E, {args.alt:.0f}m n.p.m.")
    print(f"Czas (UTC):     {czas_teraz.iso}")
    print()
    print(f"Refrakcja:      P={args.pressure} hPa, T={args.temperature} C, "
          f"RH={args.humidity}, wl={args.wavelength} nm")
    print()

    # Oblicz aktualną pozycję horyzontalną (z korekcją refrakcji)
    alt, az = oblicz_alt_az(
        ra_deg, dec_deg, czas_teraz, lokalizacja,
        args.pressure, args.temperature, args.humidity, args.wavelength,
    )

    print("--- Aktualna pozycja horyzontalna (z korekcją refrakcji) ---")
    print(f"Azymut:         {az:.4f}° ({kierunek_z_azymutu(az)})")
    print(f"Wysokość:       {alt:.4f}°")
    print()

    # Czy nad horyzontem?
    nad_horyzontem = alt > 0
    if nad_horyzontem:
        print(f"Status:         NAD HORYZONTEM (widoczna)")
    else:
        print(f"Status:         POD HORYZONTEM (niewidoczna)")

    # Czas do wschodu/zachodu
    print()
    info_wschod_zachod = znajdz_czas_wschodu_zachodu(
        ra_deg, dec_deg, lokalizacja, czas_teraz, nad_horyzontem,
        args.pressure, args.temperature, args.humidity, args.wavelength,
    )
    print(f"Prognoza:       {info_wschod_zachod}")

    # Trajektoria
    wyswietl_trajektorie(
        ra_deg, dec_deg, lokalizacja, czas_teraz,
        liczba_punktow=args.points,
        czas_trwania_min=args.duration,
        cisnienie=args.pressure,
        temperatura=args.temperature,
        wilgotnosc=args.humidity,
        dlugosc_fali=args.wavelength,
    )

    print()
    print("Obliczenia zakończone.")


def kierunek_z_azymutu(az: float) -> str:
    """
    Zwraca kierunek świata na podstawie azymutu.

    Args:
        az: Azymut w stopniach (0-360, 0=N, 90=E, 180=S, 270=W).

    Returns:
        Skrót kierunku (np. "N", "NE", "E").
    """
    kierunki = [
        (0, "N"), (22.5, "NNE"), (45, "NE"), (67.5, "ENE"),
        (90, "E"), (112.5, "ESE"), (135, "SE"), (157.5, "SSE"),
        (180, "S"), (202.5, "SSW"), (225, "SW"), (247.5, "WSW"),
        (270, "W"), (292.5, "WNW"), (315, "NW"), (337.5, "NNW"),
        (360, "N"),
    ]

    # Znajdź najbliższy kierunek
    az = az % 360
    najblizszy = min(kierunki, key=lambda k: abs(k[0] - az))
    return najblizszy[1]


if __name__ == "__main__":
    main()
