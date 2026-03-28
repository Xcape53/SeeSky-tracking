# Konfiguracja i baza danych -- dokumentacja backendu SeeSky

> Wersja dokumentu: 1.0 | Data: 2026-03-27
> Projekt studencki SeeSky -- modul sledzenia obiektow niebieskich

---

## Spis tresci

1. [Wprowadzenie](#1-wprowadzenie)
2. [Modul konfiguracji (`config.py`)](#2-modul-konfiguracji-configpy)
   - [Sciezki projektu](#21-sciezki-projektu)
   - [Konfiguracja serwera Flask](#22-konfiguracja-serwera-flask)
   - [Uwierzytelnianie JWT](#23-uwierzytelnianie-jwt)
   - [Domyslne konto operatora](#24-domyslne-konto-operatora)
   - [Lokalizacja obserwatora](#25-lokalizacja-obserwatora)
   - [Parametry trackingu](#26-parametry-trackingu)
   - [Parametry atmosferyczne](#27-parametry-atmosferyczne)
   - [Zmienne srodowiskowe -- podsumowanie](#28-zmienne-srodowiskowe--podsumowanie)
3. [Warstwa bazy danych (`database/models.py`)](#3-warstwa-bazy-danych-databasemodelspy)
   - [Schemat tabel](#31-schemat-tabel)
   - [Funkcje pomocnicze](#32-funkcje-pomocnicze)
   - [Konfiguracja teleskopu](#33-konfiguracja-teleskopu)
   - [Katalog gwiazd](#34-katalog-gwiazd)
   - [Kolejka obserwacji](#35-kolejka-obserwacji)
   - [Kalibracja](#36-kalibracja)
4. [Zaleznosci miedzy modulami](#4-zaleznosci-miedzy-modulami)
5. [Uwagi dotyczace bezpieczenstwa](#5-uwagi-dotyczace-bezpieczenstwa)

---

## 1. Wprowadzenie

Niniejszy dokument opisuje dwa fundamentalne pliki backendu systemu SeeSky:

- **`backend/config.py`** -- centralny modul konfiguracyjny przechowujacy stale i wartosci domyslne calej aplikacji.
- **`backend/database/models.py`** -- warstwa dostepu do bazy danych SQLite, odpowiedzialna za operacje CRUD na katalogu gwiazd, kolejce obserwacji i konfiguracji teleskopu.

Oba pliki stanowia fundament, na ktorym opieraja sie pozostale komponenty backendu (API REST, silnik trackingowy, modul kalibracji). Kazdy endpoint API ostatecznie deleguje operacje na danych do funkcji zdefiniowanych w `models.py`, a te z kolei korzystaja ze stalych z `config.py`.

**Sciezki plikow wzgledem katalogu projektu:**

```
tracking/
  backend/
    config.py                  <-- modul konfiguracji
    database/
      models.py                <-- warstwa bazy danych
      star_catalog.db           <-- plik bazy SQLite
```

---

## 2. Modul konfiguracji (`config.py`)

Plik `backend/config.py` pelni role jedynego zrodla prawdy dla wartosci konfiguracyjnych calej aplikacji. Zamiast rozpraszac stale po wielu plikach, wszystkie parametry sa zgromadzone w jednym miejscu. Czesc z nich moze byc nadpisana przez zmienne srodowiskowe, co pozwala dostosowac dzialanie aplikacji bez modyfikowania kodu zrodlowego (np. na serwerze produkcyjnym).

### Importy

```python
import os
from pathlib import Path
```

Modul korzysta z biblioteki standardowej Pythona: `os` do odczytu zmiennych srodowiskowych oraz `pathlib.Path` do budowania sciezek niezaleznych od systemu operacyjnego.

---

### 2.1 Sciezki projektu

```python
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = str(BASE_DIR / "database" / "star_catalog.db")
```

| Stala | Typ | Wartosc | Opis |
|-------|-----|---------|------|
| `BASE_DIR` | `Path` | Katalog, w ktorym znajduje sie `config.py` (tj. `backend/`) | Bazowy katalog backendu. Obliczany dynamicznie na podstawie lokalizacji pliku `config.py`. Dzieki uzyciu `resolve()` sciezka jest zawsze absolutna, co eliminuje problemy ze sciezkami relatywnymi. |
| `DATABASE_PATH` | `str` | `backend/database/star_catalog.db` | Pelna sciezka do pliku bazy danych SQLite. Konwertowana na `str`, poniewaz modul `sqlite3` nie akceptuje obiektow `Path`. |

**Dlaczego uzywamy `Path(__file__).resolve().parent`?**

Dzieki temu sciezka jest poprawna niezaleznie od tego, z jakiego katalogu uruchomiono skrypt Pythona. Na Raspberry Pi, gdzie aplikacja moze byc uruchamiana jako usluga systemd z dowolnym katalogiem roboczym, jest to szczegolnie istotne.

---

### 2.2 Konfiguracja serwera Flask

```python
FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
```

| Stala | Typ | Wartosc domyslna | Zmienna srodowiskowa | Opis |
|-------|-----|-------------------|----------------------|------|
| `FLASK_HOST` | `str` | `"0.0.0.0"` | `FLASK_HOST` | Adres, na ktorym nasuchuje serwer Flask. Wartosc `0.0.0.0` oznacza nasluchiwanie na wszystkich interfejsach sieciowych -- niezbedne, aby frontend na Node.js mogl komunikowac sie z backendem oraz aby uzytkownik mogl laczyc sie z Raspberry Pi z innego komputera w sieci lokalnej. |
| `FLASK_PORT` | `int` | `5000` | `FLASK_PORT` | Port serwera Flask. Frontend Node.js komunikuje sie z backendem na tym porcie. Wartosc jest konwertowana na `int` przez `int()`, poniewaz `os.environ.get()` zawsze zwraca `str`. |
| `FLASK_DEBUG` | `bool` | `False` | `FLASK_DEBUG` | Tryb debugowania Flask. Wartosc `true` (wielkimi lub malymi literami) wlacza automatyczne przeladowywanie kodu i szczegolowe komunikaty bledow. **Uwaga:** nigdy nie nalezy wlaczac tego trybu na produkcji, poniewaz ujawnia on wewnetrzne sciezki i szczegoly implementacji. |

**Sposob parsowania `FLASK_DEBUG`:**

Wartosc zmiennej srodowiskowej jest konwertowana do malych liter (`.lower()`) i porownywana z `"true"`. Kazda inna wartosc (np. `"false"`, `"0"`, `"no"`, pustka) skutkuje wartoscia `False`.

---

### 2.3 Uwierzytelnianie JWT

```python
SECRET_KEY = os.environ.get("SECRET_KEY", "seesky-dev-secret-change-in-production")
JWT_EXPIRATION_SECONDS = 3600
```

| Stala | Typ | Wartosc domyslna | Zmienna srodowiskowa | Opis |
|-------|-----|-------------------|----------------------|------|
| `SECRET_KEY` | `str` | `"seesky-dev-secret-change-in-production"` | `SECRET_KEY` | Klucz tajny uzywany do podpisywania i weryfikowania tokenow JWT. Domyslna wartosc jest przeznaczona wylacznie do celow deweloperskich. **W srodowisku produkcyjnym nalezy bezwzglednie ustawic zmienna srodowiskowa `SECRET_KEY` na dlugi, losowy ciag znakow.** |
| `JWT_EXPIRATION_SECONDS` | `int` | `3600` | -- | Czas waznosci tokena JWT wyrazony w sekundach. Wartosc `3600` odpowiada jednej godzinie. Po uplywie tego czasu operator musi zalogowac sie ponownie. Stala nie jest konfigurowalna przez zmienna srodowiskowa. |

---

### 2.4 Domyslne konto operatora

```python
DEFAULT_USERNAME = os.environ.get("SEESKY_USER", "operator")
DEFAULT_PASSWORD = os.environ.get("SEESKY_PASS", "seesky123")
```

| Stala | Typ | Wartosc domyslna | Zmienna srodowiskowa | Opis |
|-------|-----|-------------------|----------------------|------|
| `DEFAULT_USERNAME` | `str` | `"operator"` | `SEESKY_USER` | Nazwa uzytkownika dla jedynego konta w systemie. SeeSky nie posiada modulu rejestracji -- uwierzytelnienie polega na porownaniu danych logowania z tymi stalymi. |
| `DEFAULT_PASSWORD` | `str` | `"seesky123"` | `SEESKY_PASS` | Haslo operatora. **Domyslne haslo jest slabe i nalezy je zmienic na produkcji** poprzez ustawienie zmiennej `SEESKY_PASS`. |

**Uwaga bezpieczenstwa:** System nie przechowuje hasel w bazie danych ani nie hashuje ich -- porownanie odbywa sie bezposrednio ze stalymi. Jest to uproszczenie stosowne dla prototypu studenckiego dzialajacego w izolowanej sieci lokalnej.

---

### 2.5 Lokalizacja obserwatora

```python
DEFAULT_LATITUDE = 51.1079
DEFAULT_LONGITUDE = 17.0385
DEFAULT_ALTITUDE = 120.0  # metry n.p.m.
```

| Stala | Typ | Wartosc domyslna | Jednostka | Opis |
|-------|-----|-------------------|-----------|------|
| `DEFAULT_LATITUDE` | `float` | `51.1079` | stopnie (N+) | Szerokosc geograficzna obserwatora. Wartosc domyslna odpowiada Wroclawowi. Uzywana przy inicjalizacji tabeli `telescope_config` w bazie danych. |
| `DEFAULT_LONGITUDE` | `float` | `17.0385` | stopnie (E+) | Dlugosc geograficzna obserwatora. Wartosc domyslna odpowiada Wroclawowi. |
| `DEFAULT_ALTITUDE` | `float` | `120.0` | metry n.p.m. | Wysokosc obserwatora nad poziomem morza. Wplywa na obliczenia refrakcji atmosferycznej i paralaksy. |

Te wartosci sa uzywane jako domyslne przy pierwszym uruchomieniu systemu (patrz `init_db()` w `models.py`). Operator moze je pozniej zmienic przez interfejs webowy lub API -- wtedy nowe wartosci trafiaja do tabeli `telescope_config`.

---

### 2.6 Parametry trackingu

```python
TRACKING_INTERVAL_SECONDS = 2.0
DEFAULT_OBSERVATION_DURATION_MINUTES = 30
```

| Stala | Typ | Wartosc domyslna | Jednostka | Opis |
|-------|-----|-------------------|-----------|------|
| `TRACKING_INTERVAL_SECONDS` | `float` | `2.0` | sekundy | Interwal petli trackingowej -- co ile sekund system przelicza pozycje obserwowanego obiektu i wysyla komendy do silnikow krokowych. Wartosc 2 sekundy stanowi kompromis miedzy dokladnoscia sledzenia a obciazeniem procesora Raspberry Pi. |
| `DEFAULT_OBSERVATION_DURATION_MINUTES` | `int` | `30` | minuty | Domyslny czas trwania obserwacji, jesli operator nie poda innej wartosci przy dodawaniu obserwacji do kolejki. |

---

### 2.7 Parametry atmosferyczne

```python
DEFAULT_PRESSURE = 1013.25      # hPa
DEFAULT_TEMPERATURE = 10.0      # Celsius
DEFAULT_HUMIDITY = 0.5          # 0-1
DEFAULT_WAVELENGTH = 210000.0   # nm (~21cm linia wodoru HI)
```

| Stala | Typ | Wartosc domyslna | Jednostka | Opis |
|-------|-----|-------------------|-----------|------|
| `DEFAULT_PRESSURE` | `float` | `1013.25` | hPa | Cisnienie atmosferyczne na poziomie obserwatora. Wartosc domyslna to standardowe cisnienie atmosferyczne na poziomie morza. Uzywana do korekcji refrakcji atmosferycznej w obliczeniach pozycji. |
| `DEFAULT_TEMPERATURE` | `float` | `10.0` | Celsius | Temperatura powietrza. Wplywa na gestosc atmosfery i wielkosc refrakcji. |
| `DEFAULT_HUMIDITY` | `float` | `0.5` | 0-1 (wzgledna) | Wilgotnosc wzgledna powietrza. Wartosc `0.5` oznacza 50%. |
| `DEFAULT_WAVELENGTH` | `float` | `210000.0` | nanometry | Dlugosc fali obserwacyjnej. Wartosc domyslna `210000 nm` odpowiada linii wodoru HI o dlugosci 21 cm -- podstawowej czestotliwosci obserwowanej przez radioteleskopy. Dlugosc fali jest istotna, poniewaz refrakcja atmosferyczna zalezy od dlugosci fali promieniowania. |

**Dlaczego te parametry sa wazne?**

Refrakcja atmosferyczna powoduje, ze obserwowany obiekt wydaje sie byc wyzej nad horyzontem, niz jest w rzeczywistosci. Efekt ten jest szczegolnie silny przy niskich elewacjach (blisko horyzontu). Silnik trackingowy korzysta z tych parametrow, aby kompensowac refrakcje i celowac teleskop w rzeczywista pozycje obiektu, a nie w jego pozorna pozycje.

---

### 2.8 Zmienne srodowiskowe -- podsumowanie

Ponizej znajduje sie zbiorczy wykaz wszystkich zmiennych srodowiskowych obslugiwanych przez `config.py`:

| Zmienna srodowiskowa | Stala w kodzie | Wartosc domyslna | Opis |
|-----------------------|----------------|-------------------|------|
| `FLASK_HOST` | `FLASK_HOST` | `"0.0.0.0"` | Adres nasluchiwania serwera |
| `FLASK_PORT` | `FLASK_PORT` | `5000` | Port serwera |
| `FLASK_DEBUG` | `FLASK_DEBUG` | `False` | Tryb debugowania |
| `SECRET_KEY` | `SECRET_KEY` | `"seesky-dev-..."` | Klucz JWT |
| `SEESKY_USER` | `DEFAULT_USERNAME` | `"operator"` | Login operatora |
| `SEESKY_PASS` | `DEFAULT_PASSWORD` | `"seesky123"` | Haslo operatora |

**Przyklad ustawienia zmiennych srodowiskowych na Raspberry Pi (bash):**

```bash
export SECRET_KEY="moj-bardzo-tajny-klucz-produkcyjny-2026"
export SEESKY_USER="admin"
export SEESKY_PASS="silne-haslo-obserwatorium"
export FLASK_DEBUG="false"
```

Mozna tez umiescic je w pliku `.env` w katalogu projektu lub w konfiguracji uslugi `systemd`.

---

## 3. Warstwa bazy danych (`database/models.py`)

Plik `backend/database/models.py` stanowi warstwe dostepu do bazy danych (ang. _Data Access Layer_). Hermetyzuje wszystkie zapytania SQL, udostepniajac reszcie aplikacji zestaw funkcji Pythona o czytelnych nazwach i typowanych sygnaturach.

### Importy

```python
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

import config
```

- `sqlite3` -- wbudowany modul Pythona do obslugi baz danych SQLite.
- `datetime`, `timezone` -- do generowania znacznikow czasowych w formacie ISO 8601 (UTC).
- `config` -- modul konfiguracyjny opisany powyzej (uzywa `config.DATABASE_PATH`).

---

### 3.1 Schemat tabel

Baza danych `star_catalog.db` zawiera trzy tabele. Tabela `stars` jest tworzona zewnetrznie (przez skrypt importu katalogu HYG), natomiast tabele `telescope_config` i `observations` sa tworzone przez funkcje `init_db()`.

#### Tabela `telescope_config`

Przechowuje pojedynczy wiersz (id=1) z konfiguracja teleskopu. Ograniczenie `CHECK (id = 1)` gwarantuje, ze nigdy nie powstanie wiecej niz jeden rekord konfiguracyjny.

| Kolumna | Typ | Domyslna | Opis |
|---------|-----|----------|------|
| `id` | `INTEGER PRIMARY KEY` | `1` (jedyna dozwolona wartosc) | Identyfikator wiersza. Ograniczenie `CHECK (id = 1)` zapewnia, ze istnieje dokladnie jeden rekord. |
| `latitude` | `REAL NOT NULL` | `51.1079` | Szerokosc geograficzna obserwatora [stopnie]. |
| `longitude` | `REAL NOT NULL` | `17.0385` | Dlugosc geograficzna obserwatora [stopnie]. |
| `altitude` | `REAL NOT NULL` | `120.0` | Wysokosc n.p.m. [metry]. |
| `tracking_interval_seconds` | `REAL NOT NULL` | `2.0` | Interwal petli trackingowej [sekundy]. |
| `default_observation_duration_minutes` | `INTEGER NOT NULL` | `30` | Domyslny czas obserwacji [minuty]. |
| `pressure` | `REAL NOT NULL` | `1013.25` | Cisnienie atmosferyczne [hPa]. |
| `temperature` | `REAL NOT NULL` | `10.0` | Temperatura [Celsius]. |
| `humidity` | `REAL NOT NULL` | `0.5` | Wilgotnosc wzgledna [0-1]. |
| `wavelength` | `REAL NOT NULL` | `210000.0` | Dlugosc fali obserwacyjnej [nm]. |
| `calibration_offset_az` | `REAL NOT NULL` | `0.0` | Offset kalibracyjny azymutu [stopnie]. |
| `calibration_offset_alt` | `REAL NOT NULL` | `0.0` | Offset kalibracyjny elewacji [stopnie]. |
| `is_calibrated` | `INTEGER NOT NULL` | `0` | Flaga: `0` = nieskalibrowany, `1` = skalibrowany. |
| `last_calibration_time` | `TEXT` | `NULL` | Data/czas ostatniej kalibracji (ISO 8601, UTC). Wartosc `NULL` oznacza brak kalibracji. |

#### Tabela `observations`

Przechowuje kolejke obserwacji -- zarowno oczekujace, jak i zakonczone.

| Kolumna | Typ | Domyslna | Opis |
|---------|-----|----------|------|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | -- | Unikalny identyfikator obserwacji, nadawany automatycznie. |
| `star_id` | `INTEGER NOT NULL` | -- | Klucz obcy do tabeli `stars`. Wskazuje obserwowana gwiazde. |
| `duration_minutes` | `INTEGER NOT NULL` | `30` | Planowany czas trwania obserwacji [minuty]. |
| `priority` | `INTEGER NOT NULL` | `0` | Priorytet obserwacji. Wyzsza wartosc = wyzszy priorytet. Obserwacje o wyzszym priorytecie sa pobierane z kolejki jako pierwsze. |
| `status` | `TEXT NOT NULL` | `'waiting'` | Status obserwacji. Dopuszczalne wartosci: `'waiting'`, `'tracking'`, `'completed'`, `'stopped'`. |
| `position_in_queue` | `INTEGER` | `NULL` | Pozycja w kolejce (rezerwowa, obecnie nieuzywana -- kolejnosc wynika z sortowania). |
| `created_at` | `TEXT NOT NULL` | -- | Data/czas utworzenia obserwacji (ISO 8601, UTC). Ustawiana przy dodawaniu. |
| `started_at` | `TEXT` | `NULL` | Data/czas rozpoczecia sledzenia. Ustawiana przy zmianie statusu na `'tracking'`. |
| `finished_at` | `TEXT` | `NULL` | Data/czas zakonczenia. Ustawiana przy zmianie statusu na `'completed'` lub `'stopped'`. |

**Klucz obcy:** `FOREIGN KEY (star_id) REFERENCES stars(id)` -- obserwacja musi wskazywac istniejaca gwiazde w katalogu.

**Cykl zycia obserwacji:**

```
waiting  -->  tracking  -->  completed
                 |
                 +-------->  stopped
```

#### Tabela `stars`

Tabela katalogu gwiazd -- tworzona i wypelniana zewnetrznie przez skrypt importujacy dane z katalogu HYG (HYG Database v3).

| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | `INTEGER PRIMARY KEY` | Wewnetrzny identyfikator w bazie SeeSky. |
| `hyg_id` | `INTEGER` | Identyfikator z katalogu HYG. |
| `proper_name` | `TEXT` | Nazwa wlasna gwiazdy (np. "Sirius", "Vega"). Moze byc `NULL` dla gwiazd bez nazwy wlasnej. |
| `ra` | `REAL` | Rektascensja [godziny, 0-24]. |
| `dec` | `REAL` | Deklinacja [stopnie, -90 do +90]. |
| `magnitude` | `REAL` | Jasnosc obserwowana (magnitudo wizualne). |
| `abs_magnitude` | `REAL` | Jasnosc absolutna. |
| `spectral_type` | `TEXT` | Typ widmowy (np. "G2V", "A1V"). |
| `constellation` | `TEXT` | Skrot konstelacji (np. "Ori", "UMa"). |
| `distance_ly` | `REAL` | Odleglosc w latach swietlnych. |
| `color_index` | `REAL` | Indeks barwy (B-V). |

---

### 3.2 Funkcje pomocnicze

#### `get_db()`

```python
def get_db() -> sqlite3.Connection
```

**Opis:** Tworzy i zwraca nowe polaczenie z baza danych SQLite. Ustawia `row_factory` na `sqlite3.Row`, co pozwala odwolywac sie do kolumn wynikow po nazwie (np. `row["latitude"]`) zamiast po indeksie numerycznym.

**Parametry:** Brak.

**Zwraca:** `sqlite3.Connection` -- obiekt polaczenia z baza danych z ustawionym `row_factory`.

**Dzialanie krok po kroku:**

1. Otwiera polaczenie do bazy danych wskazywanej przez `config.DATABASE_PATH`.
2. Ustawia `conn.row_factory = sqlite3.Row`, dzieki czemu kazdy wiersz wynikowy zachowuje sie jak slownik (z dostepem po nazwie kolumny).
3. Zwraca obiekt polaczenia.

**Uwaga:** Funkcja tworzy **nowe polaczenie** przy kazdym wywolaniu. Wywolujacy jest odpowiedzialny za zamkniecie polaczenia (wywolanie `conn.close()`) po zakonczeniu operacji. Brak puli polaczen jest swiadomym uproszczeniem -- SQLite dobrze radzi sobie z wieloma krotkimi polaczeniami w systemach o niskim obciazeniu.

**Przyklad uzycia:**

```python
conn = get_db()
row = conn.execute("SELECT * FROM stars WHERE id = 1").fetchone()
print(row["proper_name"])
conn.close()
```

---

#### `init_db()`

```python
def init_db() -> None
```

**Opis:** Inicjalizuje baze danych -- tworzy tabele `telescope_config` i `observations`, jesli jeszcze nie istnieja, oraz wstawia domyslny wiersz konfiguracyjny.

**Parametry:** Brak.

**Zwraca:** `None`.

**Dzialanie krok po kroku:**

1. Uzyskuje polaczenie do bazy danych przez `get_db()`.
2. Wykonuje `CREATE TABLE IF NOT EXISTS telescope_config (...)` -- tworzy tabele konfiguracji z ograniczeniem `CHECK (id = 1)` i wartosciami domyslnymi dla kazdej kolumny.
3. Wykonuje `CREATE TABLE IF NOT EXISTS observations (...)` -- tworzy tabele kolejki obserwacji z kluczem obcym do tabeli `stars`.
4. Sprawdza, czy tabela `telescope_config` jest pusta (`SELECT COUNT(*)`).
5. Jesli tabela jest pusta, wstawia domyslny wiersz konfiguracyjny z wartosciami `config.DEFAULT_LATITUDE`, `config.DEFAULT_LONGITUDE` i `config.DEFAULT_ALTITUDE`. Pozostale kolumny przyjmuja wartosci `DEFAULT` zdefiniowane w schemacie tabeli.
6. Zatwierdza transakcje (`conn.commit()`) i zamyka polaczenie.

**Kiedy wywolywac:** Funkcja jest wywolywana raz, przy starcie aplikacji (w `app.py`). Dzieki uzyciu `IF NOT EXISTS` jest idempotentna -- wielokrotne wywolania nie powoduja bledow ani duplikacji danych.

**Przypadki brzegowe:**

- Jesli tabela `stars` nie istnieje, tworzenie tabeli `observations` z kluczem obcym do `stars` nie spowoduje bledu (SQLite domyslnie nie wymusza integralnosci kluczy obcych, chyba ze wlaczono `PRAGMA foreign_keys = ON`).
- Jesli wiersz konfiguracyjny juz istnieje, krok 5 jest pomijany -- istniejaca konfiguracja nie jest nadpisywana.

---

### 3.3 Konfiguracja teleskopu

#### `get_config()`

```python
def get_config() -> dict
```

**Opis:** Pobiera biezaca konfiguracje teleskopu z tabeli `telescope_config`.

**Parametry:** Brak.

**Zwraca:** `dict` -- slownik zawierajacy wszystkie kolumny tabeli `telescope_config` (np. `latitude`, `longitude`, `altitude`, `calibration_offset_az` itd.). Zwraca pusty slownik `{}`, jesli wiersz konfiguracyjny nie istnieje (co w praktyce nie powinno miec miejsca po wywolaniu `init_db()`).

**Dzialanie krok po kroku:**

1. Otwiera polaczenie do bazy danych.
2. Wykonuje `SELECT * FROM telescope_config WHERE id = 1` i pobiera jeden wiersz.
3. Zamyka polaczenie.
4. Jesli wiersz nie istnieje, zwraca pusty slownik `{}`.
5. W przeciwnym razie konwertuje `sqlite3.Row` na zwykly slownik (`dict(row)`) i zwraca go.

**Przyklad zwracanej wartosci:**

```python
{
    "id": 1,
    "latitude": 51.1079,
    "longitude": 17.0385,
    "altitude": 120.0,
    "tracking_interval_seconds": 2.0,
    "default_observation_duration_minutes": 30,
    "pressure": 1013.25,
    "temperature": 10.0,
    "humidity": 0.5,
    "wavelength": 210000.0,
    "calibration_offset_az": 0.0,
    "calibration_offset_alt": 0.0,
    "is_calibrated": 0,
    "last_calibration_time": null
}
```

---

#### `update_config()`

```python
def update_config(data: dict) -> dict
```

**Opis:** Aktualizuje wybrane pola konfiguracji teleskopu. Akceptuje tylko pola z listy dozwolonych -- pola kalibracyjne i systemowe nie moga byc zmienione ta funkcja.

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `data` | `dict` | Slownik z polami do aktualizacji. Klucze to nazwy kolumn, wartosci to nowe wartosci. |

**Dozwolone pola (whitelist):**

- `latitude` -- szerokosc geograficzna
- `longitude` -- dlugosc geograficzna
- `altitude` -- wysokosc n.p.m.
- `tracking_interval_seconds` -- interwal trackingu
- `default_observation_duration_minutes` -- domyslny czas obserwacji
- `pressure` -- cisnienie atmosferyczne
- `temperature` -- temperatura
- `humidity` -- wilgotnosc
- `wavelength` -- dlugosc fali

**Pola, ktore NIE moga byc zmienione ta funkcja:** `id`, `calibration_offset_az`, `calibration_offset_alt`, `is_calibrated`, `last_calibration_time`. Do modyfikacji pol kalibracyjnych sluza dedykowane funkcje `update_calibration()` i `reset_calibration()`.

**Zwraca:** `dict` -- zaktualizowana konfiguracja (wynik `get_config()`).

**Dzialanie krok po kroku:**

1. Definiuje liste dozwolonych pol (`allowed`).
2. Filtruje slownik wejsciowy, pozostawiajac tylko pola z listy dozwolonych.
3. Jesli po filtrowaniu nie ma zadnych pol do aktualizacji, zwraca biezaca konfiguracje bez zmian.
4. Buduje dynamicznie klauzule `SET` zapytania SQL (np. `latitude = ?, longitude = ?`).
5. Wykonuje `UPDATE telescope_config SET ... WHERE id = 1` z parametryzowanym zapytaniem.
6. Zatwierdza transakcje i zamyka polaczenie.
7. Wywoluje `get_config()`, aby zwrocic pelna, zaktualizowana konfiguracje.

**Przypadki brzegowe:**

- Jesli `data` zawiera nieznane klucze (np. `{"foo": "bar"}`), sa one po cichu ignorowane -- funkcja nie zglasza bledu.
- Jesli `data` jest pustym slownikiem, funkcja zwraca biezaca konfiguracje bez wykonywania UPDATE.
- Brak walidacji typow ani zakresow wartosci -- warstwa API powinna walidowac dane przed wywolaniem tej funkcji.

**Przyklad uzycia:**

```python
updated = update_config({
    "latitude": 52.2297,
    "longitude": 21.0122,
    "altitude": 100.0,
    "foo": "bar"  # zostanie zignorowane
})
```

---

### 3.4 Katalog gwiazd

#### `get_stars()`

```python
def get_stars(
    page: int = 1,
    per_page: int = 20,
    search: str = None,
    min_mag: float = None,
    max_mag: float = None,
    constellation: str = None
) -> dict
```

**Opis:** Pobiera liste gwiazd z katalogu z obsluga filtrowania i paginacji. Wyniki sa sortowane tak, aby gwiazdy z nazwa wlasna pojawialy sie przed gwiazdami bez nazwy, a w obrebie kazdej grupy -- wedlug jasnosci (od najjasniejszych).

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `page` | `int` | `1` | Numer strony (liczony od 1). |
| `per_page` | `int` | `20` | Liczba wynikow na strone. |
| `search` | `str` | `None` | Fraza wyszukiwania. Filtruje gwiazdy, ktorych `proper_name` zawiera podany ciag (wyszukiwanie `LIKE %...%`, wielkosci liter nie sa rozrozniane przez SQLite domyslnie). |
| `min_mag` | `float` | `None` | Minimalna jasnosc (magnitudo). Filtruje: `magnitude >= min_mag`. |
| `max_mag` | `float` | `None` | Maksymalna jasnosc (magnitudo). Filtruje: `magnitude <= max_mag`. **Uwaga:** w astronomii nizsza wartosc magnitudo oznacza jasniejszy obiekt. |
| `constellation` | `str` | `None` | Skrot konstelacji (np. `"Ori"`). Filtruje dokladne dopasowanie: `constellation = ?`. |

**Zwraca:** `dict` o strukturze:

```python
{
    "stars": [
        {
            "id": 1,
            "name": "Sirius",          # proper_name (moze byc None)
            "constellation": "CMa",
            "magnitude": -1.46,
            "ra": 6.752,
            "dec": -16.716,
            "spectral_type": "A1V",
            "distance_ly": 8.6
        },
        # ...
    ],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 119614,               # calkowita liczba wynikow
        "total_pages": 5981
    }
}
```

**Dzialanie krok po kroku:**

1. Otwiera polaczenie do bazy danych.
2. Buduje dynamicznie klauzule `WHERE` na podstawie podanych filtrow. Kazdy filtr dodaje warunek do listy `where_clauses` i odpowiednia wartosc do listy `params`.
3. Jesli nie podano zadnych filtrow, uzywa `WHERE 1=1` (zawsze prawdziwe -- zwraca wszystkie gwiazdy).
4. Wykonuje `SELECT COUNT(*)` z tymi samymi warunkami, aby obliczyc calkowita liczbe wynikow (`total`).
5. Oblicza `offset = (page - 1) * per_page`.
6. Wykonuje glowne zapytanie `SELECT` z klauzula `ORDER BY`:
   - Gwiazdy z nazwa wlasna (`proper_name IS NOT NULL`) sa sortowane jako pierwsze (`CASE WHEN proper_name IS NOT NULL THEN 0 ELSE 1 END`).
   - W obrebie kazdej grupy sortowanie jest wedlug `magnitude` (rosnaco -- najjasniejsze najpierw).
7. Stosuje `LIMIT ? OFFSET ?` do paginacji.
8. Zamyka polaczenie.
9. Konwertuje wyniki na liste slownikow, mapujac kolumne `proper_name` na klucz `name`.
10. Oblicza `total_pages` uzywajac dzielenia calkowitego z zaokragleniem w gore: `max(1, (total + per_page - 1) // per_page)`.
11. Zwraca slownik z listami `stars` i `pagination`.

**Przypadki brzegowe:**

- Dla pustego katalogu zwraca `{"stars": [], "pagination": {"page": 1, "per_page": 20, "total": 0, "total_pages": 1}}`.
- `total_pages` wynosi co najmniej `1`, nawet gdy `total = 0`.
- Zapytanie `search` uzywa operatora `LIKE` z wildcardami `%` po obu stronach, wiec wyszukanie `"sir"` znajdzie `"Sirius"`.
- Gwiazdy bez nazwy wlasnej maja `name: null` w wyniku.

---

#### `get_star()`

```python
def get_star(star_id: int) -> dict | None
```

**Opis:** Pobiera szczegolowe informacje o pojedynczej gwieezdzie na podstawie jej wewnetrznego identyfikatora.

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `star_id` | `int` | Identyfikator gwiazdy w bazie danych (kolumna `id` tabeli `stars`). |

**Zwraca:** `dict | None`

- `dict` -- slownik ze wszystkimi kolumnami tabeli `stars` (wlacznie z `abs_magnitude`, `color_index` i innymi, ktore nie sa zwracane przez `get_stars()`), jesli gwiazda o podanym ID istnieje.
- `None` -- jesli gwiazda o podanym ID nie istnieje.

**Dzialanie krok po kroku:**

1. Otwiera polaczenie do bazy danych.
2. Wykonuje `SELECT * FROM stars WHERE id = ?` z parametryzowanym zapytaniem.
3. Pobiera jeden wiersz (`fetchone()`).
4. Zamyka polaczenie.
5. Jesli wiersz nie istnieje, zwraca `None`.
6. W przeciwnym razie konwertuje `sqlite3.Row` na `dict` i zwraca.

**Roznica wzgledem `get_stars()`:** Funkcja `get_star()` zwraca **wszystkie** kolumny tabeli (w tym `abs_magnitude`, `color_index`, `hyg_id`), natomiast `get_stars()` zwraca jedynie wybrane kolumny, mapujac `proper_name` na `name`.

**Przyklad zwracanej wartosci:**

```python
{
    "id": 32349,
    "hyg_id": 32349,
    "proper_name": "Sirius",
    "ra": 6.7525693,
    "dec": -16.7161,
    "magnitude": -1.46,
    "abs_magnitude": 1.43,
    "spectral_type": "A1V",
    "constellation": "CMa",
    "distance_ly": 8.6,
    "color_index": 0.009
}
```

---

### 3.5 Kolejka obserwacji

#### `get_queue()`

```python
def get_queue() -> list[dict]
```

**Opis:** Pobiera liste wszystkich oczekujacych obserwacji (status `'waiting'`), posortowanych wedlug priorytetu i czasu utworzenia.

**Parametry:** Brak.

**Zwraca:** `list[dict]` -- lista slownikow, gdzie kazdy slownik zawiera wszystkie kolumny tabeli `observations` plus dodatkowe pole `star_name` (nazwa wlasna gwiazdy z tabeli `stars`).

**Dzialanie krok po kroku:**

1. Otwiera polaczenie do bazy danych.
2. Wykonuje zapytanie z `LEFT JOIN` na tabeli `stars`, aby dolaczyc nazwe gwiazdy.
3. Filtruje wyniki: `WHERE o.status = 'waiting'`.
4. Sortuje wyniki: `ORDER BY o.priority DESC, o.created_at ASC` -- najpierw najwyzszy priorytet, a w przypadku rownego priorytetu -- najwczesniej dodane obserwacje.
5. Zamyka polaczenie.
6. Konwertuje kazdy wiersz na `dict` i zwraca liste.

**Uwaga:** Uzycie `LEFT JOIN` zamiast `JOIN` sprawia, ze obserwacje z nieistniejacymi gwiazdami (np. usunietymi z katalogu) rowniez sa zwracane -- z `star_name = None`.

**Przyklad zwracanej wartosci:**

```python
[
    {
        "id": 5,
        "star_id": 32349,
        "duration_minutes": 60,
        "priority": 10,
        "status": "waiting",
        "position_in_queue": None,
        "created_at": "2026-03-27T10:00:00+00:00",
        "started_at": None,
        "finished_at": None,
        "star_name": "Sirius"
    },
    {
        "id": 3,
        "star_id": 677,
        "duration_minutes": 30,
        "priority": 5,
        "status": "waiting",
        "position_in_queue": None,
        "created_at": "2026-03-27T09:30:00+00:00",
        "started_at": None,
        "finished_at": None,
        "star_name": "Polaris"
    }
]
```

---

#### `add_observation()`

```python
def add_observation(
    star_id: int,
    duration_minutes: int = 30,
    priority: int = 0
) -> dict
```

**Opis:** Dodaje nowa obserwacje do kolejki ze statusem `'waiting'`.

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `star_id` | `int` | -- (wymagany) | Identyfikator gwiazdy do obserwacji (klucz obcy do `stars.id`). |
| `duration_minutes` | `int` | `30` | Planowany czas trwania obserwacji w minutach. |
| `priority` | `int` | `0` | Priorytet obserwacji. Wyzsza wartosc = wyzszy priorytet. |

**Zwraca:** `dict` -- slownik z danymi nowo utworzonej obserwacji, wlacznie z polem `star_name`.

**Dzialanie krok po kroku:**

1. Generuje biezacy znacznik czasowy w UTC w formacie ISO 8601 (`datetime.now(timezone.utc).isoformat()`).
2. Otwiera polaczenie do bazy danych.
3. Wstawia nowy wiersz do tabeli `observations` z podanymi wartosciami, statusem `'waiting'` i wygenerowanym znacznikiem `created_at`.
4. Pobiera `lastrowid` -- identyfikator nowo wstawionego wiersza.
5. Zatwierdza transakcje.
6. Pobiera pelne dane obserwacji (z `LEFT JOIN` na `stars`) na podstawie `lastrowid`.
7. Zamyka polaczenie i zwraca slownik.

**Przypadki brzegowe:**

- Jesli `star_id` nie odpowiada zadnej gwieezdzie w tabeli `stars`, wiersz zostanie wstawiony (SQLite domyslnie nie wymusza kluczy obcych), ale `star_name` w wyniku bedzie `None`.
- Brak walidacji `duration_minutes` i `priority` -- warstwa API powinna sprawdzic, czy sa to sensowne wartosci.

---

#### `delete_observation()`

```python
def delete_observation(obs_id: int) -> bool
```

**Opis:** Usuwa obserwacje z kolejki. Mozliwe jest usuwanie **wylacznie** obserwacji w stanie `'waiting'`.

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `obs_id` | `int` | Identyfikator obserwacji do usuniecia. |

**Zwraca:** `bool`

- `True` -- obserwacja zostala pomyslnie usunieta.
- `False` -- obserwacja o podanym ID nie istnieje.

**Rzuca wyjatki:**

- `ValueError("Nie mozna usunac obserwacji, ktora nie jest w stanie waiting")` -- jesli obserwacja istnieje, ale jej status to nie `'waiting'` (np. `'tracking'`, `'completed'`).

**Dzialanie krok po kroku:**

1. Otwiera polaczenie do bazy danych.
2. Pobiera status obserwacji o podanym `obs_id`.
3. Jesli obserwacja nie istnieje (`row is None`), zamyka polaczenie i zwraca `False`.
4. Jesli status nie jest `'waiting'`, zamyka polaczenie i rzuca wyjatek `ValueError`.
5. Wykonuje `DELETE FROM observations WHERE id = ?`.
6. Zatwierdza transakcje, zamyka polaczenie i zwraca `True`.

**Uzasadnienie ograniczenia:** Obserwacje w trakcie sledzenia (`'tracking'`) lub juz zakonczone (`'completed'`, `'stopped'`) stanowia czesc historii obserwacji. Ich usuniecie mogloby spowodowac niespojnosc danych (np. silnik trackingowy moze odwolywac sie do obserwacji w stanie `'tracking'`).

---

#### `update_observation()`

```python
def update_observation(obs_id: int, data: dict) -> dict | None
```

**Opis:** Aktualizuje parametry obserwacji w kolejce. Mozliwa jest modyfikacja **wylacznie** obserwacji w stanie `'waiting'`.

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `obs_id` | `int` | Identyfikator obserwacji do aktualizacji. |
| `data` | `dict` | Slownik z polami do aktualizacji. |

**Dozwolone pola (whitelist):**

- `duration_minutes` -- nowy czas trwania obserwacji.
- `priority` -- nowy priorytet.

**Zwraca:** `dict | None`

- `dict` -- zaktualizowane dane obserwacji (z `star_name`).
- `None` -- jesli obserwacja o podanym ID nie istnieje.

**Rzuca wyjatki:**

- `ValueError("Nie mozna modyfikowac obserwacji, ktora nie jest w stanie waiting")` -- jesli obserwacja istnieje, ale jej status to nie `'waiting'`.

**Dzialanie krok po kroku:**

1. Otwiera polaczenie do bazy danych.
2. Pobiera status obserwacji o podanym `obs_id`.
3. Jesli obserwacja nie istnieje, zamyka polaczenie i zwraca `None`.
4. Jesli status nie jest `'waiting'`, zamyka polaczenie i rzuca `ValueError`.
5. Filtruje slownik `data`, pozostawiajac tylko dozwolone pola (`duration_minutes`, `priority`).
6. Jesli po filtrowaniu sa pola do aktualizacji, buduje dynamicznie zapytanie `UPDATE` i wykonuje je.
7. Jesli po filtrowaniu nie ma pol do aktualizacji (np. `data` zawieral tylko nieznane klucze), pomija krok UPDATE, ale kontynuuje.
8. Pobiera pelne, zaktualizowane dane obserwacji (z `LEFT JOIN` na `stars`).
9. Zamyka polaczenie i zwraca slownik.

**Przypadki brzegowe:**

- Podanie pustego slownika `data` lub slownika z samymi niedozwolonymi kluczami nie powoduje bledu -- funkcja zwraca aktualne dane obserwacji bez zmian.
- Nie mozna zmienic `star_id` -- po utworzeniu obserwacja jest na stale powiazana z gwiazda.

---

#### `get_next_observation()`

```python
def get_next_observation() -> dict | None
```

**Opis:** Pobiera nastepna obserwacje do realizacji z kolejki -- te o najwyzszym priorytecie sposrod oczekujacych. Zwraca rowniez wspolrzedne rektascensji i deklinacji gwiazdy, ktore sa niezbedne do uruchomienia silnika trackingowego.

**Parametry:** Brak.

**Zwraca:** `dict | None`

- `dict` -- dane obserwacji wlacznie z polami `star_name`, `ra`, `dec` (wspolrzedne gwiazdy).
- `None` -- jesli kolejka jest pusta (brak obserwacji w stanie `'waiting'`).

**Dzialanie krok po kroku:**

1. Otwiera polaczenie do bazy danych.
2. Wykonuje zapytanie z `LEFT JOIN` na tabeli `stars`, filtrujac po `status = 'waiting'`.
3. Sortuje wyniki: `ORDER BY o.priority DESC, o.created_at ASC`.
4. Pobiera tylko jeden wiersz (`LIMIT 1`) -- obserwacje o najwyzszym priorytecie, a w przypadku remisu -- te dodana najwczesniej.
5. Zamyka polaczenie.
6. Jesli wiersz nie istnieje, zwraca `None`.
7. W przeciwnym razie konwertuje wiersz na slownik i zwraca.

**Roznica wzgledem `get_queue()`:** Funkcja `get_next_observation()` zwraca **jeden** wynik z dodatkowymi polami `ra` i `dec`, natomiast `get_queue()` zwraca **cala liste** oczekujacych obserwacji bez wspolrzednych gwiazdy. Funkcja ta jest uzywana przez silnik trackingowy do pobrania kolejnego zadania.

**Przyklad zwracanej wartosci:**

```python
{
    "id": 5,
    "star_id": 32349,
    "duration_minutes": 60,
    "priority": 10,
    "status": "waiting",
    "position_in_queue": None,
    "created_at": "2026-03-27T10:00:00+00:00",
    "started_at": None,
    "finished_at": None,
    "star_name": "Sirius",
    "ra": 6.7525693,
    "dec": -16.7161
}
```

---

#### `update_observation_status()`

```python
def update_observation_status(obs_id: int, status: str) -> None
```

**Opis:** Zmienia status obserwacji i automatycznie ustawia odpowiedni znacznik czasowy w zaleznosci od nowego statusu.

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `obs_id` | `int` | Identyfikator obserwacji. |
| `status` | `str` | Nowy status. Oczekiwane wartosci: `'waiting'`, `'tracking'`, `'completed'`, `'stopped'`. |

**Zwraca:** `None`.

**Dzialanie krok po kroku:**

1. Otwiera polaczenie do bazy danych.
2. Generuje biezacy znacznik czasowy w UTC (ISO 8601).
3. W zaleznosci od wartosci `status`:
   - **`"tracking"`** -- wykonuje `UPDATE` ustawiajac `status` i `started_at` na biezacy czas. Oznacza to, ze silnik trackingowy rozpoczal sledzenie obiektu.
   - **`"completed"` lub `"stopped"`** -- wykonuje `UPDATE` ustawiajac `status` i `finished_at` na biezacy czas. Obserwacja zostala zakonczona (pomyslnie lub przerwana przez operatora).
   - **Inny status** (np. `"waiting"`) -- wykonuje `UPDATE` ustawiajac tylko `status`, bez modyfikacji znacznikow czasowych.
4. Zatwierdza transakcje i zamyka polaczenie.

**Mapa statusow i znacznikow czasowych:**

| Nowy status | `started_at` | `finished_at` |
|-------------|-------------|--------------|
| `tracking` | Ustawiana na biezacy czas UTC | Bez zmian |
| `completed` | Bez zmian | Ustawiana na biezacy czas UTC |
| `stopped` | Bez zmian | Ustawiana na biezacy czas UTC |
| Inny | Bez zmian | Bez zmian |

**Przypadki brzegowe:**

- Funkcja **nie sprawdza**, czy obserwacja o danym `obs_id` istnieje. Jesli nie istnieje, zapytanie `UPDATE` po prostu nie zmieni zadnego wiersza (brak bledu).
- Funkcja **nie waliduje przejsc statusow** -- mozliwe jest np. ustawienie statusu `'waiting'` na obserwacji, ktora juz jest `'completed'`. Walidacja przejsc jest odpowiedzialnoscia warstwy API i silnika trackingowego.
- W przypadku wielokrotnego ustawienia statusu `'tracking'` pole `started_at` zostanie nadpisane nowym znacznikiem.

---

### 3.6 Kalibracja

#### `update_calibration()`

```python
def update_calibration(offset_az: float, offset_alt: float) -> None
```

**Opis:** Zapisuje obliczone offsety kalibracyjne teleskopu do tabeli `telescope_config`. Offsety to roznice miedzy oczekiwana a rzeczywista pozycja teleskopu, wyrzonae w stopniach. Sa stosowane jako korekta przy kazdym obliczeniu pozycji docelowej.

**Parametry:**

| Parametr | Typ | Jednostka | Opis |
|----------|-----|-----------|------|
| `offset_az` | `float` | stopnie | Offset kalibracyjny azymutu. Wartosc dodawana do obliczonego azymutu, aby skompensowac blad montazu. |
| `offset_alt` | `float` | stopnie | Offset kalibracyjny elewacji (wysokosci). Wartosc dodawana do obliczonej elewacji. |

**Zwraca:** `None`.

**Dzialanie krok po kroku:**

1. Generuje biezacy znacznik czasowy w UTC (ISO 8601).
2. Otwiera polaczenie do bazy danych.
3. Wykonuje `UPDATE telescope_config` ustawiajac:
   - `calibration_offset_az` -- podany offset azymutu.
   - `calibration_offset_alt` -- podany offset elewacji.
   - `is_calibrated = 1` -- flaga wskazujaca, ze teleskop jest skalibrowany.
   - `last_calibration_time` -- biezacy znacznik czasowy.
4. Zatwierdza transakcje i zamyka polaczenie.

**Kiedy uzywac:** Funkcja jest wywolywana po zakonczeniu procedury kalibracji, gdy system obliczyl roznice miedzy pozycja teoretyczna a rzeczywista wybranej gwiazdy referencyjnej.

---

#### `reset_calibration()`

```python
def reset_calibration() -> None
```

**Opis:** Resetuje kalibracje teleskopu do stanu poczatkowego -- zeruje offsety i oznacza teleskop jako nieskalibrowany.

**Parametry:** Brak.

**Zwraca:** `None`.

**Dzialanie krok po kroku:**

1. Otwiera polaczenie do bazy danych.
2. Wykonuje `UPDATE telescope_config` ustawiajac:
   - `calibration_offset_az = 0` -- zerowy offset azymutu.
   - `calibration_offset_alt = 0` -- zerowy offset elewacji.
   - `is_calibrated = 0` -- flaga: nieskalibrowany.
   - `last_calibration_time = NULL` -- brak daty kalibracji.
3. Zatwierdza transakcje i zamyka polaczenie.

**Kiedy uzywac:** Funkcja jest wywolywana gdy:

- Operator reczenie resetuje kalibracje przez interfejs webowy.
- Teleskop zostal fizycznie przemieszczony (np. zmiana lokalizacji obserwatorium).
- Wykryto, ze istniejaca kalibracja daje bledne wyniki.

---

## 4. Zaleznosci miedzy modulami

Ponizszy diagram przedstawia, jak `config.py` i `models.py` lacza sie z pozostalymi komponentami backendu:

```
                    config.py
                   /    |    \
                  /     |     \
                 v      v      v
          models.py   app.py   api/
            |           |       |
            v           v       v
    star_catalog.db   Flask   REST endpoints
                        |
                        v
                   tracker.py
                   calibration.py
```

- **`config.py`** jest importowany przez wszystkie moduly backendu.
- **`models.py`** importuje `config` w celu uzyskania sciezki do bazy danych (`config.DATABASE_PATH`) oraz wartosci domyslnych lokalizacji.
- **`app.py`** wywoluje `init_db()` przy starcie aplikacji.
- **Endpointy API** (`api/`) wywoluja funkcje z `models.py` do realizacji operacji CRUD.
- **Silnik trackingowy** (`tracker.py`) korzysta z `get_next_observation()`, `update_observation_status()` i `get_config()`.
- **Modul kalibracji** (`calibration.py`) korzysta z `update_calibration()` i `reset_calibration()`.

---

## 5. Uwagi dotyczace bezpieczenstwa

1. **Klucz JWT:** Domyslna wartosc `SECRET_KEY` jest przeznaczona wylacznie do srodowiska deweloperskiego. Na Raspberry Pi w laboratorium nalezy ustawic zmienna srodowiskowa `SECRET_KEY` na losowy ciag znakow.

2. **Haslo operatora:** Domyslne haslo `"seesky123"` jest slabe. W srodowisku produkcyjnym nalezy ustawic zmienna `SEESKY_PASS`.

3. **SQL Injection:** Wszystkie zapytania SQL w `models.py` uzywaja parametryzowanych zapytan (`?` jako placeholder), co chroni przed atakami SQL injection. Jedynym wyjatkiem jest dynamiczne budowanie klauzuli `SET` w `update_config()` i `update_observation()`, ale nazwy kolumn sa filtrowane przez biala liste (`allowed`), wiec nie pochodza od uzytkownika.

4. **Tryb debugowania:** Flaga `FLASK_DEBUG` nie powinna byc wlaczona na Raspberry Pi podlaczonym do sieci -- ujawnia wewnetrzne sciezki i umozliwia zdalne wykonywanie kodu przez debugger Werkzeug.

5. **Polaczenia z baza:** Kazda funkcja w `models.py` otwiera i zamyka wlasne polaczenie. Nie ma puli polaczen ani mechanizmu transakcji rozproszonej. Jest to wystarczajace dla systemu o niskim obciazeniu (jeden operator, jeden silnik trackingowy), ale moze wymagac refaktoryzacji w przypadku rozszerzenia systemu.
