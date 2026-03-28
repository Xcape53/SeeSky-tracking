#!/usr/bin/env python3
"""
Benchmark wydajności astropy do obliczeń śledzenia.

Mierzy czas potrzebny na transformację współrzędnych równikowych (RA/Dec)
na horyzontalne (Alt/Az), co jest kluczową operacją w pętli śledzenia.

Wyniki pomagają dobrać optymalny interwał śledzenia dla Raspberry Pi.

Użycie:
    python benchmark_astropy.py
    python benchmark_astropy.py --iterations 500
    python benchmark_astropy.py --verbose
"""

import argparse
import gc
import sys
import time
from datetime import timedelta

try:
    from astropy.coordinates import SkyCoord, EarthLocation, AltAz
    from astropy.time import Time
    import astropy.units as u
    import numpy as np
except ImportError:
    print("BŁĄD: Wymagana biblioteka astropy nie jest zainstalowana.", file=sys.stderr)
    print("Zainstaluj: pip install astropy numpy", file=sys.stderr)
    sys.exit(1)


# Lokalizacja obserwatora: Wrocław, Polska
LOKALIZACJA = EarthLocation(
    lat=51.1079 * u.deg,
    lon=17.0385 * u.deg,
    height=120.0 * u.m,
)

# Cel testowy: Vega (jasna gwiazda, łatwy benchmark)
CEL_RA = 279.2347   # stopnie
CEL_DEC = 38.7837   # stopnie


def rozgrzewka(verbose: bool = False) -> None:
    """
    Rozgrzewka astropy - pierwsze wywołanie jest zawsze wolniejsze.

    Astropy przy pierwszym użyciu ładuje tabele, inicjalizuje cache
    i pobiera dane (np. tablice IERS). Ta funkcja zapewnia,
    że benchmark mierzy rzeczywistą wydajność obliczeń.

    Args:
        verbose: Czy wyświetlać szczegóły rozgrzewki.
    """
    if verbose:
        print("Rozgrzewka astropy (pierwsze wywołanie jest wolniejsze)...")

    cel = SkyCoord(ra=CEL_RA * u.deg, dec=CEL_DEC * u.deg, frame="icrs")
    czas = Time.now()
    ramka = AltAz(obstime=czas, location=LOKALIZACJA)

    start = time.perf_counter()
    wynik = cel.transform_to(ramka)
    koniec = time.perf_counter()

    if verbose:
        print(f"  Rozgrzewka: {(koniec - start) * 1000:.2f} ms")
        print(f"  Alt={wynik.alt.deg:.4f}° Az={wynik.az.deg:.4f}°")
        print()

    # Druga rozgrzewka (po załadowaniu cache)
    start = time.perf_counter()
    wynik = cel.transform_to(ramka)
    koniec = time.perf_counter()

    if verbose:
        print(f"  Rozgrzewka 2 (cache): {(koniec - start) * 1000:.2f} ms")
        print()


def benchmark_pojedyncza_transformacja(iteracje: int, verbose: bool = False) -> dict:
    """
    Mierzy czas pojedynczej transformacji SkyCoord -> AltAz.

    Symuluje sytuację, w której w każdym kroku śledzenia obliczamy
    pozycję dla jednego punktu czasowego.

    Args:
        iteracje: Liczba powtórzeń pomiaru.
        verbose: Czy wyświetlać szczegóły.

    Returns:
        Słownik z wynikami: min, max, srednia, mediana (w milisekundach).
    """
    print(f"[1/3] Pojedyncza transformacja (SkyCoord -> AltAz) x{iteracje}...")

    cel = SkyCoord(ra=CEL_RA * u.deg, dec=CEL_DEC * u.deg, frame="icrs")
    czasy_pomiarow = []

    # Wymuś garbage collection przed benchmarkiem
    gc.collect()
    gc.disable()

    try:
        for i in range(iteracje):
            # Każda iteracja używa nieco innego czasu (realistyczne)
            czas = Time.now() + timedelta(seconds=i * 0.001)
            ramka = AltAz(obstime=czas, location=LOKALIZACJA)

            start = time.perf_counter()
            wynik = cel.transform_to(ramka)
            koniec = time.perf_counter()

            czasy_pomiarow.append((koniec - start) * 1000)  # ms

            if verbose and (i + 1) % (iteracje // 5) == 0:
                print(f"  Postęp: {i + 1}/{iteracje}")
    finally:
        gc.enable()

    wyniki = {
        "nazwa": "Pojedyncza transformacja",
        "iteracje": iteracje,
        "min_ms": min(czasy_pomiarow),
        "max_ms": max(czasy_pomiarow),
        "srednia_ms": np.mean(czasy_pomiarow),
        "mediana_ms": np.median(czasy_pomiarow),
        "std_ms": np.std(czasy_pomiarow),
        "p95_ms": np.percentile(czasy_pomiarow, 95),
        "p99_ms": np.percentile(czasy_pomiarow, 99),
    }

    print(f"  Średnia: {wyniki['srednia_ms']:.3f} ms | "
          f"Mediana: {wyniki['mediana_ms']:.3f} ms | "
          f"Min: {wyniki['min_ms']:.3f} ms | "
          f"Max: {wyniki['max_ms']:.3f} ms")
    print()

    return wyniki


def benchmark_wektoryzowana(liczba_krokow: int = 100, verbose: bool = False) -> dict:
    """
    Mierzy czas wektoryzowanego obliczenia wielu punktów czasowych naraz.

    Astropy potrafi obliczać transformację dla tablicy czasów jednocześnie,
    co jest znacznie szybsze niż pętla po pojedynczych punktach.

    Args:
        liczba_krokow: Liczba punktów czasowych do obliczenia naraz.
        verbose: Czy wyświetlać szczegóły.

    Returns:
        Słownik z wynikami pomiaru.
    """
    print(f"[2/3] Wektoryzowane obliczenie {liczba_krokow} kroków czasowych naraz...")

    cel = SkyCoord(ra=CEL_RA * u.deg, dec=CEL_DEC * u.deg, frame="icrs")

    # Przygotuj tablicę czasów (100 kroków co 1 sekundę)
    czas_start = Time.now()
    czasy = czas_start + np.arange(liczba_krokow) * u.s

    # Wielokrotny pomiar dla dokładności
    powtorzenia = 50
    czasy_pomiarow = []

    gc.collect()
    gc.disable()

    try:
        for i in range(powtorzenia):
            ramka = AltAz(obstime=czasy, location=LOKALIZACJA)

            start = time.perf_counter()
            wynik = cel.transform_to(ramka)
            koniec = time.perf_counter()

            czasy_pomiarow.append((koniec - start) * 1000)  # ms

            if verbose and (i + 1) % 10 == 0:
                print(f"  Postęp: {i + 1}/{powtorzenia}")
    finally:
        gc.enable()

    wyniki = {
        "nazwa": f"Wektoryzowane ({liczba_krokow} kroków)",
        "liczba_krokow": liczba_krokow,
        "powtorzenia": powtorzenia,
        "min_ms": min(czasy_pomiarow),
        "max_ms": max(czasy_pomiarow),
        "srednia_ms": np.mean(czasy_pomiarow),
        "mediana_ms": np.median(czasy_pomiarow),
        "czas_na_krok_ms": np.mean(czasy_pomiarow) / liczba_krokow,
    }

    print(f"  Średnia łączna: {wyniki['srednia_ms']:.3f} ms | "
          f"Na krok: {wyniki['czas_na_krok_ms']:.3f} ms | "
          f"Min: {wyniki['min_ms']:.3f} ms | "
          f"Max: {wyniki['max_ms']:.3f} ms")
    print()

    return wyniki


def benchmark_symulacja_sledzenia(
    czas_trwania_min: int = 30,
    interwal_s: int = 1,
    verbose: bool = False,
) -> dict:
    """
    Mierzy czas pełnej symulacji śledzenia 30-minutowej sesji.

    Symuluje realistyczny scenariusz: oblicza pozycję celu
    co 1 sekundę przez 30 minut (1800 transformacji).

    Args:
        czas_trwania_min: Czas trwania symulowanej sesji w minutach.
        interwal_s: Interwał śledzenia w sekundach.
        verbose: Czy wyświetlać szczegóły.

    Returns:
        Słownik z wynikami pomiaru.
    """
    liczba_krokow = (czas_trwania_min * 60) // interwal_s
    print(f"[3/3] Symulacja śledzenia: {czas_trwania_min} min, "
          f"interwał {interwal_s}s ({liczba_krokow} kroków)...")

    cel = SkyCoord(ra=CEL_RA * u.deg, dec=CEL_DEC * u.deg, frame="icrs")

    # Metoda A: Pojedyncze transformacje (jak w rzeczywistej pętli)
    gc.collect()
    gc.disable()

    czas_start_astropy = Time.now()

    start_a = time.perf_counter()
    for i in range(liczba_krokow):
        czas_i = czas_start_astropy + timedelta(seconds=i * interwal_s)
        ramka = AltAz(obstime=czas_i, location=LOKALIZACJA)
        wynik = cel.transform_to(ramka)
    koniec_a = time.perf_counter()
    czas_a = (koniec_a - start_a) * 1000

    gc.enable()

    print(f"  Metoda A (pętla po pojedynczych): {czas_a:.1f} ms "
          f"({czas_a / liczba_krokow:.3f} ms/krok)")

    # Metoda B: Wektoryzowane obliczenie
    gc.collect()
    gc.disable()

    czasy_tablica = czas_start_astropy + np.arange(liczba_krokow) * interwal_s * u.s

    start_b = time.perf_counter()
    ramka = AltAz(obstime=czasy_tablica, location=LOKALIZACJA)
    wynik = cel.transform_to(ramka)
    koniec_b = time.perf_counter()
    czas_b = (koniec_b - start_b) * 1000

    gc.enable()

    print(f"  Metoda B (wektoryzowane):         {czas_b:.1f} ms "
          f"({czas_b / liczba_krokow:.3f} ms/krok)")
    print(f"  Przyspieszenie B vs A:            {czas_a / czas_b:.1f}x")
    print()

    wyniki = {
        "nazwa": f"Symulacja {czas_trwania_min} min / {interwal_s}s",
        "liczba_krokow": liczba_krokow,
        "petla_ms": czas_a,
        "petla_na_krok_ms": czas_a / liczba_krokow,
        "wektoryzowane_ms": czas_b,
        "wektoryzowane_na_krok_ms": czas_b / liczba_krokow,
        "przyspieszenie": czas_a / czas_b,
    }

    return wyniki


def wyswietl_podsumowanie(wyniki: list[dict]) -> None:
    """
    Wyświetla podsumowanie benchmarków z rekomendacjami.

    Analizuje wyniki i sugeruje optymalny interwał śledzenia
    dla różnych platform (PC, Raspberry Pi).

    Args:
        wyniki: Lista słowników z wynikami poszczególnych benchmarków.
    """
    print("=" * 70)
    print("PODSUMOWANIE BENCHMARKÓW")
    print("=" * 70)
    print()

    # Pokaż wszystkie wyniki w tabeli
    for w in wyniki:
        print(f"  {w['nazwa']}:")
        for klucz, wartosc in w.items():
            if klucz == "nazwa":
                continue
            if isinstance(wartosc, float):
                print(f"    {klucz:<30} {wartosc:.3f}")
            else:
                print(f"    {klucz:<30} {wartosc}")
        print()

    # Rekomendacje
    print("=" * 70)
    print("REKOMENDACJE DLA SYSTEMU SeeSky")
    print("=" * 70)
    print()

    # Bazujemy na pojedynczej transformacji
    if wyniki and "srednia_ms" in wyniki[0]:
        srednia_ms = wyniki[0]["srednia_ms"]

        print(f"Średni czas pojedynczej transformacji: {srednia_ms:.3f} ms")
        print()

        # Szacowanie dla Raspberry Pi (ok. 5-10x wolniejsze niż PC)
        szacunek_rpi = srednia_ms * 7.5  # Środek zakresu
        print(f"Szacunek dla Raspberry Pi 4: ~{szacunek_rpi:.1f} ms/transformację")
        print(f"Szacunek dla Raspberry Pi 5: ~{szacunek_rpi * 0.6:.1f} ms/transformację")
        print()

        # Rekomendowane interwały
        print("Rekomendowane interwały śledzenia:")
        print(f"  PC (ten komputer):      0.5 - 1.0 s (zapas: {1000 / srednia_ms:.0f}x)")
        print(f"  Raspberry Pi 4:         1.0 - 2.0 s (zapas: {1000 / szacunek_rpi:.0f}x)")
        print(f"  Raspberry Pi 5:         0.5 - 1.0 s (zapas: {1000 / (szacunek_rpi * 0.6):.0f}x)")
        print()

        # Ruch nieba - ile się przesuwa cel między krokami
        predkosc_nieba = 15.0 / 3600  # 15 arcsec/s = 0.00417 deg/s
        print("Ruch obiektów na niebie (rotacja Ziemi):")
        print(f"  Prędkość:               15\"/s = 0.00417°/s")
        for interwal in [0.5, 1.0, 2.0, 5.0, 10.0]:
            przesuniecie = predkosc_nieba * interwal
            print(f"  Przy interwale {interwal:>4.1f}s:    {przesuniecie:.5f}° = "
                  f"{przesuniecie * 3600:.1f}\" przesunięcia")
        print()

        # Wnioski
        print("Wnioski:")
        print("  - Interwał 1-2s jest optymalny dla radioteleskopów amatorskich")
        print("  - Przesunięcie 15-30\" jest akceptowalne dla wiązki > 1°")
        print("  - Wektoryzacja przyspiesza obliczenia, ale wymaga więcej RAM")
        print("  - Na Raspberry Pi zalecane jest użycie cache dla powtarzających się obliczeń")


def main():
    """Główna funkcja skryptu - parsowanie argumentów i uruchomienie benchmarków."""
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark wydajności obliczeń astropy dla pętli śledzenia. "
            "Pomaga dobrać optymalny interwał śledzenia dla Raspberry Pi. "
            "System SeeSky."
        ),
        epilog=(
            "Przykłady:\n"
            "  python benchmark_astropy.py\n"
            "  python benchmark_astropy.py --iterations 500 --verbose\n"
            "  python benchmark_astropy.py --duration 60 --interval 2"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Liczba iteracji dla benchmarku pojedynczej transformacji (domyślnie: 1000)",
    )
    parser.add_argument(
        "--vectorized-steps",
        type=int,
        default=100,
        help="Liczba kroków dla benchmarku wektoryzowanego (domyślnie: 100)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Czas trwania symulacji śledzenia w minutach (domyślnie: 30)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1,
        help="Interwał śledzenia w sekundach dla symulacji (domyślnie: 1)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Wyświetlaj szczegółowe informacje podczas benchmarku",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("SeeSky - Benchmark wydajności astropy")
    print("=" * 70)
    print()
    print(f"Cel testowy:    Vega (RA={CEL_RA}° Dec={CEL_DEC}°)")
    print(f"Lokalizacja:    Wrocław (51.1079°N, 17.0385°E)")
    print(f"Platform:       {sys.platform}")
    print()

    # Wyświetl wersje bibliotek
    import astropy
    print(f"Python:         {sys.version.split()[0]}")
    print(f"Astropy:        {astropy.__version__}")
    print(f"NumPy:          {np.__version__}")
    print()

    # Rozgrzewka
    rozgrzewka(verbose=args.verbose)

    # Uruchom benchmarki
    wszystkie_wyniki = []

    # 1. Pojedyncza transformacja
    wynik1 = benchmark_pojedyncza_transformacja(args.iterations, args.verbose)
    wszystkie_wyniki.append(wynik1)

    # 2. Wektoryzowane obliczenie
    wynik2 = benchmark_wektoryzowana(args.vectorized_steps, args.verbose)
    wszystkie_wyniki.append(wynik2)

    # 3. Symulacja śledzenia
    wynik3 = benchmark_symulacja_sledzenia(args.duration, args.interval, args.verbose)
    wszystkie_wyniki.append(wynik3)

    # Podsumowanie
    wyswietl_podsumowanie(wszystkie_wyniki)

    print()
    print("Benchmark zakończony.")


if __name__ == "__main__":
    main()
