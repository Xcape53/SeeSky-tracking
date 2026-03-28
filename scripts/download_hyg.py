#!/usr/bin/env python3
"""
Skrypt do pobierania katalogu gwiazd HYG v4.1 z GitHub.

Katalog HYG (Hipparcos-Yale-Gliese) zawiera dane ponad 100 000 gwiazd
i jest wykorzystywany przez system SeeSky do identyfikacji celów obserwacji.

Użycie:
    python download_hyg.py
    python download_hyg.py --output sciezka/do/pliku.csv
"""

import argparse
import os
import sys
import time
import urllib.request
import urllib.error


# Domyślny URL do katalogu HYG v4.1 na GitHubie
HYG_URL = (
    "https://raw.githubusercontent.com/astronexus/HYG-Database/"
    "refs/heads/main/hyg/CURRENT/hygdata_v41.csv"
)

# Domyślna ścieżka zapisu (względem katalogu skryptu)
DEFAULT_OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "hygdata_v41.csv")


def pobierz_katalog(url: str, sciezka_wyjsciowa: str) -> None:
    """
    Pobiera plik CSV katalogu HYG z podanego URL.

    Wyświetla pasek postępu podczas pobierania i weryfikuje
    rozmiar pliku po zakończeniu.

    Args:
        url: Adres URL pliku do pobrania.
        sciezka_wyjsciowa: Ścieżka lokalna, gdzie zapisać plik.
    """
    # Upewnij się, że katalog docelowy istnieje
    katalog_docelowy = os.path.dirname(sciezka_wyjsciowa)
    if katalog_docelowy and not os.path.exists(katalog_docelowy):
        os.makedirs(katalog_docelowy, exist_ok=True)
        print(f"Utworzono katalog: {katalog_docelowy}")

    print(f"Pobieranie katalogu HYG v4.1...")
    print(f"URL: {url}")
    print(f"Zapis do: {sciezka_wyjsciowa}")
    print()

    try:
        # Otwórz połączenie i odczytaj nagłówki
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "SeeSky-Tracking/1.0")
        odpowiedz = urllib.request.urlopen(req, timeout=60)

        # Sprawdź rozmiar pliku z nagłówków (jeśli dostępny)
        rozmiar_calkowity = odpowiedz.headers.get("Content-Length")
        if rozmiar_calkowity:
            rozmiar_calkowity = int(rozmiar_calkowity)
            print(f"Rozmiar pliku: {rozmiar_calkowity / (1024 * 1024):.2f} MB")
        else:
            print("Rozmiar pliku: nieznany (brak nagłówka Content-Length)")

        # Pobieraj dane blokami i pokazuj postęp
        rozmiar_bloku = 8192
        pobrano = 0
        czas_start = time.time()

        with open(sciezka_wyjsciowa, "wb") as plik:
            while True:
                blok = odpowiedz.read(rozmiar_bloku)
                if not blok:
                    break

                plik.write(blok)
                pobrano += len(blok)

                # Wyświetl pasek postępu
                if rozmiar_calkowity:
                    procent = (pobrano / rozmiar_calkowity) * 100
                    wypelnione = int(procent / 2)
                    pasek = "=" * wypelnione + "-" * (50 - wypelnione)
                    print(
                        f"\r[{pasek}] {procent:5.1f}% "
                        f"({pobrano / (1024 * 1024):.2f} / "
                        f"{rozmiar_calkowity / (1024 * 1024):.2f} MB)",
                        end="",
                        flush=True,
                    )
                else:
                    print(
                        f"\rPobrano: {pobrano / (1024 * 1024):.2f} MB",
                        end="",
                        flush=True,
                    )

        czas_koniec = time.time()
        czas_trwania = czas_koniec - czas_start
        print()  # Nowa linia po pasku postępu
        print()

    except urllib.error.URLError as e:
        print(f"\nBłąd połączenia: {e}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"\nBłąd HTTP {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"\nBłąd zapisu pliku: {e}", file=sys.stderr)
        sys.exit(1)

    # Weryfikacja pobranego pliku
    print("--- Weryfikacja pobranego pliku ---")

    if not os.path.exists(sciezka_wyjsciowa):
        print("BŁĄD: Plik nie został zapisany!", file=sys.stderr)
        sys.exit(1)

    rozmiar_pliku = os.path.getsize(sciezka_wyjsciowa)
    print(f"Rozmiar pliku na dysku: {rozmiar_pliku / (1024 * 1024):.2f} MB ({rozmiar_pliku} bajtów)")

    if rozmiar_calkowity and rozmiar_pliku != rozmiar_calkowity:
        print(
            f"OSTRZEŻENIE: Rozmiar pliku ({rozmiar_pliku}) nie zgadza się "
            f"z oczekiwanym ({rozmiar_calkowity})!",
            file=sys.stderr,
        )
        sys.exit(1)

    if rozmiar_pliku < 1024:
        print("OSTRZEŻENIE: Plik jest podejrzanie mały (< 1 KB)!", file=sys.stderr)
        sys.exit(1)

    # Sprawdź, czy plik wygląda na poprawny CSV (odczytaj pierwszy wiersz)
    try:
        with open(sciezka_wyjsciowa, "r", encoding="utf-8") as plik:
            pierwsza_linia = plik.readline().strip()
            if "id" in pierwsza_linia.lower() and "ra" in pierwsza_linia.lower():
                print("Nagłówek CSV wygląda poprawnie.")
            else:
                print(f"OSTRZEŻENIE: Nieoczekiwany nagłówek: {pierwsza_linia[:100]}", file=sys.stderr)
    except UnicodeDecodeError:
        print("OSTRZEŻENIE: Plik nie wygląda na poprawny plik tekstowy!", file=sys.stderr)

    predkosc = rozmiar_pliku / (1024 * 1024) / czas_trwania if czas_trwania > 0 else 0
    print(f"Czas pobierania: {czas_trwania:.1f} s ({predkosc:.2f} MB/s)")
    print()
    print("Pobieranie zakończone pomyślnie!")


def main():
    """Główna funkcja skryptu - parsowanie argumentów i uruchomienie pobierania."""
    parser = argparse.ArgumentParser(
        description="Pobiera katalog gwiazd HYG v4.1 z repozytorium GitHub astronexus.",
        epilog="Przykład: python download_hyg.py --output ./data/hygdata_v41.csv",
    )
    parser.add_argument(
        "--url",
        default=HYG_URL,
        help=f"URL do pliku CSV (domyślnie: oficjalne repozytorium HYG)",
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT,
        help=f"Ścieżka zapisu pliku (domyślnie: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Nadpisz istniejący plik bez pytania",
    )

    args = parser.parse_args()

    # Sprawdź, czy plik już istnieje
    if os.path.exists(args.output) and not args.force:
        rozmiar = os.path.getsize(args.output)
        print(f"Plik już istnieje: {args.output} ({rozmiar / (1024 * 1024):.2f} MB)")
        odpowiedz = input("Czy nadpisać? [t/N]: ").strip().lower()
        if odpowiedz not in ("t", "tak", "y", "yes"):
            print("Anulowano.")
            sys.exit(0)

    pobierz_katalog(args.url, args.output)


if __name__ == "__main__":
    main()
