#!/usr/bin/env python3
"""
Symulacja pętli śledzenia gwiazdy BEZ fizycznych silników.

Skrypt demonstruje działanie algorytmu śledzenia: co N sekund oblicza
aktualną pozycję celu (Alt/Az), porównuje z symulowaną pozycją anteny
i wyznacza korekcję. Pozycja anteny jest aktualizowana o wyliczone delty.

Ten skrypt dowodzi, że koncepcja śledzenia działa poprawnie
przed podłączeniem prawdziwych silników.

Użycie:
    python test_tracking_loop.py --name Vega
    python test_tracking_loop.py --ra 279.23 --dec 38.78 --duration 120 --interval 5
    python test_tracking_loop.py --name Polaris --duration 300 --interval 1
"""

import argparse
import sys
import time
from datetime import datetime, timezone

try:
    from astropy.coordinates import SkyCoord, EarthLocation, AltAz
    from astropy.time import Time
    import astropy.units as u
    import numpy as np
except ImportError:
    print("BŁĄD: Wymagana biblioteka astropy nie jest zainstalowana.", file=sys.stderr)
    print("Zainstaluj: pip install astropy numpy", file=sys.stderr)
    sys.exit(1)


# Domyślna lokalizacja obserwatora: Wrocław, Polska
DOMYSLNA_SZEROKOSC = 51.1079
DOMYSLNA_DLUGOSC = 17.0385
DOMYSLNA_WYSOKOSC = 120.0

# Domyślne parametry atmosferyczne (korekcja refrakcji)
DOMYSLNE_CISNIENIE = 1013.25    # hPa
DOMYSLNA_TEMPERATURA = 10.0     # °C
DOMYSLNA_WILGOTNOSC = 0.5       # 0-1
DOMYSLNA_DLUGOSC_FALI = 210000.0  # nm (~21cm linia wodoru HI)

# Znane gwiazdy - te same co w test_position.py
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
}


def oblicz_pozycje_celu(
    cel: SkyCoord,
    lokalizacja: EarthLocation,
    czas: Time,
    cisnienie: float = DOMYSLNE_CISNIENIE,
    temperatura: float = DOMYSLNA_TEMPERATURA,
    wilgotnosc: float = DOMYSLNA_WILGOTNOSC,
    dlugosc_fali: float = DOMYSLNA_DLUGOSC_FALI,
) -> tuple[float, float]:
    """
    Oblicza współrzędne horyzontalne (Alt/Az) celu z korekcją refrakcji.

    Uwzględnia refrakcję atmosferyczną, co jest istotne szczególnie
    przy niskich wysokościach (< 15°), gdzie błąd może sięgać ~0.5°.

    Args:
        cel: Obiekt SkyCoord z współrzędnymi równikowymi.
        lokalizacja: Lokalizacja obserwatora.
        czas: Czas obserwacji.
        cisnienie: Ciśnienie atmosferyczne w hPa.
        temperatura: Temperatura w °C.
        wilgotnosc: Wilgotność względna 0-1.
        dlugosc_fali: Długość fali obserwacji w nm.

    Returns:
        Krotka (altitude, azimuth) w stopniach.
    """
    ramka_altaz = AltAz(
        obstime=czas,
        location=lokalizacja,
        pressure=cisnienie * u.hPa,
        temperature=temperatura * u.deg_C,
        relative_humidity=wilgotnosc,
        obswl=dlugosc_fali * u.nm,
    )
    cel_altaz = cel.transform_to(ramka_altaz)
    return cel_altaz.alt.deg, cel_altaz.az.deg


def odleglosc_katowa(alt1: float, az1: float, alt2: float, az2: float) -> float:
    """
    Oblicza odległość kątową między dwoma punktami na sferze (haversine).

    Prosta odległość euklidesowa w przestrzeni (Alt, Az) nie jest poprawna
    na sferze — 1° azymutu blisko zenitu to mniejszy kąt na niebie niż
    1° blisko horyzontu. Formuła haversine daje dokładną odległość kątową.

    Args:
        alt1, az1: Współrzędne pierwszego punktu w stopniach.
        alt2, az2: Współrzędne drugiego punktu w stopniach.

    Returns:
        Odległość kątowa w stopniach.
    """
    alt1_r = np.radians(alt1)
    alt2_r = np.radians(alt2)
    dalt = np.radians(alt2 - alt1)
    daz = np.radians(az2 - az1)

    a = np.sin(dalt / 2) ** 2 + np.cos(alt1_r) * np.cos(alt2_r) * np.sin(daz / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return np.degrees(c)


def normalizuj_delta_az(delta: float) -> float:
    """
    Normalizuje różnicę azymutu do zakresu [-180, +180].

    Zapobiega sytuacji gdy antena obraca się o 359° zamiast 1°
    w przeciwnym kierunku.

    Args:
        delta: Surowa różnica azymutu w stopniach.

    Returns:
        Znormalizowana różnica w zakresie [-180, +180].
    """
    while delta > 180:
        delta -= 360
    while delta < -180:
        delta += 360
    return delta


def uruchom_petle_sledzenia(
    ra_deg: float,
    dec_deg: float,
    nazwa_celu: str,
    lokalizacja: EarthLocation,
    czas_trwania_s: int,
    interwal_s: float,
    cisnienie: float = DOMYSLNE_CISNIENIE,
    temperatura: float = DOMYSLNA_TEMPERATURA,
    wilgotnosc: float = DOMYSLNA_WILGOTNOSC,
    dlugosc_fali: float = DOMYSLNA_DLUGOSC_FALI,
) -> dict:
    """
    Uruchamia symulowaną pętlę śledzenia z interpolacją predykcyjną.

    W każdym kroku oblicza pozycję celu TERAZ i za interwal_s sekund,
    generując prędkość kątową do płynnego ruchu silników między krokami.
    Używa formuły haversine do precyzyjnej metryki błędu kątowego
    oraz korekcji refrakcji atmosferycznej.

    Args:
        ra_deg: Rektascensja celu w stopniach.
        dec_deg: Deklinacja celu w stopniach.
        nazwa_celu: Nazwa obiektu (do wyświetlania).
        lokalizacja: Lokalizacja obserwatora.
        czas_trwania_s: Łączny czas trwania symulacji w sekundach.
        interwal_s: Interwał między krokami śledzenia w sekundach.
        cisnienie: Ciśnienie atmosferyczne w hPa.
        temperatura: Temperatura w °C.
        wilgotnosc: Wilgotność względna 0-1.
        dlugosc_fali: Długość fali obserwacji w nm.

    Returns:
        Słownik ze statystykami śledzenia.
    """
    atm = (cisnienie, temperatura, wilgotnosc, dlugosc_fali)

    # Obiekt celowy w układzie równikowym
    cel = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")

    # Oblicz początkową pozycję celu - od niej startuje "antena"
    czas_start = Time.now()
    alt_cel, az_cel = oblicz_pozycje_celu(cel, lokalizacja, czas_start, *atm)

    # Symulowana pozycja anteny - startujemy dokładnie na celu
    antena_alt = alt_cel
    antena_az = az_cel

    # Zbieranie statystyk
    historia_delt = []
    krok = 0
    laczna_rotacja_alt = 0.0
    laczna_rotacja_az = 0.0

    print()
    print("=" * 120)
    print(f"SYMULACJA PĘTLI ŚLEDZENIA (z interpolacją predykcyjną) - {nazwa_celu}")
    print(f"RA={ra_deg:.4f}° Dec={dec_deg:.4f}°")
    print(f"Czas trwania: {czas_trwania_s}s | Interwał: {interwal_s}s")
    print(f"Lokalizacja: {lokalizacja.lat.deg:.4f}°N, {lokalizacja.lon.deg:.4f}°E")
    print(f"Refrakcja: P={cisnienie} hPa, T={temperatura} C, "
          f"RH={wilgotnosc}, wl={dlugosc_fali} nm")
    print("=" * 120)
    print()

    # Nagłówek tabeli
    print(
        f"{'Krok':>5} {'Czas UTC':<20} "
        f"{'Cel_Alt':>10} {'Cel_Az':>10} "
        f"{'Ant_Alt':>10} {'Ant_Az':>10} "
        f"{'dAlt':>10} {'dAz':>10} "
        f"{'|d|':>8} "
        f"{'v_Alt':>10} {'v_Az':>10}"
    )
    print("-" * 136)

    # Sprawdź, czy cel jest nad horyzontem na starcie
    if alt_cel < 0:
        print(f"UWAGA: Cel jest pod horyzontem (Alt={alt_cel:.2f}°)!")
        print("Symulacja będzie kontynuowana, ale w praktyce śledzenie nie ma sensu.")
        print()

    try:
        # Główna pętla śledzenia
        czas_poczatek = time.time()
        nastepny_krok = czas_poczatek

        while True:
            czas_biezacy = time.time()
            uplynelo = czas_biezacy - czas_poczatek

            # Sprawdź, czy minął czas trwania symulacji
            if uplynelo >= czas_trwania_s:
                break

            # Czekaj do następnego kroku
            if czas_biezacy < nastepny_krok:
                czas_do_snu = nastepny_krok - czas_biezacy
                if czas_do_snu > 0:
                    time.sleep(czas_do_snu)

            krok += 1
            nastepny_krok = czas_poczatek + krok * interwal_s

            # Oblicz aktualną pozycję celu
            czas_teraz = Time.now()
            alt_cel, az_cel = oblicz_pozycje_celu(cel, lokalizacja, czas_teraz, *atm)

            # Interpolacja predykcyjna: oblicz pozycję celu za interwal_s
            czas_nastepny = czas_teraz + interwal_s * u.s
            alt_pred, az_pred = oblicz_pozycje_celu(cel, lokalizacja, czas_nastepny, *atm)

            # Prędkości kątowe (°/s) do płynnego ruchu silników
            predkosc_alt = (alt_pred - alt_cel) / interwal_s
            predkosc_az = normalizuj_delta_az(az_pred - az_cel) / interwal_s

            # Oblicz delty (różnicę między celem a anteną)
            delta_alt = alt_cel - antena_alt
            delta_az = normalizuj_delta_az(az_cel - antena_az)

            # Odległość kątowa na sferze (haversine) — precyzyjna metryka
            wielkosc_delta = odleglosc_katowa(
                antena_alt, antena_az, alt_cel, az_cel,
            )

            # Zapisz statystyki
            historia_delt.append({
                "krok": krok,
                "czas": uplynelo,
                "delta_alt": delta_alt,
                "delta_az": delta_az,
                "wielkosc": wielkosc_delta,
                "cel_alt": alt_cel,
                "cel_az": az_cel,
                "antena_alt": antena_alt,
                "antena_az": antena_az,
                "predkosc_alt": predkosc_alt,
                "predkosc_az": predkosc_az,
            })

            # Akumuluj łączną rotację
            laczna_rotacja_alt += abs(delta_alt)
            laczna_rotacja_az += abs(delta_az)

            # Wyświetl wiersz tabeli
            czas_utc = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
            print(
                f"{krok:>5} {czas_utc:<20} "
                f"{alt_cel:>10.4f} {az_cel:>10.4f} "
                f"{antena_alt:>10.4f} {antena_az:>10.4f} "
                f"{delta_alt:>+10.6f} {delta_az:>+10.6f} "
                f"{wielkosc_delta:>8.6f} "
                f"{predkosc_alt:>+10.6f} {predkosc_az:>+10.6f}"
            )

            # Zastosuj korekcję - przesuń antenę do celu
            # (w rzeczywistości silniki by się obróciły o te delty)
            antena_alt += delta_alt
            antena_az += delta_az

    except KeyboardInterrupt:
        print("\n\nPrzerwano przez użytkownika (Ctrl+C).")

    # Przygotuj podsumowanie
    podsumowanie = {
        "nazwa_celu": nazwa_celu,
        "liczba_krokow": len(historia_delt),
        "czas_trwania_rzeczywisty": time.time() - czas_poczatek,
        "interwal": interwal_s,
        "historia": historia_delt,
        "laczna_rotacja_alt": laczna_rotacja_alt,
        "laczna_rotacja_az": laczna_rotacja_az,
    }

    return podsumowanie


def wyswietl_podsumowanie(podsumowanie: dict) -> None:
    """
    Wyświetla podsumowanie symulacji śledzenia.

    Analizuje zebrane delty i podaje statystyki przydatne
    do oceny wymagań dla silników.

    Args:
        podsumowanie: Słownik ze statystykami z pętli śledzenia.
    """
    historia = podsumowanie["historia"]

    if not historia:
        print("\nBrak danych - symulacja nie wykonała żadnych kroków.")
        return

    print()
    print("=" * 70)
    print("PODSUMOWANIE SYMULACJI ŚLEDZENIA")
    print("=" * 70)
    print()

    print(f"Cel:                        {podsumowanie['nazwa_celu']}")
    print(f"Liczba kroków:              {podsumowanie['liczba_krokow']}")
    print(f"Czas trwania:               {podsumowanie['czas_trwania_rzeczywisty']:.1f} s")
    print(f"Interwał:                   {podsumowanie['interwal']} s")
    print()

    # Statystyki delt wysokości (Alt)
    delty_alt = [d["delta_alt"] for d in historia]
    print("--- Delty wysokości (Alt) ---")
    print(f"  Maksymalna:               {max(delty_alt, key=abs):>+.6f}°")
    print(f"  Minimalna:                {min(delty_alt, key=abs):>+.6f}°")
    print(f"  Średnia |delta|:          {np.mean(np.abs(delty_alt)):.6f}°")
    print(f"  Łączna rotacja:           {podsumowanie['laczna_rotacja_alt']:.6f}°")
    print()

    # Statystyki delt azymutu (Az)
    delty_az = [d["delta_az"] for d in historia]
    print("--- Delty azymutu (Az) ---")
    print(f"  Maksymalna:               {max(delty_az, key=abs):>+.6f}°")
    print(f"  Minimalna:                {min(delty_az, key=abs):>+.6f}°")
    print(f"  Średnia |delta|:          {np.mean(np.abs(delty_az)):.6f}°")
    print(f"  Łączna rotacja:           {podsumowanie['laczna_rotacja_az']:.6f}°")
    print()

    # Statystyki łącznej wielkości korekcji
    wielkosci = [d["wielkosc"] for d in historia]
    print("--- Łączna wielkość korekcji ---")
    print(f"  Maksymalna:               {max(wielkosci):.6f}°")
    print(f"  Średnia:                  {np.mean(wielkosci):.6f}°")
    print(f"  Mediana:                  {np.median(wielkosci):.6f}°")
    print()

    # Prędkość kątowa (stopnie na sekundę) - przydatne do doboru silników
    interwal = podsumowanie["interwal"]
    predkosci = [d["wielkosc"] / interwal for d in historia]
    print("--- Wymagana prędkość kątowa (z korekcji) ---")
    print(f"  Maksymalna:               {max(predkosci):.6f} °/s")
    print(f"  Średnia:                  {np.mean(predkosci):.6f} °/s")
    print(f"  (Ziemia obraca się:       0.004167 °/s = 15\"/s)")
    print()

    # Prędkości kątowe z interpolacji predykcyjnej
    pred_alt = [d["predkosc_alt"] for d in historia]
    pred_az = [d["predkosc_az"] for d in historia]
    print("--- Prędkości kątowe (interpolacja predykcyjna) ---")
    print(f"  v_Alt średnia:            {np.mean(pred_alt):>+.6f} °/s")
    print(f"  v_Alt zakres:             [{min(pred_alt):>+.6f}, {max(pred_alt):>+.6f}] °/s")
    print(f"  v_Az  średnia:            {np.mean(pred_az):>+.6f} °/s")
    print(f"  v_Az  zakres:             [{min(pred_az):>+.6f}, {max(pred_az):>+.6f}] °/s")
    print()

    # Czy śledzenie się udało?
    blad_koncowy = wielkosci[-1] if wielkosci else 0
    print(f"Błąd na końcu symulacji (haversine): {blad_koncowy:.6f}°")
    print(f"                             = {blad_koncowy * 3600:.2f}\"")
    if blad_koncowy < 0.01:
        print("Śledzenie: PRECYZYJNE (< 0.01° = 36\")")
    elif blad_koncowy < 0.1:
        print("Śledzenie: DOBRE (< 0.1° = 360\")")
    else:
        print("Śledzenie: WYMAGA POPRAWY")
    print()


def main():
    """Główna funkcja skryptu - parsowanie argumentów i uruchomienie symulacji."""
    parser = argparse.ArgumentParser(
        description=(
            "Symulacja pętli śledzenia gwiazdy BEZ fizycznych silników. "
            "Oblicza korekcje potrzebne do śledzenia obiektu na niebie. "
            "System SeeSky."
        ),
        epilog=(
            "Przykłady:\n"
            "  python test_tracking_loop.py --name Vega\n"
            "  python test_tracking_loop.py --name Polaris --duration 120 --interval 5\n"
            "  python test_tracking_loop.py --ra 279.23 --dec 38.78 --duration 300\n"
            "\nDostępne nazwy gwiazd: " + ", ".join(sorted(ZNANE_GWIAZDY.keys()))
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Cel obserwacji
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

    # Parametry śledzenia
    sledzenie = parser.add_argument_group("Parametry śledzenia")
    sledzenie.add_argument(
        "--duration", "-d",
        type=int,
        default=60,
        help="Czas trwania symulacji w sekundach (domyślnie: 60)",
    )
    sledzenie.add_argument(
        "--interval", "-i",
        type=float,
        default=2.0,
        help="Interwał między krokami śledzenia w sekundach (domyślnie: 2.0)",
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
        "--elevation",
        type=float,
        default=DOMYSLNA_WYSOKOSC,
        help=f"Wysokość n.p.m. [m] (domyślnie: {DOMYSLNA_WYSOKOSC})",
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

    # Określ cel
    if args.name:
        klucz = args.name.lower().strip()
        if klucz not in ZNANE_GWIAZDY:
            print(f"BŁĄD: Nie znaleziono gwiazdy: '{args.name}'", file=sys.stderr)
            print(f"Dostępne: {', '.join(sorted(ZNANE_GWIAZDY.keys()))}", file=sys.stderr)
            sys.exit(1)
        ra_deg, dec_deg = ZNANE_GWIAZDY[klucz]
        nazwa_celu = args.name.capitalize()
    elif args.ra is not None and args.dec is not None:
        ra_deg = args.ra
        dec_deg = args.dec
        nazwa_celu = f"RA={ra_deg:.4f}° Dec={dec_deg:.4f}°"
    else:
        print("BŁĄD: Podaj nazwę gwiazdy (--name) lub współrzędne (--ra i --dec).", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # Walidacja
    if not (0 <= ra_deg <= 360):
        print(f"BŁĄD: RA musi być w zakresie 0-360° (podano: {ra_deg})", file=sys.stderr)
        sys.exit(1)
    if not (-90 <= dec_deg <= 90):
        print(f"BŁĄD: Dec musi być w zakresie -90 do +90° (podano: {dec_deg})", file=sys.stderr)
        sys.exit(1)
    if args.duration <= 0:
        print(f"BŁĄD: Czas trwania musi być > 0 (podano: {args.duration})", file=sys.stderr)
        sys.exit(1)
    if args.interval <= 0:
        print(f"BŁĄD: Interwał musi być > 0 (podano: {args.interval})", file=sys.stderr)
        sys.exit(1)

    # Lokalizacja obserwatora
    lokalizacja = EarthLocation(
        lat=args.lat * u.deg,
        lon=args.lon * u.deg,
        height=args.elevation * u.m,
    )

    # Informacja startowa
    print()
    print("SeeSky - Symulacja pętli śledzenia")
    print(f"Cel: {nazwa_celu} (RA={ra_deg:.4f}° Dec={dec_deg:.4f}°)")
    print(f"Czas trwania: {args.duration}s, Interwał: {args.interval}s")
    print(f"Oczekiwana liczba kroków: {int(args.duration / args.interval)}")
    print(f"Naciśnij Ctrl+C aby przerwać wcześniej.")

    # Uruchom symulację
    podsumowanie = uruchom_petle_sledzenia(
        ra_deg, dec_deg, nazwa_celu,
        lokalizacja,
        czas_trwania_s=args.duration,
        interwal_s=args.interval,
        cisnienie=args.pressure,
        temperatura=args.temperature,
        wilgotnosc=args.humidity,
        dlugosc_fali=args.wavelength,
    )

    # Wyświetl podsumowanie
    wyswietl_podsumowanie(podsumowanie)


if __name__ == "__main__":
    main()
