#!/usr/bin/env python3
"""
Skrypt parsujący katalog HYG CSV i tworzący bazę danych SQLite.

Odczytuje plik hygdata_v41.csv, konwertuje jednostki (RA z godzin na stopnie,
dystans z parseków na lata świetlne) i zapisuje dane do bazy SQLite
wykorzystywanej przez system SeeSky.

Użycie:
    python parse_catalog.py
    python parse_catalog.py --input dane/hygdata_v41.csv --output baza/stars.db
    python parse_catalog.py --mag-limit 10.0   # tylko gwiazdy jaśniejsze niż 10 mag
"""

import argparse
import csv
import os
import sqlite3
import sys
import time
from collections import Counter


# Domyślne ścieżki (względem katalogu skryptu)
KATALOG_SKRYPTU = os.path.dirname(os.path.abspath(__file__))
DOMYSLNY_PLIK_CSV = os.path.join(KATALOG_SKRYPTU, "data", "hygdata_v41.csv")
DOMYSLNA_BAZA = os.path.join(KATALOG_SKRYPTU, "..", "backend", "database", "star_catalog.db")

# Stałe do konwersji jednostek
GODZINY_NA_STOPNIE = 15.0       # 1 godzina RA = 15 stopni (360/24)
PARSEKI_NA_LATA_SWIETLNE = 3.26156  # 1 parsek = 3.26156 lat świetlnych

# Schemat tabeli w bazie SQLite
SCHEMAT_TABELI = """
CREATE TABLE IF NOT EXISTS stars (
    id INTEGER PRIMARY KEY,
    hyg_id INTEGER UNIQUE,
    proper_name TEXT,
    ra REAL NOT NULL,           -- Rektascensja w stopniach (0-360)
    dec REAL NOT NULL,          -- Deklinacja w stopniach (-90 do +90)
    magnitude REAL,             -- Jasność obserwowana (magnitudo pozorna)
    abs_magnitude REAL,         -- Jasność absolutna
    spectral_type TEXT,         -- Typ widmowy (np. G2V dla Słońca)
    constellation TEXT,         -- 3-literowy skrót konstelacji (np. Ori, UMa)
    distance_ly REAL,           -- Odległość w latach świetlnych
    color_index REAL            -- Indeks barwy (B-V)
);
"""

# Indeksy przyspieszające wyszukiwanie
INDEKSY = [
    "CREATE INDEX IF NOT EXISTS idx_proper_name ON stars(proper_name);",
    "CREATE INDEX IF NOT EXISTS idx_constellation ON stars(constellation);",
    "CREATE INDEX IF NOT EXISTS idx_magnitude ON stars(magnitude);",
    "CREATE INDEX IF NOT EXISTS idx_ra_dec ON stars(ra, dec);",
]


def parsuj_wartosc_float(wartosc: str) -> float | None:
    """
    Bezpiecznie parsuje string na float.

    Zwraca None jeśli wartość jest pusta lub niepoprawna.
    """
    if wartosc is None or wartosc.strip() == "":
        return None
    try:
        return float(wartosc)
    except ValueError:
        return None


def parsuj_wartosc_int(wartosc: str) -> int | None:
    """
    Bezpiecznie parsuje string na int.

    Zwraca None jeśli wartość jest pusta lub niepoprawna.
    """
    if wartosc is None or wartosc.strip() == "":
        return None
    try:
        return int(wartosc)
    except ValueError:
        # Spróbuj przez float (np. "123.0")
        try:
            return int(float(wartosc))
        except ValueError:
            return None


def utworz_baze(sciezka_bazy: str) -> sqlite3.Connection:
    """
    Tworzy bazę SQLite i tabelę stars.

    Jeśli baza już istnieje, usuwa starą tabelę i tworzy nową.

    Args:
        sciezka_bazy: Ścieżka do pliku bazy danych.

    Returns:
        Połączenie do bazy danych.
    """
    # Upewnij się, że katalog docelowy istnieje
    katalog = os.path.dirname(os.path.abspath(sciezka_bazy))
    if katalog and not os.path.exists(katalog):
        os.makedirs(katalog, exist_ok=True)
        print(f"Utworzono katalog: {katalog}")

    polaczenie = sqlite3.connect(sciezka_bazy)
    kursor = polaczenie.cursor()

    # Usuń starą tabelę jeśli istnieje (pełna reimportacja)
    kursor.execute("DROP TABLE IF EXISTS stars;")

    # Utwórz tabelę zgodnie ze schematem
    kursor.execute(SCHEMAT_TABELI)

    polaczenie.commit()
    return polaczenie


def importuj_gwiazdy(
    sciezka_csv: str,
    polaczenie: sqlite3.Connection,
    limit_mag: float | None = None,
) -> dict:
    """
    Importuje gwiazdy z pliku CSV do bazy SQLite.

    Konwertuje:
    - RA z godzin (0-24) na stopnie (0-360)
    - Dystans z parseków na lata świetlne

    Filtruje gwiazdy bez poprawnych wartości RA/Dec.

    Args:
        sciezka_csv: Ścieżka do pliku CSV z katalogiem HYG.
        polaczenie: Połączenie do bazy SQLite.
        limit_mag: Opcjonalny limit jasności (importuj tylko jaśniejsze).

    Returns:
        Słownik ze statystykami importu.
    """
    # Statystyki importu
    statystyki = {
        "razem_wierszy": 0,
        "zaimportowano": 0,
        "pominieto_brak_ra_dec": 0,
        "pominieto_mag_limit": 0,
        "z_nazwa_wlasna": 0,
        "magnitudy": [],         # Lista magnitud do statystyk
        "konstelacje": Counter(),  # Licznik gwiazd per konstelacja
    }

    kursor = polaczenie.cursor()

    # Zapytanie INSERT
    sql_insert = """
        INSERT INTO stars (hyg_id, proper_name, ra, dec, magnitude, abs_magnitude,
                          spectral_type, constellation, distance_ly, color_index)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    print(f"Odczytywanie pliku CSV: {sciezka_csv}")
    czas_start = time.time()

    # Bufor do wsadowego wstawiania (batch insert)
    bufor = []
    ROZMIAR_BUFORA = 5000

    with open(sciezka_csv, "r", encoding="utf-8") as plik:
        czytnik = csv.DictReader(plik)

        # Sprawdź, czy nagłówki zawierają oczekiwane kolumny
        wymagane_kolumny = {"id", "ra", "dec"}
        if not wymagane_kolumny.issubset(set(czytnik.fieldnames or [])):
            brakujace = wymagane_kolumny - set(czytnik.fieldnames or [])
            print(f"BŁĄD: Brakujące kolumny w CSV: {brakujace}", file=sys.stderr)
            sys.exit(1)

        print(f"Znalezione kolumny: {len(czytnik.fieldnames)}")
        print("Importowanie gwiazd...")
        print()

        for wiersz in czytnik:
            statystyki["razem_wierszy"] += 1

            # Parsuj RA (w godzinach) i Dec (w stopniach)
            ra_godziny = parsuj_wartosc_float(wiersz.get("ra", ""))
            dec_stopnie = parsuj_wartosc_float(wiersz.get("dec", ""))

            # Pomiń gwiazdy bez poprawnych współrzędnych
            if ra_godziny is None or dec_stopnie is None:
                statystyki["pominieto_brak_ra_dec"] += 1
                continue

            # Konwersja RA z godzin na stopnie: 1h = 15 stopni
            ra_stopnie = ra_godziny * GODZINY_NA_STOPNIE

            # Sprawdź zakres wartości
            if not (0.0 <= ra_stopnie <= 360.0):
                statystyki["pominieto_brak_ra_dec"] += 1
                continue
            if not (-90.0 <= dec_stopnie <= 90.0):
                statystyki["pominieto_brak_ra_dec"] += 1
                continue

            # Parsuj jasność (magnitudo pozorna)
            magnitude = parsuj_wartosc_float(wiersz.get("mag", ""))

            # Filtr jasności (jeśli ustawiony)
            if limit_mag is not None and magnitude is not None:
                if magnitude > limit_mag:
                    statystyki["pominieto_mag_limit"] += 1
                    continue

            # Parsuj pozostałe pola
            hyg_id = parsuj_wartosc_int(wiersz.get("id", ""))
            nazwa_wlasna = wiersz.get("proper", "").strip() or None
            abs_magnitude = parsuj_wartosc_float(wiersz.get("absmag", ""))
            typ_widmowy = wiersz.get("spect", "").strip() or None
            konstelacja = wiersz.get("con", "").strip() or None
            indeks_barwy = parsuj_wartosc_float(wiersz.get("ci", ""))

            # Konwersja dystansu z parseków na lata świetlne
            dystans_parseki = parsuj_wartosc_float(wiersz.get("dist", ""))
            if dystans_parseki is not None and dystans_parseki > 0:
                dystans_ly = dystans_parseki * PARSEKI_NA_LATA_SWIETLNE
            else:
                dystans_ly = None

            # Zbierz statystyki
            if nazwa_wlasna:
                statystyki["z_nazwa_wlasna"] += 1
            if magnitude is not None:
                statystyki["magnitudy"].append(magnitude)
            if konstelacja:
                statystyki["konstelacje"][konstelacja] += 1

            # Dodaj do bufora
            bufor.append((
                hyg_id, nazwa_wlasna, ra_stopnie, dec_stopnie,
                magnitude, abs_magnitude, typ_widmowy,
                konstelacja, dystans_ly, indeks_barwy,
            ))
            statystyki["zaimportowano"] += 1

            # Wstaw wsadowo gdy bufor pełny
            if len(bufor) >= ROZMIAR_BUFORA:
                kursor.executemany(sql_insert, bufor)
                bufor.clear()

                # Pokaż postęp co 5000 wierszy
                print(
                    f"\r  Przetworzono: {statystyki['razem_wierszy']:>8} wierszy, "
                    f"zaimportowano: {statystyki['zaimportowano']:>8}",
                    end="",
                    flush=True,
                )

    # Wstaw pozostałe rekordy z bufora
    if bufor:
        kursor.executemany(sql_insert, bufor)

    polaczenie.commit()

    czas_koniec = time.time()
    statystyki["czas_importu"] = czas_koniec - czas_start

    print(
        f"\r  Przetworzono: {statystyki['razem_wierszy']:>8} wierszy, "
        f"zaimportowano: {statystyki['zaimportowano']:>8}"
    )
    print()

    return statystyki


def utworz_indeksy(polaczenie: sqlite3.Connection) -> None:
    """Tworzy indeksy na tabeli stars dla szybszego wyszukiwania."""
    kursor = polaczenie.cursor()
    print("Tworzenie indeksów...")
    for sql_indeks in INDEKSY:
        kursor.execute(sql_indeks)
        # Wyciągnij nazwę indeksu z SQL-a dla informacji
        nazwa = sql_indeks.split("EXISTS")[1].split("ON")[0].strip() if "EXISTS" in sql_indeks else "?"
        print(f"  Utworzono indeks: {nazwa}")
    polaczenie.commit()
    print()


def wyswietl_statystyki(statystyki: dict) -> None:
    """
    Wyświetla podsumowanie statystyk importu.

    Pokazuje rozkład magnitud, najpopularniejsze konstelacje
    i inne przydatne informacje.
    """
    print("=" * 60)
    print("STATYSTYKI IMPORTU KATALOGU HYG")
    print("=" * 60)
    print()

    print(f"Razem wierszy w CSV:        {statystyki['razem_wierszy']:>8}")
    print(f"Zaimportowano gwiazd:       {statystyki['zaimportowano']:>8}")
    print(f"Pominieto (brak RA/Dec):    {statystyki['pominieto_brak_ra_dec']:>8}")
    print(f"Pominieto (limit mag):      {statystyki['pominieto_mag_limit']:>8}")
    print(f"Gwiazdy z nazwą własną:     {statystyki['z_nazwa_wlasna']:>8}")
    print(f"Czas importu:               {statystyki['czas_importu']:>7.2f} s")
    print()

    # Rozkład magnitud
    magnitudy = statystyki["magnitudy"]
    if magnitudy:
        print("--- Rozkład magnitud (jasność pozorna) ---")
        print(f"  Najjaśniejsza:  {min(magnitudy):>8.2f} mag")
        print(f"  Najsłabsza:     {max(magnitudy):>8.2f} mag")
        print(f"  Średnia:         {sum(magnitudy) / len(magnitudy):>8.2f} mag")
        print(f"  Mediana:         {sorted(magnitudy)[len(magnitudy) // 2]:>8.2f} mag")
        print()

        # Histogram przedziałowy
        print("  Rozkład wg przedziałów:")
        progi = [
            (-2, 0, "< 0 mag (bardzo jasne)"),
            (0, 2, "0-2 mag (jasne gołym okiem)"),
            (2, 4, "2-4 mag (widoczne gołym okiem)"),
            (4, 6, "4-6 mag (granica oka)"),
            (6, 8, "6-8 mag (lornetka)"),
            (8, 10, "8-10 mag (mały teleskop)"),
            (10, 15, "10-15 mag (średni teleskop)"),
            (15, 30, "15+ mag (duży teleskop)"),
        ]
        for dolny, gorny, opis in progi:
            liczba = sum(1 for m in magnitudy if dolny <= m < gorny)
            if liczba > 0:
                pasek = "#" * min(liczba // 100, 50)
                print(f"    {opis:<35} {liczba:>7} {pasek}")
        print()

    # Najpopularniejsze konstelacje
    konstelacje = statystyki["konstelacje"]
    if konstelacje:
        print("--- Top 15 konstelacji (najwięcej gwiazd) ---")
        for konstelacja, liczba in konstelacje.most_common(15):
            pasek = "#" * min(liczba // 50, 40)
            print(f"    {konstelacja:<6} {liczba:>6} {pasek}")
        print(f"  Razem konstelacji: {len(konstelacje)}")
        print()


def main():
    """Główna funkcja skryptu - parsowanie argumentów i uruchomienie importu."""
    parser = argparse.ArgumentParser(
        description="Parsuje katalog HYG CSV i tworzy bazę danych SQLite dla systemu SeeSky.",
        epilog=(
            "Przykłady:\n"
            "  python parse_catalog.py\n"
            "  python parse_catalog.py --mag-limit 10.0\n"
            "  python parse_catalog.py --input data/hyg.csv --output baza.db"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        default=DOMYSLNY_PLIK_CSV,
        help=f"Ścieżka do pliku CSV katalogu HYG (domyślnie: {DOMYSLNY_PLIK_CSV})",
    )
    parser.add_argument(
        "--output", "-o",
        default=DOMYSLNA_BAZA,
        help=f"Ścieżka do pliku bazy SQLite (domyślnie: {DOMYSLNA_BAZA})",
    )
    parser.add_argument(
        "--mag-limit",
        type=float,
        default=None,
        help="Importuj tylko gwiazdy jaśniejsze niż podana magnitudo (np. 10.0)",
    )

    args = parser.parse_args()

    # Sprawdź, czy plik wejściowy istnieje
    if not os.path.exists(args.input):
        print(f"BŁĄD: Plik CSV nie znaleziony: {args.input}", file=sys.stderr)
        print("Uruchom najpierw: python download_hyg.py", file=sys.stderr)
        sys.exit(1)

    rozmiar_csv = os.path.getsize(args.input)
    print(f"Plik wejściowy: {args.input} ({rozmiar_csv / (1024 * 1024):.2f} MB)")
    print(f"Baza wyjściowa: {args.output}")
    if args.mag_limit is not None:
        print(f"Limit jasności: {args.mag_limit} mag")
    print()

    # Utwórz bazę danych
    polaczenie = utworz_baze(args.output)

    try:
        # Importuj gwiazdy
        statystyki = importuj_gwiazdy(args.input, polaczenie, args.mag_limit)

        # Utwórz indeksy
        utworz_indeksy(polaczenie)

        # Wyświetl statystyki
        wyswietl_statystyki(statystyki)

        # Pokaż rozmiar bazy danych
        rozmiar_bazy = os.path.getsize(args.output)
        print(f"Rozmiar bazy danych: {rozmiar_bazy / (1024 * 1024):.2f} MB")
        print("Import zakończony pomyślnie!")

    finally:
        polaczenie.close()


if __name__ == "__main__":
    main()
