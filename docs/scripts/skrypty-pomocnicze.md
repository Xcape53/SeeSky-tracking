# Skrypty pomocnicze systemu SeeSky

Dokumentacja wszystkich skryptow znajdujacych sie w katalogu `scripts/` modulu sledzenia (tracking) projektu SeeSky. Skrypty sluza do przygotowania danych katalogowych, testowania obliczen pozycji, symulacji petli sledzenia oraz benchmarkowania wydajnosci.

---

## Spis tresci

1. [download_hyg.py -- Pobieranie katalogu gwiazd](#1-download_hygpy--pobieranie-katalogu-gwiazd)
2. [parse_catalog.py -- Parser CSV do SQLite](#2-parse_catalogpy--parser-csv-do-sqlite)
3. [test_position.py -- Tester obliczen pozycji](#3-test_positionpy--tester-obliczen-pozycji)
4. [test_tracking_loop.py -- Symulacja petli sledzenia](#4-test_tracking_looppy--symulacja-petli-sledzenia)
5. [benchmark_astropy.py -- Benchmark wydajnosci](#5-benchmark_astropypy--benchmark-wydajnosci)

---

## 1. `download_hyg.py` -- Pobieranie katalogu gwiazd

### Opis ogolny

Skrypt pobiera katalog gwiazd HYG (Hipparcos-Yale-Gliese) w wersji 4.1 z repozytorium GitHub `astronexus/HYG-Database`. Katalog zawiera dane ponad 119 626 gwiazd w formacie CSV i jest wykorzystywany przez system SeeSky do identyfikacji celow obserwacji.

Pobierany plik ma rozmiar okolo 32 MB. Skrypt wyswietla pasek postepu podczas pobierania, weryfikuje poprawnosc pobranego pliku (rozmiar, naglowek CSV) i tworzy katalog docelowy jesli nie istnieje.

### Stale

| Stala | Wartosc | Opis |
|-------|---------|------|
| `HYG_URL` | `https://raw.githubusercontent.com/astronexus/HYG-Database/refs/heads/main/hyg/CURRENT/hygdata_v41.csv` | Domyslny URL do pliku CSV katalogu HYG v4.1 na GitHubie |
| `DEFAULT_OUTPUT` | `scripts/data/hygdata_v41.csv` | Domyslna sciezka zapisu pliku (wzgledem katalogu skryptu) |

### Wymagane biblioteki

- `urllib.request`, `urllib.error` (biblioteka standardowa)
- `argparse`, `os`, `sys`, `time` (biblioteka standardowa)

### Funkcje

#### `pobierz_katalog(url, sciezka_wyjsciowa)`

Pobiera plik CSV katalogu HYG z podanego URL i zapisuje na dysku.

**Sygnatura:**
```python
def pobierz_katalog(url: str, sciezka_wyjsciowa: str) -> None
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `url` | `str` | Adres URL pliku do pobrania |
| `sciezka_wyjsciowa` | `str` | Sciezka lokalna, gdzie zapisac plik |

**Typ zwracany:** `None`

**Algorytm krok po kroku:**

1. Sprawdza, czy katalog docelowy istnieje -- jesli nie, tworzy go za pomoca `os.makedirs`.
2. Tworzy zadanie HTTP (`urllib.request.Request`) z naglowkiem `User-Agent: SeeSky-Tracking/1.0`.
3. Otwiera polaczenie z timeoutem 60 sekund.
4. Odczytuje naglowek `Content-Length` (jesli dostepny) aby wyswietlic rozmiar pliku.
5. Pobiera dane w blokach po 8192 bajtow (8 KB), zapisujac je do pliku.
6. Po kazdym bloku wyswietla pasek postepu:
   - Jesli znany rozmiar: pasek procentowy `[====----] 35.2% (11.28 / 32.00 MB)`
   - Jesli nieznany: prosty licznik `Pobrano: 11.28 MB`
7. Po zakonczeniu pobierania przeprowadza weryfikacje:
   - Czy plik istnieje na dysku
   - Czy rozmiar pliku zgadza sie z `Content-Length` (jesli byl dostepny)
   - Czy plik nie jest podejrzanie maly (< 1 KB)
   - Czy pierwszy wiersz wyglada na poprawny naglowek CSV (zawiera `id` i `ra`)
8. Wyswietla czas pobierania i predkosc transferu (MB/s).

**Obsluga bledow:**

- `urllib.error.URLError` -- blad polaczenia sieciowego
- `urllib.error.HTTPError` -- blad HTTP (np. 404, 500)
- `OSError` -- blad zapisu pliku na dysk

Kazdy z powyzszych bledow powoduje wyswietlenie komunikatu na `stderr` i zakonczenie z kodem 1.

**Przyklad uzycia:**
```python
pobierz_katalog(
    "https://raw.githubusercontent.com/astronexus/HYG-Database/refs/heads/main/hyg/CURRENT/hygdata_v41.csv",
    "scripts/data/hygdata_v41.csv"
)
```

---

#### `main()`

Glowna funkcja skryptu -- parsuje argumenty wiersza polecen i uruchamia pobieranie.

**Sygnatura:**
```python
def main() -> None
```

**Typ zwracany:** `None`

**Argumenty wiersza polecen (argparse):**

| Argument | Skrot | Domyslna | Opis |
|----------|-------|----------|------|
| `--url` | -- | `HYG_URL` | URL do pliku CSV |
| `--output` | `-o` | `DEFAULT_OUTPUT` | Sciezka zapisu pliku |
| `--force` | `-f` | `False` | Nadpisz istniejacy plik bez pytania |

**Algorytm krok po kroku:**

1. Parsuje argumenty za pomoca `argparse.ArgumentParser`.
2. Sprawdza, czy plik docelowy juz istnieje:
   - Jesli tak i brak flagi `--force`, wyswietla informacje o istniejacym pliku i pyta uzytkownika o potwierdzenie nadpisania (`t/tak/y/yes`).
   - Jesli uzytkownik odmowi, konczy dzialanie z kodem 0.
3. Wywoluje `pobierz_katalog()` z podanymi parametrami.

**Przyklady uzycia z wiersza polecen:**

```bash
# Pobieranie z domyslnymi ustawieniami
python download_hyg.py

# Pobieranie do konkretnej lokalizacji
python download_hyg.py --output ./dane/hygdata_v41.csv

# Nadpisanie istniejacego pliku bez pytania
python download_hyg.py --force

# Pobieranie z innego URL
python download_hyg.py --url https://example.com/hyg.csv --output ./hyg.csv
```

### Plik wyjsciowy

Pobrany plik to CSV o rozmiarze okolo 32 MB zawierajacy dane 119 626+ gwiazd. Pierwsza linia to naglowek z nazwami kolumn (m.in. `id`, `ra`, `dec`, `mag`, `proper`, `con`, `dist`, `spect`, `ci`, `absmag`).

---

## 2. `parse_catalog.py` -- Parser CSV do SQLite

### Opis ogolny

Skrypt odczytuje plik CSV katalogu HYG (`hygdata_v41.csv`), konwertuje jednostki astronomiczne i zapisuje dane do bazy SQLite (`star_catalog.db`). Baza jest nastepnie wykorzystywana przez system SeeSky do identyfikacji celow obserwacji.

Glowne konwersje:
- **Rektascensja (RA):** z godzin (0-24) na stopnie (0-360), mnozone przez 15
- **Odleglosc:** z parsekow na lata swietlne, mnozone przez 3.26156

### Stale

| Stala | Wartosc | Opis |
|-------|---------|------|
| `KATALOG_SKRYPTU` | (dynamicznie) | Katalog, w ktorym znajduje sie skrypt |
| `DOMYSLNY_PLIK_CSV` | `scripts/data/hygdata_v41.csv` | Domyslna sciezka wejsciowego pliku CSV |
| `DOMYSLNA_BAZA` | `backend/database/star_catalog.db` | Domyslna sciezka wyjsciowej bazy SQLite |
| `GODZINY_NA_STOPNIE` | `15.0` | Wspolczynnik konwersji: 1 godzina RA = 15 stopni (360/24) |
| `PARSEKI_NA_LATA_SWIETLNE` | `3.26156` | Wspolczynnik konwersji: 1 parsek = 3.26156 lat swietlnych |

### Schemat bazy danych

Tabela `stars` zawiera 11 kolumn:

| Kolumna | Typ | Ograniczenia | Opis |
|---------|-----|-------------|------|
| `id` | `INTEGER` | `PRIMARY KEY` | Identyfikator wewnetrzny (autoincrement) |
| `hyg_id` | `INTEGER` | `UNIQUE` | Identyfikator z katalogu HYG |
| `proper_name` | `TEXT` | -- | Nazwa wlasna gwiazdy (np. Sirius, Vega) |
| `ra` | `REAL` | `NOT NULL` | Rektascensja w stopniach (0-360) |
| `dec` | `REAL` | `NOT NULL` | Deklinacja w stopniach (-90 do +90) |
| `magnitude` | `REAL` | -- | Jasnosc obserwowana (magnitudo pozorna) |
| `abs_magnitude` | `REAL` | -- | Jasnosc absolutna |
| `spectral_type` | `TEXT` | -- | Typ widmowy (np. G2V dla Slonca) |
| `constellation` | `TEXT` | -- | 3-literowy skrot konstelacji (np. Ori, UMa) |
| `distance_ly` | `REAL` | -- | Odleglosc w latach swietlnych |
| `color_index` | `REAL` | -- | Indeks barwy (B-V) |

### Indeksy

Skrypt tworzy 4 indeksy przyspieszajace wyszukiwanie:

| Indeks | Kolumny | Zastosowanie |
|--------|---------|-------------|
| `idx_proper_name` | `proper_name` | Wyszukiwanie po nazwie wlasnej |
| `idx_constellation` | `constellation` | Filtrowanie po konstelacji |
| `idx_magnitude` | `magnitude` | Filtrowanie po jasnosci |
| `idx_ra_dec` | `ra, dec` | Wyszukiwanie przestrzenne po wspolrzednych |

### Wymagane biblioteki

- `csv`, `sqlite3`, `argparse`, `os`, `sys`, `time` (biblioteka standardowa)
- `collections.Counter` (biblioteka standardowa)

### Funkcje

#### `parsuj_wartosc_float(wartosc)`

Bezpiecznie parsuje string na liczbe zmiennoprzecinkowa.

**Sygnatura:**
```python
def parsuj_wartosc_float(wartosc: str) -> float | None
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `wartosc` | `str` | Tekst do sparsowania na float |

**Typ zwracany:** `float | None`

**Algorytm krok po kroku:**

1. Sprawdza, czy wartosc jest `None` lub pustym stringiem (po obcieciu bialych znakow) -- jesli tak, zwraca `None`.
2. Probuje wykonac `float(wartosc)`.
3. Jesli konwersja sie powiedzie, zwraca wynik.
4. Jesli wystapi `ValueError`, zwraca `None`.

**Przyklad uzycia:**
```python
parsuj_wartosc_float("3.14")     # -> 3.14
parsuj_wartosc_float("")          # -> None
parsuj_wartosc_float("abc")       # -> None
parsuj_wartosc_float(None)        # -> None
```

---

#### `parsuj_wartosc_int(wartosc)`

Bezpiecznie parsuje string na liczbe calkowita.

**Sygnatura:**
```python
def parsuj_wartosc_int(wartosc: str) -> int | None
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `wartosc` | `str` | Tekst do sparsowania na int |

**Typ zwracany:** `int | None`

**Algorytm krok po kroku:**

1. Sprawdza, czy wartosc jest `None` lub pustym stringiem (po obcieciu bialych znakow) -- jesli tak, zwraca `None`.
2. Probuje wykonac `int(wartosc)`.
3. Jesli konwersja sie nie powiedzie (`ValueError`), probuje sciezke posrednia: `int(float(wartosc))` -- obsluguje przypadki takie jak `"123.0"`.
4. Jesli oba sposoby zawioda, zwraca `None`.

**Przyklad uzycia:**
```python
parsuj_wartosc_int("42")      # -> 42
parsuj_wartosc_int("123.0")   # -> 123
parsuj_wartosc_int("")         # -> None
parsuj_wartosc_int("abc")      # -> None
```

---

#### `utworz_baze(sciezka_bazy)`

Tworzy baze danych SQLite i tabele `stars`.

**Sygnatura:**
```python
def utworz_baze(sciezka_bazy: str) -> sqlite3.Connection
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `sciezka_bazy` | `str` | Sciezka do pliku bazy danych SQLite |

**Typ zwracany:** `sqlite3.Connection` -- polaczenie do nowo utworzonej bazy danych

**Algorytm krok po kroku:**

1. Sprawdza, czy katalog docelowy istnieje -- jesli nie, tworzy go za pomoca `os.makedirs`.
2. Nawiazuje polaczenie z baza SQLite (`sqlite3.connect`).
3. Usuwa istniejaca tabele `stars` (`DROP TABLE IF EXISTS`) -- kazdy import jest pelna reimportacja.
4. Tworzy nowa tabele wedlug zdefiniowanego schematu (`SCHEMAT_TABELI`).
5. Zatwierdza transakcje (`commit`).
6. Zwraca polaczenie do bazy.

**Przyklad uzycia:**
```python
polaczenie = utworz_baze("baza/star_catalog.db")
# polaczenie jest gotowe do importu danych
```

---

#### `importuj_gwiazdy(sciezka_csv, polaczenie, limit_mag)`

Importuje gwiazdy z pliku CSV do bazy SQLite z konwersja jednostek.

**Sygnatura:**
```python
def importuj_gwiazdy(
    sciezka_csv: str,
    polaczenie: sqlite3.Connection,
    limit_mag: float | None = None,
) -> dict
```

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `sciezka_csv` | `str` | -- | Sciezka do pliku CSV z katalogiem HYG |
| `polaczenie` | `sqlite3.Connection` | -- | Polaczenie do bazy SQLite |
| `limit_mag` | `float \| None` | `None` | Opcjonalny limit jasnosci (importuj tylko gwiazdy jasniejsze niz podana wartosc) |

**Typ zwracany:** `dict` -- slownik ze statystykami importu

**Struktura zwracanego slownika:**

| Klucz | Typ | Opis |
|-------|-----|------|
| `razem_wierszy` | `int` | Laczna liczba przetworzonych wierszy CSV |
| `zaimportowano` | `int` | Liczba gwiazd pomyslnie zaimportowanych |
| `pominieto_brak_ra_dec` | `int` | Pominiete z powodu brakujacych lub nieprawidlowych wspolrzednych |
| `pominieto_mag_limit` | `int` | Pominiete z powodu przekroczenia limitu jasnosci |
| `z_nazwa_wlasna` | `int` | Liczba gwiazd posiadajacych nazwe wlasna |
| `magnitudy` | `list[float]` | Lista magnitud do generowania statystyk |
| `konstelacje` | `Counter` | Licznik gwiazd w poszczegolnych konstelacjach |
| `czas_importu` | `float` | Czas trwania importu w sekundach |

**Algorytm krok po kroku:**

1. Inicjalizuje slownik statystyk z licznikami wyzerowymi.
2. Otwiera plik CSV za pomoca `csv.DictReader`.
3. Weryfikuje, czy naglowki CSV zawieraja wymagane kolumny (`id`, `ra`, `dec`).
4. Dla kazdego wiersza:
   a. Parsuje RA (w godzinach) i Dec (w stopniach) na `float`.
   b. Pomija wiersz jesli RA lub Dec sa `None` (brak danych).
   c. Konwertuje RA z godzin na stopnie: `ra_stopnie = ra_godziny * 15.0`.
   d. Waliduje zakresy: RA musi byc w [0, 360], Dec w [-90, +90].
   e. Parsuje magnitude pozorna. Jesli ustawiony `limit_mag` i gwiazda jest slabsza, pomija wiersz.
   f. Parsuje pozostale pola: `hyg_id`, `proper_name`, `abs_magnitude`, `spectral_type`, `constellation`, `color_index`.
   g. Konwertuje odleglosc z parsekow na lata swietlne: `dystans_ly = dystans_parseki * 3.26156`.
   h. Dodaje rekord do bufora wsadowego.
5. Wstawia rekordy wsadowo (batch INSERT) co 5000 rekordow za pomoca `executemany`.
6. Po zakonczeniu petli wstawia pozostale rekordy z bufora.
7. Zatwierdza transakcje i zwraca statystyki.

**Przyklad uzycia:**
```python
polaczenie = utworz_baze("star_catalog.db")
statystyki = importuj_gwiazdy("hygdata_v41.csv", polaczenie, limit_mag=10.0)
print(f"Zaimportowano {statystyki['zaimportowano']} gwiazd")
```

---

#### `utworz_indeksy(polaczenie)`

Tworzy indeksy na tabeli `stars` dla szybszego wyszukiwania.

**Sygnatura:**
```python
def utworz_indeksy(polaczenie: sqlite3.Connection) -> None
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `polaczenie` | `sqlite3.Connection` | Polaczenie do bazy SQLite |

**Typ zwracany:** `None`

**Algorytm krok po kroku:**

1. Iteruje po liscie `INDEKSY` (4 instrukcje SQL `CREATE INDEX IF NOT EXISTS`).
2. Wykonuje kazda instrukcje SQL.
3. Wyswietla nazwe kazdego utworzonego indeksu.
4. Zatwierdza transakcje (`commit`).

**Przyklad uzycia:**
```python
utworz_indeksy(polaczenie)
# Tworzy: idx_proper_name, idx_constellation, idx_magnitude, idx_ra_dec
```

---

#### `wyswietl_statystyki(statystyki)`

Wyswietla podsumowanie statystyk importu.

**Sygnatura:**
```python
def wyswietl_statystyki(statystyki: dict) -> None
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `statystyki` | `dict` | Slownik ze statystykami zwrocony przez `importuj_gwiazdy()` |

**Typ zwracany:** `None`

**Algorytm krok po kroku:**

1. Wyswietla podsumowanie liczbowe: razem wierszy, zaimportowano, pominieto (z podzialem na przyczyny), gwiazdy z nazwa wlasna, czas importu.
2. Jesli dostepne dane o magnitudach:
   a. Wyswietla statystyki: najjasniejsza, najslabsza, srednia, mediana.
   b. Generuje histogram przedzialowy magnitud z 8 przedzialami:
      - `< 0 mag` (bardzo jasne)
      - `0-2 mag` (jasne golym okiem)
      - `2-4 mag` (widoczne golym okiem)
      - `4-6 mag` (granica oka)
      - `6-8 mag` (lornetka)
      - `8-10 mag` (maly teleskop)
      - `10-15 mag` (sredni teleskop)
      - `15+ mag` (duzy teleskop)
3. Wyswietla 15 najpopularniejszych konstelacji (z najwieksza liczba gwiazd) jako ranking z paskami graficznymi.
4. Podaje laczna liczbe konstelacji w zbiorze danych.

**Przyklad uzycia:**
```python
statystyki = importuj_gwiazdy("hygdata_v41.csv", polaczenie)
wyswietl_statystyki(statystyki)
```

---

#### `main()`

Glowna funkcja skryptu -- parsuje argumenty wiersza polecen i uruchamia import.

**Sygnatura:**
```python
def main() -> None
```

**Typ zwracany:** `None`

**Argumenty wiersza polecen (argparse):**

| Argument | Skrot | Domyslna | Opis |
|----------|-------|----------|------|
| `--input` | `-i` | `DOMYSLNY_PLIK_CSV` | Sciezka do pliku CSV katalogu HYG |
| `--output` | `-o` | `DOMYSLNA_BAZA` | Sciezka do pliku bazy SQLite |
| `--mag-limit` | -- | `None` | Importuj tylko gwiazdy jasniejsze niz podana magnitudo |

**Algorytm krok po kroku:**

1. Parsuje argumenty wiersza polecen.
2. Sprawdza, czy plik wejsciowy CSV istnieje -- jesli nie, wyswietla komunikat bledy i sugeruje uruchomienie `download_hyg.py`.
3. Wyswietla informacje o plikach wejsciowym/wyjsciowym i limitach.
4. Tworzy baze danych (`utworz_baze`).
5. Importuje gwiazdy (`importuj_gwiazdy`).
6. Tworzy indeksy (`utworz_indeksy`).
7. Wyswietla statystyki (`wyswietl_statystyki`).
8. Wyswietla rozmiar wynikowej bazy danych.
9. Zamyka polaczenie z baza (w bloku `finally`).

**Przyklady uzycia z wiersza polecen:**

```bash
# Import z domyslnymi ustawieniami
python parse_catalog.py

# Import z limitem jasnosci
python parse_catalog.py --mag-limit 10.0

# Import z niestandardowymi sciezkami
python parse_catalog.py --input dane/hygdata_v41.csv --output baza/stars.db

# Polaczenie: pobranie i import
python download_hyg.py && python parse_catalog.py
```

---

## 3. `test_position.py` -- Tester obliczen pozycji

### Opis ogolny

Skrypt testowy do obliczania pozycji gwiazdy na niebie w ukladzie horyzontalnym (Alt/Az). Wykorzystuje biblioteke `astropy` do transformacji wspolrzednych rownnikowych (RA/Dec) na horyzontalne z uwzglednieniem refrakcji atmosferycznej. Obsluguje zarowno wyszukiwanie gwiazd po nazwie, jak i podawanie wspolrzednych recznie.

Domyslna lokalizacja obserwatora to Wroclaw, Polska (51.1079N, 17.0385E, 120 m n.p.m.). Domyslna dlugosc fali obserwacji to 210 000 nm (21 cm -- linia wodoru HI), co odpowiada typowej obserwacji radioastronomicznej.

### Stale

| Stala | Wartosc | Opis |
|-------|---------|------|
| `DOMYSLNA_SZEROKOSC` | `51.1079` | Szerokosc geograficzna Wroclawia [stopnie N] |
| `DOMYSLNA_DLUGOSC` | `17.0385` | Dlugosc geograficzna Wroclawia [stopnie E] |
| `DOMYSLNA_WYSOKOSC` | `120.0` | Wysokosc n.p.m. [m] |
| `DOMYSLNE_CISNIENIE` | `1013.25` | Cisnienie atmosferyczne [hPa] |
| `DOMYSLNA_TEMPERATURA` | `10.0` | Temperatura [C] |
| `DOMYSLNA_WILGOTNOSC` | `0.5` | Wilgotnosc wzgledna (0-1, czyli 50%) |
| `DOMYSLNA_DLUGOSC_FALI` | `210000.0` | Dlugosc fali [nm] (21 cm linia wodoru HI) |

### Slownik znanych gwiazd (`ZNANE_GWIAZDY`)

Slownik zawiera 19 jasnych gwiazd z ich wspolrzednymi rownnikowymi (RA, Dec) w stopniach:

| Nazwa | RA [stopnie] | Dec [stopnie] |
|-------|-------------|---------------|
| Polaris | 37.9546 | +89.2641 |
| Sirius | 101.287 | -16.7161 |
| Betelgeuse | 88.7929 | +7.4070 |
| Rigel | 78.6345 | -8.2016 |
| Vega | 279.2347 | +38.7837 |
| Altair | 297.6958 | +8.8683 |
| Deneb | 310.3580 | +45.2803 |
| Arcturus | 213.9153 | +19.1824 |
| Capella | 79.1723 | +45.9980 |
| Procyon | 114.8257 | +5.2250 |
| Aldebaran | 68.9802 | +16.5093 |
| Antares | 247.3519 | -26.4320 |
| Spica | 201.2983 | -11.1614 |
| Fomalhaut | 344.4127 | -29.6222 |
| Regulus | 152.0929 | +11.9672 |
| Castor | 113.6497 | +31.8883 |
| Pollux | 116.3289 | +28.0262 |
| Dubhe | 165.9319 | +61.7510 |
| Merak | 165.4603 | +56.3824 |
| Mizar | 200.9814 | +54.9254 |

### Wymagane biblioteki

- `astropy` (SkyCoord, EarthLocation, AltAz, Time, units)
- `numpy`
- `argparse`, `sys`, `datetime` (biblioteka standardowa)

### Funkcje

#### `znajdz_gwiazde_po_nazwie(nazwa)`

Wyszukuje wspolrzedne gwiazdy po nazwie wlasnej w wbudowanym slowniku.

**Sygnatura:**
```python
def znajdz_gwiazde_po_nazwie(nazwa: str) -> tuple[float, float] | None
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `nazwa` | `str` | Nazwa gwiazdy (bez rozrozniania wielkosci liter) |

**Typ zwracany:** `tuple[float, float] | None` -- krotka (RA, Dec) w stopniach lub `None` jesli nie znaleziono

**Algorytm krok po kroku:**

1. Zamienia nazwe na male litery i obcina biale znaki (`.lower().strip()`).
2. Sprawdza, czy klucz istnieje w slowniku `ZNANE_GWIAZDY`.
3. Jesli tak, zwraca krotke (RA, Dec).
4. Jesli nie, zwraca `None`.

**Przyklad uzycia:**
```python
znajdz_gwiazde_po_nazwie("Vega")       # -> (279.2347, 38.7837)
znajdz_gwiazde_po_nazwie("POLARIS")     # -> (37.9546, 89.2641)
znajdz_gwiazde_po_nazwie("Nieznana")    # -> None
```

---

#### `oblicz_alt_az(ra_deg, dec_deg, czas, lokalizacja, cisnienie, temperatura, wilgotnosc, dlugosc_fali)`

Oblicza wspolrzedne horyzontalne (Alt/Az) obiektu niebieskiego z korekcja refrakcji atmosferycznej.

**Sygnatura:**
```python
def oblicz_alt_az(
    ra_deg: float,
    dec_deg: float,
    czas: Time,
    lokalizacja: EarthLocation,
    cisnienie: float = 1013.25,
    temperatura: float = 10.0,
    wilgotnosc: float = 0.5,
    dlugosc_fali: float = 210000.0,
) -> tuple[float, float]
```

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `ra_deg` | `float` | -- | Rektascensja w stopniach (0-360) |
| `dec_deg` | `float` | -- | Deklinacja w stopniach (-90 do +90) |
| `czas` | `Time` | -- | Czas obserwacji (obiekt `astropy.time.Time`) |
| `lokalizacja` | `EarthLocation` | -- | Lokalizacja obserwatora |
| `cisnienie` | `float` | `1013.25` | Cisnienie atmosferyczne [hPa] |
| `temperatura` | `float` | `10.0` | Temperatura [C] |
| `wilgotnosc` | `float` | `0.5` | Wilgotnosc wzgledna (0-1) |
| `dlugosc_fali` | `float` | `210000.0` | Dlugosc fali obserwacji [nm] |

**Typ zwracany:** `tuple[float, float]` -- krotka (altitude, azimuth) w stopniach

**Algorytm krok po kroku:**

1. Tworzy obiekt `SkyCoord` z podanymi wspolrzednymi RA/Dec w ukladzie ICRS.
2. Definiuje ramke ukladu horyzontalnego `AltAz` z parametrami:
   - czas obserwacji (`obstime`)
   - lokalizacja obserwatora (`location`)
   - cisnienie (`pressure`) -- do korekcji refrakcji
   - temperatura (`temperature`) -- do korekcji refrakcji
   - wilgotnosc wzgledna (`relative_humidity`) -- do korekcji refrakcji
   - dlugosc fali obserwacji (`obswl`) -- istotna dla radioteleskopow, poniewaz refrakcja radiowa rozni sie od optycznej
3. Wykonuje transformacje wspolrzednych (`transform_to`).
4. Zwraca krotke (altitude, azimuth) w stopniach.

**Uwagi dotyczace refrakcji:**

- Refrakcja atmosferyczna jest szczegolnie istotna przy niskich wysokosciach (< 15 stopni), gdzie blad moze siegac ~0.5 stopnia.
- Parametr `obswl` (dlugosc fali) jest kluczowy dla radioteleskopow, poniewaz refrakcja na falach radiowych (np. 21 cm) rozni sie od refrakcji swiatla widzialnego.

**Przyklad uzycia:**
```python
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u

lokalizacja = EarthLocation(lat=51.1079*u.deg, lon=17.0385*u.deg, height=120*u.m)
czas = Time.now()

alt, az = oblicz_alt_az(279.2347, 38.7837, czas, lokalizacja)
print(f"Vega: Alt={alt:.4f}  Az={az:.4f}")
```

---

#### `znajdz_czas_wschodu_zachodu(ra_deg, dec_deg, lokalizacja, czas_start, czy_nad_horyzontem, cisnienie, temperatura, wilgotnosc, dlugosc_fali)`

Szacuje czas do nastepnego wschodu lub zachodu obiektu niebieskiego.

**Sygnatura:**
```python
def znajdz_czas_wschodu_zachodu(
    ra_deg: float,
    dec_deg: float,
    lokalizacja: EarthLocation,
    czas_start: Time,
    czy_nad_horyzontem: bool,
    cisnienie: float = 1013.25,
    temperatura: float = 10.0,
    wilgotnosc: float = 0.5,
    dlugosc_fali: float = 210000.0,
) -> str
```

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `ra_deg` | `float` | -- | Rektascensja w stopniach |
| `dec_deg` | `float` | -- | Deklinacja w stopniach |
| `lokalizacja` | `EarthLocation` | -- | Lokalizacja obserwatora |
| `czas_start` | `Time` | -- | Aktualny czas |
| `czy_nad_horyzontem` | `bool` | -- | Czy obiekt jest teraz nad horyzontem |
| `cisnienie` | `float` | `1013.25` | Cisnienie atmosferyczne [hPa] |
| `temperatura` | `float` | `10.0` | Temperatura [C] |
| `wilgotnosc` | `float` | `0.5` | Wilgotnosc wzgledna (0-1) |
| `dlugosc_fali` | `float` | `210000.0` | Dlugosc fali obserwacji [nm] |

**Typ zwracany:** `str` -- tekst opisujacy czas do wschodu/zachodu

**Mozliwe wartosci zwracane:**

- `"Zachod za ok. Xh Ymin"` -- jesli obiekt jest nad horyzontem i znajdzie moment zachodu
- `"Wschod za ok. Xh Ymin"` -- jesli obiekt jest pod horyzontem i znajdzie moment wschodu
- `"Obiekt cyrkulumpolarny - nie zachodzi w ciagu 24h"` -- jesli obiekt jest nad horyzontem przez cale 24h
- `"Obiekt nie wschodzi w ciagu 24h (ponizej horyzontu)"` -- jesli obiekt pozostaje pod horyzontem przez cale 24h

**Algorytm krok po kroku:**

1. Tworzy obiekt `SkyCoord` z podanymi wspolrzednymi.
2. Definiuje 288 krokow czasowych (24 godziny / 5 minut = 288 krokow).
3. Dla kazdego kroku (co 5 minut):
   a. Oblicza czas sprawdzenia: `czas_start + i * 5 minut`.
   b. Tworzy ramke `AltAz` z parametrami refrakcji.
   c. Oblicza wysokosc obiektu (`alt`).
   d. Sprawdza, czy nastapila zmiana stanu (przejscie przez horyzont):
      - Jesli obiekt byl nad horyzontem i `alt < 0` -- znaleziono zachod.
      - Jesli obiekt byl pod horyzontem i `alt > 0` -- znaleziono wschod.
   e. Jesli znaleziono przejscie, oblicza czas w godzinach i minutach i zwraca tekst.
4. Jesli po 24h nie znaleziono zmiany stanu, zwraca odpowiedni komunikat o obiekcie cyrkulumpolarnym lub niewschodzacym.

**Przyklad uzycia:**
```python
czas = Time.now()
info = znajdz_czas_wschodu_zachodu(
    279.2347, 38.7837, lokalizacja, czas,
    czy_nad_horyzontem=True
)
print(info)  # np. "Zachod za ok. 3h 15min"
```

---

#### `wyswietl_trajektorie(ra_deg, dec_deg, lokalizacja, czas_start, liczba_punktow, czas_trwania_min, cisnienie, temperatura, wilgotnosc, dlugosc_fali)`

Wyswietla trajektorie obiektu -- pozycje Alt/Az w kolejnych chwilach czasu.

**Sygnatura:**
```python
def wyswietl_trajektorie(
    ra_deg: float,
    dec_deg: float,
    lokalizacja: EarthLocation,
    czas_start: Time,
    liczba_punktow: int = 10,
    czas_trwania_min: int = 30,
    cisnienie: float = 1013.25,
    temperatura: float = 10.0,
    wilgotnosc: float = 0.5,
    dlugosc_fali: float = 210000.0,
) -> None
```

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `ra_deg` | `float` | -- | Rektascensja w stopniach |
| `dec_deg` | `float` | -- | Deklinacja w stopniach |
| `lokalizacja` | `EarthLocation` | -- | Lokalizacja obserwatora |
| `czas_start` | `Time` | -- | Czas poczatkowy |
| `liczba_punktow` | `int` | `10` | Liczba punktow trajektorii |
| `czas_trwania_min` | `int` | `30` | Czas trwania obserwacji [min] |
| `cisnienie` | `float` | `1013.25` | Cisnienie atmosferyczne [hPa] |
| `temperatura` | `float` | `10.0` | Temperatura [C] |
| `wilgotnosc` | `float` | `0.5` | Wilgotnosc wzgledna (0-1) |
| `dlugosc_fali` | `float` | `210000.0` | Dlugosc fali obserwacji [nm] |

**Typ zwracany:** `None`

**Algorytm krok po kroku:**

1. Wyswietla naglowek tabeli z kolumnami: Czas (UTC), Alt, Az, Nad horyzontem.
2. Dla kazdego z `liczba_punktow` punktow:
   a. Oblicza przesuniecie czasowe: `i * czas_trwania_min / (liczba_punktow - 1)` minut.
   b. Wywoluje `oblicz_alt_az()` dla danego momentu.
   c. Wyswietla wiersz tabeli z czasem UTC, wysokoscia, azymutem i statusem (TAK/NIE).

**Przyklad wyjscia:**
```
--- Trajektoria przez nastepne 30 minut (10 punktow) ---
Czas (UTC)                Alt [deg]     Az [deg]   Nad horyzontem
--------------------------------------------------------------
2026-03-27 20:00:00         45.1234   123.4567              TAK
2026-03-27 20:03:20         44.9876   123.8901              TAK
...
```

---

#### `kierunek_z_azymutu(az)`

Konwertuje azymut na kierunek swiata (roza wiatrow, 16 kierunkow).

**Sygnatura:**
```python
def kierunek_z_azymutu(az: float) -> str
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `az` | `float` | Azymut w stopniach (0-360; 0=N, 90=E, 180=S, 270=W) |

**Typ zwracany:** `str` -- skrot kierunku

**16 obslugiwanych kierunkow:**

`N`, `NNE`, `NE`, `ENE`, `E`, `ESE`, `SE`, `SSE`, `S`, `SSW`, `SW`, `WSW`, `W`, `WNW`, `NW`, `NNW`

**Algorytm krok po kroku:**

1. Definiuje liste 17 punktow kierunkowych (od 0 do 360 stopni, z krokiem 22.5 stopnia).
2. Normalizuje azymut do zakresu [0, 360) za pomoca operatora modulo.
3. Znajduje najblizszy punkt kierunkowy (minimalna roznica bezwzgledna).
4. Zwraca odpowiadajacy mu skrot.

**Przyklad uzycia:**
```python
kierunek_z_azymutu(0)      # -> "N"
kierunek_z_azymutu(45)     # -> "NE"
kierunek_z_azymutu(90)     # -> "E"
kierunek_z_azymutu(180)    # -> "S"
kierunek_z_azymutu(270)    # -> "W"
kierunek_z_azymutu(350)    # -> "NNW"
kierunek_z_azymutu(400)    # -> "NE" (normalizacja 400 -> 40)
```

---

#### `main()`

Glowna funkcja skryptu -- parsuje argumenty wiersza polecen, oblicza i wyswietla pozycje obiektu.

**Sygnatura:**
```python
def main() -> None
```

**Typ zwracany:** `None`

**Argumenty wiersza polecen (argparse):**

**Cel obserwacji (podaj `--name` LUB `--ra` i `--dec`):**

| Argument | Skrot | Typ | Opis |
|----------|-------|-----|------|
| `--name` | `-n` | `str` | Nazwa gwiazdy (np. Polaris, Sirius, Vega) |
| `--ra` | -- | `float` | Rektascensja w stopniach (0-360) |
| `--dec` | -- | `float` | Deklinacja w stopniach (-90 do +90) |

**Lokalizacja obserwatora:**

| Argument | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `--lat` | `float` | `51.1079` | Szerokosc geograficzna [stopnie N] |
| `--lon` | `float` | `17.0385` | Dlugosc geograficzna [stopnie E] |
| `--alt` | `float` | `120.0` | Wysokosc n.p.m. [m] |

**Parametry trajektorii:**

| Argument | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `--points` | `int` | `10` | Liczba punktow trajektorii |
| `--duration` | `int` | `30` | Czas trwania trajektorii [min] |

**Parametry atmosferyczne (korekcja refrakcji):**

| Argument | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `--pressure` | `float` | `1013.25` | Cisnienie atmosferyczne [hPa] |
| `--temperature` | `float` | `10.0` | Temperatura [C] |
| `--humidity` | `float` | `0.5` | Wilgotnosc wzgledna (0-1) |
| `--wavelength` | `float` | `210000.0` | Dlugosc fali obserwacji [nm] |

**Algorytm krok po kroku:**

1. Parsuje argumenty wiersza polecen.
2. Okresla wspolrzedne celu:
   - Jesli podano `--name`, szuka w slowniku `ZNANE_GWIAZDY`.
   - Jesli podano `--ra` i `--dec`, uzywa ich bezposrednio.
   - Jesli nie podano nic, wyswietla blad i pomoc.
3. Waliduje zakresy RA (0-360) i Dec (-90 do +90).
4. Tworzy obiekt `EarthLocation` z podana lokalizacja.
5. Pobiera aktualny czas UTC.
6. Wyswietla informacje o celu, obserwatorze, czasie i parametrach refrakcji.
7. Oblicza aktualna pozycje horyzontalna (`oblicz_alt_az`).
8. Wyswietla azymut z kierunkiem swiata i wysokosc.
9. Informuje, czy obiekt jest nad czy pod horyzontem.
10. Szacuje czas wschodu/zachodu (`znajdz_czas_wschodu_zachodu`).
11. Wyswietla trajektorie (`wyswietl_trajektorie`).

**Przyklady uzycia z wiersza polecen:**

```bash
# Pozycja gwiazdy Polaris (domyslna lokalizacja: Wroclaw)
python test_position.py --name Polaris

# Pozycja po wspolrzednych
python test_position.py --ra 83.633 --dec 22.0145

# Vega widziana z Warszawy
python test_position.py --name Vega --lat 52.0 --lon 21.0 --alt 100

# Dluga trajektoria z 20 punktami
python test_position.py --ra 279.23 --dec 38.78 --points 20 --duration 60

# Z niestandardowymi parametrami atmosferycznymi
python test_position.py --name Sirius --pressure 1000 --temperature 20 --humidity 0.3
```

---

## 4. `test_tracking_loop.py` -- Symulacja petli sledzenia

### Opis ogolny

Skrypt demonstruje dzialanie algorytmu sledzenia gwiazdy BEZ fizycznych silnikow. Co N sekund oblicza aktualna pozycje celu na niebie (Alt/Az), porownuje z symulowana pozycja anteny i wyznacza korekcje (delty katowe). Pozycja anteny jest aktualizowana o wyliczone delty, symulujac ruch silnikow.

Skrypt wykorzystuje interpolacje predykcyjna -- w kazdym kroku oblicza pozycje celu zarowno w chwili obecnej, jak i za `interwal_s` sekund, wyznaczajac predkosc katowa do plynnego ruchu silnikow miedzy krokami. Do pomiaru bledu katowego stosowana jest formula haversine (dokladna na sferze).

Cel: udowodnienie, ze koncepcja sledzenia dziala poprawnie przed podlaczeniem prawdziwych silnikow.

### Stale

| Stala | Wartosc | Opis |
|-------|---------|------|
| `DOMYSLNA_SZEROKOSC` | `51.1079` | Szerokosc geograficzna Wroclawia [stopnie N] |
| `DOMYSLNA_DLUGOSC` | `17.0385` | Dlugosc geograficzna Wroclawia [stopnie E] |
| `DOMYSLNA_WYSOKOSC` | `120.0` | Wysokosc n.p.m. [m] |
| `DOMYSLNE_CISNIENIE` | `1013.25` | Cisnienie atmosferyczne [hPa] |
| `DOMYSLNA_TEMPERATURA` | `10.0` | Temperatura [C] |
| `DOMYSLNA_WILGOTNOSC` | `0.5` | Wilgotnosc wzgledna (0-1) |
| `DOMYSLNA_DLUGOSC_FALI` | `210000.0` | Dlugosc fali [nm] (21 cm linia wodoru HI) |

### Slownik znanych gwiazd (`ZNANE_GWIAZDY`)

Slownik zawiera 10 jasnych gwiazd (podzbior ze skryptu `test_position.py`):

Polaris, Sirius, Betelgeuse, Rigel, Vega, Altair, Deneb, Arcturus, Capella, Procyon

### Wymagane biblioteki

- `astropy` (SkyCoord, EarthLocation, AltAz, Time, units)
- `numpy`
- `argparse`, `sys`, `time`, `datetime` (biblioteka standardowa)

### Funkcje

#### `oblicz_pozycje_celu(cel, lokalizacja, czas, cisnienie, temperatura, wilgotnosc, dlugosc_fali)`

Oblicza wspolrzedne horyzontalne (Alt/Az) celu z korekcja refrakcji.

**Sygnatura:**
```python
def oblicz_pozycje_celu(
    cel: SkyCoord,
    lokalizacja: EarthLocation,
    czas: Time,
    cisnienie: float = 1013.25,
    temperatura: float = 10.0,
    wilgotnosc: float = 0.5,
    dlugosc_fali: float = 210000.0,
) -> tuple[float, float]
```

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `cel` | `SkyCoord` | -- | Obiekt SkyCoord z wspolrzednymi rownnikowymi |
| `lokalizacja` | `EarthLocation` | -- | Lokalizacja obserwatora |
| `czas` | `Time` | -- | Czas obserwacji |
| `cisnienie` | `float` | `1013.25` | Cisnienie atmosferyczne [hPa] |
| `temperatura` | `float` | `10.0` | Temperatura [C] |
| `wilgotnosc` | `float` | `0.5` | Wilgotnosc wzgledna (0-1) |
| `dlugosc_fali` | `float` | `210000.0` | Dlugosc fali obserwacji [nm] |

**Typ zwracany:** `tuple[float, float]` -- krotka (altitude, azimuth) w stopniach

**Algorytm krok po kroku:**

1. Tworzy ramke `AltAz` z podanymi parametrami refrakcji.
2. Transformuje wspolrzedne celu z ukladu rownnikowego (ICRS) na horyzontalny.
3. Zwraca krotke (altitude, azimuth) w stopniach.

**Roznica wzgledem `oblicz_alt_az()` z `test_position.py`:** Ta funkcja przyjmuje gotowy obiekt `SkyCoord` zamiast wspolrzednych RA/Dec jako floatow, co pozwala na ponowne uzycie tego samego obiektu w petli sledzenia bez wielokrotnego tworzenia.

---

#### `odleglosc_katowa(alt1, az1, alt2, az2)`

Oblicza odleglosc katowa miedzy dwoma punktami na sferze za pomoca formuly haversine.

**Sygnatura:**
```python
def odleglosc_katowa(alt1: float, az1: float, alt2: float, az2: float) -> float
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `alt1` | `float` | Wysokosc pierwszego punktu [stopnie] |
| `az1` | `float` | Azymut pierwszego punktu [stopnie] |
| `alt2` | `float` | Wysokosc drugiego punktu [stopnie] |
| `az2` | `float` | Azymut drugiego punktu [stopnie] |

**Typ zwracany:** `float` -- odleglosc katowa w stopniach

**Algorytm krok po kroku:**

1. Konwertuje wszystkie wspolrzedne z stopni na radiany.
2. Oblicza roznicy: `dalt = alt2 - alt1`, `daz = az2 - az1` (w radianach).
3. Stosuje formule haversine:
   ```
   a = sin(dalt/2)^2 + cos(alt1) * cos(alt2) * sin(daz/2)^2
   c = 2 * arctan2(sqrt(a), sqrt(1-a))
   ```
4. Konwertuje wynik z radianow na stopnie.

**Dlaczego haversine, a nie odleglosc euklidesowa:** Prosta odleglosc euklidesowa w przestrzeni (Alt, Az) nie jest poprawna na sferze -- 1 stopien azymutu blisko zenitu odpowiada mniejszemu katowi na niebie niz 1 stopien blisko horyzontu.

**Przyklad uzycia:**
```python
d = odleglosc_katowa(45.0, 180.0, 45.01, 180.02)
print(f"Odleglosc katowa: {d:.6f} deg")
```

---

#### `normalizuj_delta_az(delta)`

Normalizuje roznice azymutu do zakresu [-180, +180].

**Sygnatura:**
```python
def normalizuj_delta_az(delta: float) -> float
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `delta` | `float` | Surowa roznica azymutu w stopniach |

**Typ zwracany:** `float` -- znormalizowana roznica w zakresie [-180, +180]

**Algorytm krok po kroku:**

1. Dopoki `delta > 180`, odejmuje 360.
2. Dopoki `delta < -180`, dodaje 360.
3. Zwraca znormalizowana wartosc.

**Cel:** Zapobieganie sytuacji, w ktorej antena obraca sie o 359 stopni zamiast 1 stopnia w przeciwnym kierunku.

**Przyklad uzycia:**
```python
normalizuj_delta_az(350)    # -> -10  (obrot o 10 w lewo zamiast 350 w prawo)
normalizuj_delta_az(-200)   # -> 160
normalizuj_delta_az(45)     # -> 45   (bez zmian)
```

---

#### `uruchom_petle_sledzenia(ra_deg, dec_deg, nazwa_celu, lokalizacja, czas_trwania_s, interwal_s, cisnienie, temperatura, wilgotnosc, dlugosc_fali)`

Uruchamia symulowana petle sledzenia z interpolacja predykcyjna.

**Sygnatura:**
```python
def uruchom_petle_sledzenia(
    ra_deg: float,
    dec_deg: float,
    nazwa_celu: str,
    lokalizacja: EarthLocation,
    czas_trwania_s: int,
    interwal_s: float,
    cisnienie: float = 1013.25,
    temperatura: float = 10.0,
    wilgotnosc: float = 0.5,
    dlugosc_fali: float = 210000.0,
) -> dict
```

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `ra_deg` | `float` | -- | Rektascensja celu [stopnie] |
| `dec_deg` | `float` | -- | Deklinacja celu [stopnie] |
| `nazwa_celu` | `str` | -- | Nazwa obiektu (do wyswietlania) |
| `lokalizacja` | `EarthLocation` | -- | Lokalizacja obserwatora |
| `czas_trwania_s` | `int` | -- | Laczny czas trwania symulacji [s] |
| `interwal_s` | `float` | -- | Interwal miedzy krokami sledzenia [s] |
| `cisnienie` | `float` | `1013.25` | Cisnienie atmosferyczne [hPa] |
| `temperatura` | `float` | `10.0` | Temperatura [C] |
| `wilgotnosc` | `float` | `0.5` | Wilgotnosc wzgledna (0-1) |
| `dlugosc_fali` | `float` | `210000.0` | Dlugosc fali obserwacji [nm] |

**Typ zwracany:** `dict` -- slownik ze statystykami sledzenia

**Struktura zwracanego slownika:**

| Klucz | Typ | Opis |
|-------|-----|------|
| `nazwa_celu` | `str` | Nazwa sledzonego obiektu |
| `liczba_krokow` | `int` | Liczba wykonanych krokow |
| `czas_trwania_rzeczywisty` | `float` | Rzeczywisty czas symulacji [s] |
| `interwal` | `float` | Interwal miedzy krokami [s] |
| `historia` | `list[dict]` | Lista slownikow z danymi kazdego kroku |
| `laczna_rotacja_alt` | `float` | Sumaryczna rotacja w wysokosci [stopnie] |
| `laczna_rotacja_az` | `float` | Sumaryczna rotacja w azymucie [stopnie] |

**Kazdy element `historia` zawiera:**

| Klucz | Typ | Opis |
|-------|-----|------|
| `krok` | `int` | Numer kroku |
| `czas` | `float` | Uplyniety czas [s] |
| `delta_alt` | `float` | Korekcja wysokosci [stopnie] |
| `delta_az` | `float` | Korekcja azymutu [stopnie] |
| `wielkosc` | `float` | Odleglosc katowa haversine [stopnie] |
| `cel_alt` | `float` | Wysokosc celu [stopnie] |
| `cel_az` | `float` | Azymut celu [stopnie] |
| `antena_alt` | `float` | Wysokosc anteny [stopnie] |
| `antena_az` | `float` | Azymut anteny [stopnie] |
| `predkosc_alt` | `float` | Predkosc katowa w wysokosci [stopnie/s] |
| `predkosc_az` | `float` | Predkosc katowa w azymucie [stopnie/s] |

**Algorytm krok po kroku:**

1. Tworzy obiekt `SkyCoord` z wspolrzednymi celu.
2. Oblicza poczatkowa pozycje celu -- antena startuje dokladnie na celu.
3. Jesli cel jest pod horyzontem, wyswietla ostrzezenie.
4. Glowna petla (dziala w czasie rzeczywistym, z uzyciem `time.sleep`):
   a. Sprawdza, czy uplyniety czas >= czas_trwania_s -- jesli tak, konczy.
   b. Czeka do nastepnego kroku (`time.sleep`).
   c. Oblicza aktualna pozycje celu (`oblicz_pozycje_celu`).
   d. **Interpolacja predykcyjna:** Oblicza pozycje celu za `interwal_s` sekund.
   e. Wyznacza predkosci katowe: `v = (pozycja_przyszla - pozycja_teraz) / interwal`.
   f. Oblicza delty miedzy celem a antena (z normalizacja azymutu).
   g. Oblicza odleglosc katowa (haversine) jako precyzyjna metryke bledu.
   h. Zapisuje dane kroku do historii.
   i. Akumuluje laczna rotacje.
   j. Wyswietla wiersz tabeli z danymi kroku.
   k. Aktualizuje pozycje anteny o obliczone delty.
5. Mozna przerwac skrotem Ctrl+C (obsluga `KeyboardInterrupt`).
6. Zwraca podsumowanie ze statystykami.

**Format wyswietlanej tabeli:**

Kolumny: Krok, Czas UTC, Cel_Alt, Cel_Az, Ant_Alt, Ant_Az, dAlt, dAz, |d| (haversine), v_Alt, v_Az

---

#### `wyswietl_podsumowanie(podsumowanie)`

Wyswietla podsumowanie symulacji sledzenia.

**Sygnatura:**
```python
def wyswietl_podsumowanie(podsumowanie: dict) -> None
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `podsumowanie` | `dict` | Slownik ze statystykami z `uruchom_petle_sledzenia()` |

**Typ zwracany:** `None`

**Algorytm krok po kroku:**

1. Sprawdza, czy sa dane w historii -- jesli nie, wyswietla komunikat i konczy.
2. Wyswietla informacje ogolne: cel, liczba krokow, czas, interwal.
3. **Statystyki delt wysokosci (Alt):**
   - Maksymalna i minimalna delta (bezwzglednie)
   - Srednia wartosc bezwzgledna
   - Laczna rotacja
4. **Statystyki delt azymutu (Az):** analogicznie jak dla wysokosci.
5. **Laczna wielkosc korekcji (haversine):**
   - Maksymalna, srednia, mediana
6. **Wymagana predkosc katowa:**
   - Maksymalna i srednia (stopnie/sekunde)
   - Porownanie z predkoscia obrotu Ziemi (0.004167 stopnia/s = 15"/s)
7. **Predkosci katowe z interpolacji predykcyjnej:**
   - Srednie i zakresy dla Alt i Az
8. **Ocena jakosci sledzenia** (na podstawie koncowego bledu haversine):
   - `< 0.01 stopnia` (36") -- PRECYZYJNE
   - `< 0.1 stopnia` (360") -- DOBRE
   - `>= 0.1 stopnia` -- WYMAGA POPRAWY

---

#### `main()`

Glowna funkcja skryptu -- parsuje argumenty wiersza polecen i uruchamia symulacje.

**Sygnatura:**
```python
def main() -> None
```

**Typ zwracany:** `None`

**Argumenty wiersza polecen (argparse):**

**Cel obserwacji (podaj `--name` LUB `--ra` i `--dec`):**

| Argument | Skrot | Typ | Opis |
|----------|-------|-----|------|
| `--name` | `-n` | `str` | Nazwa gwiazdy |
| `--ra` | -- | `float` | Rektascensja [stopnie] |
| `--dec` | -- | `float` | Deklinacja [stopnie] |

**Parametry sledzenia:**

| Argument | Skrot | Typ | Domyslna | Opis |
|----------|-------|-----|----------|------|
| `--duration` | `-d` | `int` | `60` | Czas trwania symulacji [s] |
| `--interval` | `-i` | `float` | `2.0` | Interwal miedzy krokami [s] |

**Lokalizacja obserwatora:**

| Argument | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `--lat` | `float` | `51.1079` | Szerokosc geograficzna [stopnie N] |
| `--lon` | `float` | `17.0385` | Dlugosc geograficzna [stopnie E] |
| `--elevation` | `float` | `120.0` | Wysokosc n.p.m. [m] |

**Parametry atmosferyczne:**

| Argument | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `--pressure` | `float` | `1013.25` | Cisnienie [hPa] |
| `--temperature` | `float` | `10.0` | Temperatura [C] |
| `--humidity` | `float` | `0.5` | Wilgotnosc (0-1) |
| `--wavelength` | `float` | `210000.0` | Dlugosc fali [nm] |

**Algorytm krok po kroku:**

1. Parsuje argumenty wiersza polecen.
2. Okresla cel (nazwa lub wspolrzedne).
3. Waliduje zakresy RA, Dec, czas trwania (> 0), interwal (> 0).
4. Tworzy obiekt `EarthLocation`.
5. Wyswietla informacje startowe i oczekiwana liczbe krokow.
6. Uruchamia `uruchom_petle_sledzenia()`.
7. Wywoluje `wyswietl_podsumowanie()`.

**Przyklady uzycia z wiersza polecen:**

```bash
# Sledzenie Vegi przez 60s co 2s (domyslne)
python test_tracking_loop.py --name Vega

# Sledzenie Polaris przez 5 minut co 5s
python test_tracking_loop.py --name Polaris --duration 300 --interval 5

# Sledzenie po wspolrzednych przez 2 minuty co 1s
python test_tracking_loop.py --ra 279.23 --dec 38.78 --duration 120 --interval 1

# Sledzenie z inna lokalizacja
python test_tracking_loop.py --name Sirius --lat 52.0 --lon 21.0 --elevation 100
```

---

## 5. `benchmark_astropy.py` -- Benchmark wydajnosci

### Opis ogolny

Skrypt mierzy wydajnosc obliczen astropy kluczowych dla petli sledzenia -- transformacji wspolrzednych rownnikowych (RA/Dec) na horyzontalne (Alt/Az). Wyniki pomagaja dobrac optymalny interwal sledzenia, szczegolnie z mysla o uruchomieniu na Raspberry Pi, ktore jest kilkukrotnie wolniejsze od typowego PC.

Skrypt przeprowadza trzy benchmarki:
1. Pojedyncza transformacja (N iteracji)
2. Wektoryzowane obliczenie (wiele punktow czasowych naraz)
3. Symulacja 30-minutowej sesji sledzenia (petla vs wektoryzacja)

Na zakonczenie generuje rekomendacje dotyczace optymalnych interwalow dla roznych platform.

### Stale

| Stala | Wartosc | Opis |
|-------|---------|------|
| `LOKALIZACJA` | Wroclaw (51.1079N, 17.0385E, 120m) | Obiekt `EarthLocation` obserwatora |
| `CEL_RA` | `279.2347` | Rektascensja celu testowego (Vega) [stopnie] |
| `CEL_DEC` | `38.7837` | Deklinacja celu testowego (Vega) [stopnie] |

### Wymagane biblioteki

- `astropy` (SkyCoord, EarthLocation, AltAz, Time, units)
- `numpy`
- `gc` (garbage collector -- do precyzyjnych pomiarow)
- `argparse`, `sys`, `time`, `datetime` (biblioteka standardowa)

### Funkcje

#### `rozgrzewka(verbose)`

Wykonuje rozgrzewke astropy -- pierwsze wywolanie jest zawsze wolniejsze z powodu ladowania tabel i inicjalizacji cache.

**Sygnatura:**
```python
def rozgrzewka(verbose: bool = False) -> None
```

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `verbose` | `bool` | `False` | Czy wyswietlac szczegoly rozgrzewki |

**Typ zwracany:** `None`

**Algorytm krok po kroku:**

1. Tworzy obiekt `SkyCoord` dla Vegi i pobiera aktualny czas.
2. **Rozgrzewka 1 (z ladowaniem):** Wykonuje transformacje i mierzy czas. Przy pierwszym uzyciu astropy laduje tabele IERS, inicjalizuje cache itp.
3. Jesli `verbose`, wyswietla czas rozgrzewki i obliczone wspolrzedne.
4. **Rozgrzewka 2 (z cache):** Powtarza transformacje -- powinna byc szybsza, bo cache jest juz zaladowany.
5. Jesli `verbose`, wyswietla czas drugiej rozgrzewki.

**Przyklad uzycia:**
```python
rozgrzewka(verbose=True)
# Wyswietla np.:
# Rozgrzewka: 450.32 ms
# Alt=45.1234  Az=123.4567
# Rozgrzewka 2 (cache): 12.45 ms
```

---

#### `benchmark_pojedyncza_transformacja(iteracje, verbose)`

Mierzy czas pojedynczej transformacji SkyCoord na AltAz.

**Sygnatura:**
```python
def benchmark_pojedyncza_transformacja(iteracje: int, verbose: bool = False) -> dict
```

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `iteracje` | `int` | -- | Liczba powtorzen pomiaru |
| `verbose` | `bool` | `False` | Czy wyswietlac szczegoly |

**Typ zwracany:** `dict` -- slownik z wynikami pomiaru

**Struktura zwracanego slownika:**

| Klucz | Typ | Opis |
|-------|-----|------|
| `nazwa` | `str` | `"Pojedyncza transformacja"` |
| `iteracje` | `int` | Liczba iteracji |
| `min_ms` | `float` | Najkrotszy czas [ms] |
| `max_ms` | `float` | Najdluzszy czas [ms] |
| `srednia_ms` | `float` | Sredni czas [ms] |
| `mediana_ms` | `float` | Mediana czasu [ms] |
| `std_ms` | `float` | Odchylenie standardowe [ms] |
| `p95_ms` | `float` | 95. percentyl [ms] |
| `p99_ms` | `float` | 99. percentyl [ms] |

**Algorytm krok po kroku:**

1. Tworzy obiekt `SkyCoord` dla Vegi.
2. Wylacza garbage collector (`gc.disable()`) aby nie zaklocalzmiarow.
3. Dla kazdej iteracji:
   a. Tworzy nowy czas (nieco inny w kazdej iteracji -- realistyczny scenariusz).
   b. Tworzy ramke `AltAz`.
   c. Mierzy czas transformacji za pomoca `time.perf_counter()`.
   d. Zapisuje czas w milisekundach.
4. Wlacza z powrotem garbage collector.
5. Oblicza statystyki: min, max, srednia, mediana, odchylenie standardowe, 95. i 99. percentyl.
6. Wyswietla podsumowanie i zwraca slownik wynikow.

**Przyklad uzycia:**
```python
wyniki = benchmark_pojedyncza_transformacja(1000)
print(f"Srednia: {wyniki['srednia_ms']:.3f} ms")
```

---

#### `benchmark_wektoryzowana(liczba_krokow, verbose)`

Mierzy czas wektoryzowanego obliczenia wielu punktow czasowych jednoczesnie.

**Sygnatura:**
```python
def benchmark_wektoryzowana(liczba_krokow: int = 100, verbose: bool = False) -> dict
```

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `liczba_krokow` | `int` | `100` | Liczba punktow czasowych do obliczenia naraz |
| `verbose` | `bool` | `False` | Czy wyswietlac szczegoly |

**Typ zwracany:** `dict` -- slownik z wynikami pomiaru

**Struktura zwracanego slownika:**

| Klucz | Typ | Opis |
|-------|-----|------|
| `nazwa` | `str` | `"Wektoryzowane (N krokow)"` |
| `liczba_krokow` | `int` | Liczba krokow |
| `powtorzenia` | `int` | Liczba powtorzen pomiaru (stale: 50) |
| `min_ms` | `float` | Najkrotszy czas [ms] |
| `max_ms` | `float` | Najdluzszy czas [ms] |
| `srednia_ms` | `float` | Sredni czas laczny [ms] |
| `mediana_ms` | `float` | Mediana czasu lacznego [ms] |
| `czas_na_krok_ms` | `float` | Sredni czas na jeden krok [ms] |

**Algorytm krok po kroku:**

1. Tworzy obiekt `SkyCoord` dla Vegi.
2. Przygotowuje tablice czasow (`liczba_krokow` punktow co 1 sekunde) za pomoca numpy.
3. Wylacza garbage collector.
4. Powtarza pomiar 50 razy dla dokladnosci:
   a. Tworzy ramke `AltAz` z tablica czasow.
   b. Mierzy czas transformacji.
5. Wlacza garbage collector.
6. Oblicza statystyki, w tym czas na jeden krok (`srednia / liczba_krokow`).

**Dlaczego wektoryzacja jest szybsza:** Astropy potrafi obliczyc transformacje dla tablicy czasow jednoczesnie, unikajac narzutu petli Pythona i wykorzystujac operacje numpy.

**Przyklad uzycia:**
```python
wyniki = benchmark_wektoryzowana(100)
print(f"Czas na krok: {wyniki['czas_na_krok_ms']:.3f} ms")
```

---

#### `benchmark_symulacja_sledzenia(czas_trwania_min, interwal_s, verbose)`

Mierzy czas pelnej symulacji sledzenia (porownanie petli vs wektoryzacji).

**Sygnatura:**
```python
def benchmark_symulacja_sledzenia(
    czas_trwania_min: int = 30,
    interwal_s: int = 1,
    verbose: bool = False,
) -> dict
```

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `czas_trwania_min` | `int` | `30` | Czas trwania symulowanej sesji [min] |
| `interwal_s` | `int` | `1` | Interwal sledzenia [s] |
| `verbose` | `bool` | `False` | Czy wyswietlac szczegoly |

**Typ zwracany:** `dict` -- slownik z wynikami pomiaru

**Struktura zwracanego slownika:**

| Klucz | Typ | Opis |
|-------|-----|------|
| `nazwa` | `str` | `"Symulacja N min / Xs"` |
| `liczba_krokow` | `int` | Laczna liczba krokow |
| `petla_ms` | `float` | Czas metody petlowej [ms] |
| `petla_na_krok_ms` | `float` | Czas na krok w petli [ms] |
| `wektoryzowane_ms` | `float` | Czas metody wektoryzowanej [ms] |
| `wektoryzowane_na_krok_ms` | `float` | Czas na krok wektoryzowany [ms] |
| `przyspieszenie` | `float` | Wspolczynnik przyspieszenia (B vs A) |

**Algorytm krok po kroku:**

1. Oblicza liczbe krokow: `(czas_trwania_min * 60) / interwal_s`.
2. **Metoda A (petla po pojedynczych):**
   a. Wylacza GC.
   b. Iteruje po kazdym kroku, tworzac ramke `AltAz` i wykonujac transformacje.
   c. Mierzy laczny czas.
3. **Metoda B (wektoryzowane):**
   a. Tworzy tablice czasow za pomoca numpy.
   b. Wykonuje jedna transformacje dla calej tablicy.
   c. Mierzy laczny czas.
4. Oblicza wspolczynnik przyspieszenia: `czas_A / czas_B`.

**Przyklad uzycia:**
```python
wyniki = benchmark_symulacja_sledzenia(30, 1)
print(f"Petla: {wyniki['petla_ms']:.1f} ms")
print(f"Wektor: {wyniki['wektoryzowane_ms']:.1f} ms")
print(f"Przyspieszenie: {wyniki['przyspieszenie']:.1f}x")
```

---

#### `wyswietl_podsumowanie(wyniki)`

Wyswietla podsumowanie benchmarkow z rekomendacjami dla systemu SeeSky.

**Sygnatura:**
```python
def wyswietl_podsumowanie(wyniki: list[dict]) -> None
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `wyniki` | `list[dict]` | Lista slownikow z wynikami poszczegolnych benchmarkow |

**Typ zwracany:** `None`

**Algorytm krok po kroku:**

1. Wyswietla tabele ze wszystkimi wynikami benchmarkow.
2. Na podstawie sredniej z pojedynczej transformacji oblicza:
   a. **Szacunek dla Raspberry Pi 4:** srednia * 7.5 (RPi4 jest ok. 5-10x wolniejsze).
   b. **Szacunek dla Raspberry Pi 5:** srednia * 7.5 * 0.6 (RPi5 jest ok. 40% szybsze od RPi4).
3. Generuje rekomendacje interwalow sledzenia:
   - PC: 0.5 - 1.0 s
   - Raspberry Pi 4: 1.0 - 2.0 s
   - Raspberry Pi 5: 0.5 - 1.0 s
4. Wyswietla tabele ruchu obiektow na niebie dla roznych interwalow (0.5s, 1s, 2s, 5s, 10s):
   - Predkosc obrotu Ziemi: 15"/s = 0.00417 stopnia/s
   - Przesuniecie celu w kazdym interwale
5. Formuje wnioski:
   - Interwal 1-2s jest optymalny dla radioteleskopow amatorskich
   - Przesuniecie 15-30" jest akceptowalne dla wiazki > 1 stopnia
   - Wektoryzacja przyspiesza obliczenia, ale wymaga wiecej RAM
   - Na Raspberry Pi zalecane jest uzycie cache

---

#### `main()`

Glowna funkcja skryptu -- parsuje argumenty wiersza polecen i uruchamia benchmarki.

**Sygnatura:**
```python
def main() -> None
```

**Typ zwracany:** `None`

**Argumenty wiersza polecen (argparse):**

| Argument | Skrot | Typ | Domyslna | Opis |
|----------|-------|-----|----------|------|
| `--iterations` | -- | `int` | `1000` | Liczba iteracji pojedynczej transformacji |
| `--vectorized-steps` | -- | `int` | `100` | Liczba krokow wektoryzowanego benchmarku |
| `--duration` | -- | `int` | `30` | Czas trwania symulacji sledzenia [min] |
| `--interval` | -- | `int` | `1` | Interwal sledzenia w symulacji [s] |
| `--verbose` | `-v` | `bool` | `False` | Wyswietlaj szczegolowe informacje |

**Algorytm krok po kroku:**

1. Parsuje argumenty wiersza polecen.
2. Wyswietla informacje o celu testowym, lokalizacji i platformie.
3. Wyswietla wersje bibliotek: Python, astropy, NumPy.
4. Wykonuje rozgrzewke (`rozgrzewka`).
5. Uruchamia 3 benchmarki sekwencyjnie:
   a. Pojedyncza transformacja (`benchmark_pojedyncza_transformacja`)
   b. Wektoryzowane obliczenie (`benchmark_wektoryzowana`)
   c. Symulacja sledzenia (`benchmark_symulacja_sledzenia`)
6. Wyswietla podsumowanie z rekomendacjami (`wyswietl_podsumowanie`).

**Przyklady uzycia z wiersza polecen:**

```bash
# Benchmark z domyslnymi ustawieniami (1000 iteracji)
python benchmark_astropy.py

# Benchmark z wieksza liczba iteracji i szczegolami
python benchmark_astropy.py --iterations 500 --verbose

# Symulacja dluzszej sesji z innym interwalem
python benchmark_astropy.py --duration 60 --interval 2

# Wiecej krokow wektoryzowanych
python benchmark_astropy.py --vectorized-steps 500
```

---

## Zaleznosci miedzy skryptami

Ponizszy diagram pokazuje zalenosci i kolejnosc uruchamiania skryptow:

```
download_hyg.py  --->  parse_catalog.py  --->  [baza star_catalog.db gotowa]
   (pobiera CSV)       (CSV -> SQLite)

test_position.py           -- niezalezny, uzywa wbudowanego slownika gwiazd
test_tracking_loop.py      -- niezalezny, uzywa wbudowanego slownika gwiazd
benchmark_astropy.py       -- niezalezny, uzywa stalych (Vega)
```

### Typowy przebieg pracy

```bash
# 1. Pobranie katalogu gwiazd
python scripts/download_hyg.py

# 2. Parsowanie katalogu do bazy SQLite
python scripts/parse_catalog.py

# 3. Sprawdzenie wydajnosci na danym komputerze
python scripts/benchmark_astropy.py

# 4. Test obliczen pozycji dla wybranej gwiazdy
python scripts/test_position.py --name Vega

# 5. Symulacja sledzenia
python scripts/test_tracking_loop.py --name Vega --duration 120 --interval 2
```

---

## Wymagania systemowe

### Python

- Python 3.10+ (wymagany dla skladni `float | None`)

### Biblioteki zewnetrzne

| Biblioteka | Wymagana przez | Cel |
|------------|---------------|-----|
| `astropy` | test_position.py, test_tracking_loop.py, benchmark_astropy.py | Transformacje wspolrzednych astronomicznych |
| `numpy` | test_position.py, test_tracking_loop.py, benchmark_astropy.py | Obliczenia numeryczne |

### Instalacja

```bash
pip install astropy numpy
```

Skrypty `download_hyg.py` i `parse_catalog.py` nie wymagaja bibliotek zewnetrznych -- korzystaja wylacznie z biblioteki standardowej Pythona.
