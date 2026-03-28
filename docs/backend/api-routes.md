# SeeSky REST API -- Dokumentacja tras (routes)

Niniejszy dokument zawiera kompletny opis implementacji REST API systemu SeeSky
realizowanego w dwoch plikach zrodlowych:

| Plik | Rola |
|---|---|
| `backend/app.py` | Fabryka aplikacji Flask |
| `backend/api/routes.py` | Definicja 19 endpointow REST API |

Bazowy prefiks wszystkich tras: **`/api`**

---

## Spis tresci

1. [Fabryka aplikacji (`app.py`)](#1-fabryka-aplikacji-apppy)
2. [Elementy globalne (`routes.py`)](#2-elementy-globalne-routespy)
3. [Autentykacja](#3-autentykacja)
   - 3.1 [POST /api/auth/login](#31-post-apiauthlogin)
   - 3.2 [POST /api/auth/logout](#32-post-apiauthlogout)
4. [Konfiguracja teleskopu](#4-konfiguracja-teleskopu)
   - 4.1 [GET /api/config](#41-get-apiconfig)
   - 4.2 [PUT /api/config](#42-put-apiconfig)
5. [Katalog gwiazd](#5-katalog-gwiazd)
   - 5.1 [GET /api/stars](#51-get-apistars)
   - 5.2 [GET /api/stars/:id](#52-get-apistarsid)
   - 5.3 [GET /api/stars/:id/position](#53-get-apistarsidposition)
6. [Kolejka obserwacji](#6-kolejka-obserwacji)
   - 6.1 [GET /api/queue](#61-get-apiqueue)
   - 6.2 [POST /api/queue](#62-post-apiqueue)
   - 6.3 [DELETE /api/queue/:id](#63-delete-apiqueueid)
   - 6.4 [PUT /api/queue/:id](#64-put-apiqueueid)
7. [Tracking (sledzenie)](#7-tracking-sledzenie)
   - 7.1 [GET /api/tracking/status](#71-get-apitrackingstatus)
   - 7.2 [POST /api/tracking/start](#72-post-apitrackingstart)
   - 7.3 [POST /api/tracking/stop](#73-post-apitrackingstop)
   - 7.4 [POST /api/tracking/pause](#74-post-apitrackingpause)
   - 7.5 [POST /api/tracking/resume](#75-post-apitrackingresume)
8. [Kalibracja](#8-kalibracja)
   - 8.1 [GET /api/calibration/status](#81-get-apicalibrationstatus)
   - 8.2 [POST /api/calibration/reset](#82-post-apicalibrationreset)
   - 8.3 [POST /api/calibration/polaris](#83-post-apicalibrationpolaris)
9. [Zestawienie kodow bledow](#9-zestawienie-kodow-bledow)

---

## 1. Fabryka aplikacji (`app.py`)

Plik `backend/app.py` odpowiada za utworzenie i skonfigurowanie instancji aplikacji Flask.

### Funkcja `create_app()`

**Sygnatura:** `create_app() -> Flask`

Kroki wykonywane wewnatrz funkcji:

1. Tworzy nowa instancje `Flask(__name__)`.
2. Ustawia klucz szyfrujacy `app.config["SECRET_KEY"]` na wartosc `config.SECRET_KEY` (domyslnie `"seesky-dev-secret-change-in-production"`, nadpisywalna zmienna srodowiskowa `SECRET_KEY`).
3. Wlacza obsluge CORS za pomoca `flask_cors.CORS` z regula `r"/api/*"` -> `origins: "*"`, co pozwala aplikacji frontendowej na komunikacje z API z dowolnej domeny.
4. Inicjalizuje baze danych wywolujac `init_db()` z modulu `database.models`.
5. Rejestruje Blueprint `api_bp` (zdefiniowany w `api/routes.py`) z prefiksem URL `/api`.
6. Zwraca skonfigurowany obiekt `app`.

### Blok glowny (`if __name__ == "__main__"`)

Uruchamia serwer deweloperski Flask z parametrami:

| Parametr | Zrodlo | Wartosc domyslna |
|---|---|---|
| `host` | `config.FLASK_HOST` | `"0.0.0.0"` |
| `port` | `config.FLASK_PORT` | `5000` |
| `debug` | `config.FLASK_DEBUG` | `False` |

Kazdy z tych parametrow moze byc nadpisany odpowiednia zmienna srodowiskowa (`FLASK_HOST`, `FLASK_PORT`, `FLASK_DEBUG`).

---

## 2. Elementy globalne (`routes.py`)

Plik `backend/api/routes.py` definiuje Blueprint `api_bp = Blueprint("api", __name__)` oraz wszystkie endpointy API.

### Zbior uniewaznionychtoken ow (`_revoked_tokens`)

```python
_revoked_tokens: set[str] = set()
```

Przechowuje tokeny JWT dodane podczas operacji wylogowania. Jest to struktura **in-memory** -- resetuje sie po kazdym restarcie serwera. Kazdy token znajdujacy sie w tym zbiorze jest traktowany jako niewazny.

### Dekorator `token_required`

**Sygnatura:** `token_required(f) -> decorated`

Dekorator stosowany na endpointach wymagajacych autoryzacji. Kolejnosc sprawdzen:

1. Odczytuje naglowek HTTP `Authorization`.
2. Sprawdza, czy naglowek rozpoczyna sie od `"Bearer "`. Jesli nie:
   - Zwraca `401` z bledem `TOKEN_MISSING` i komunikatem `"Brak naglowka Authorization"`.
3. Wyodrebnia token (znaki od indeksu 7 do konca naglowka).
4. Sprawdza, czy token znajduje sie w zbiorze `_revoked_tokens`. Jesli tak:
   - Zwraca `401` z bledem `TOKEN_EXPIRED` i komunikatem `"Token zostal uniewaziony"`.
5. Dekoduje token za pomoca `jwt.decode()` z algorytmem `HS256` i kluczem `current_app.config["SECRET_KEY"]`.
   - Jesli token wygasl (`ExpiredSignatureError`): zwraca `401` z bledem `TOKEN_EXPIRED`.
   - Jesli token jest nieprawidlowy (`InvalidTokenError`): zwraca `401` z bledem `TOKEN_MISSING`.
6. Jesli wszystkie sprawdzenia przeszly pomyslnie -- wywoluje oryginalna funkcje.

> **Uwaga:** Dekorator korzysta z `functools.wraps`, wiec zachowuje nazwe i docstring oryginalnej funkcji.

---

## 3. Autentykacja

### 3.1 POST `/api/auth/login`

**Funkcja:** `login()`
**Wymaga autoryzacji:** Nie

Loguje uzytkownika i zwraca token JWT.

#### Cialo zadania (JSON)

| Pole | Typ | Wymagane | Opis |
|---|---|---|---|
| `username` | `string` | Tak | Nazwa uzytkownika |
| `password` | `string` | Tak | Haslo |

#### Logika krok po kroku

1. Parsuje cialo zadania jako JSON (`get_json(silent=True)`).
2. Jesli brak danych JSON -> zwraca `400 BAD_REQUEST`.
3. Odczytuje pola `username` i `password`.
4. Jesli ktorekolwiek pole jest puste lub brakuje go -> zwraca `400 BAD_REQUEST` z komunikatem `"Pola 'username' i 'password' sa wymagane"`.
5. Porownuje dane z wartosciami konfiguracyjnymi `config.DEFAULT_USERNAME` (domyslnie `"operator"`) i `config.DEFAULT_PASSWORD` (domyslnie `"seesky123"`).
6. Jesli dane sie nie zgadzaja -> zwraca `401 INVALID_CREDENTIALS`.
7. Tworzy payload JWT z claimami:
   - `sub` -- nazwa uzytkownika,
   - `iat` -- aktualny czas UTC,
   - `exp` -- aktualny czas UTC + `config.JWT_EXPIRATION_SECONDS` (domyslnie 3600 sekund = 1 godzina).
8. Koduje token algorytmem `HS256` z kluczem `SECRET_KEY`.
9. Zwraca odpowiedz `200`.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "token": "<token_jwt>",
    "expires_in": 3600,
    "user": {
        "id": 1,
        "username": "operator"
    }
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `BAD_REQUEST` | Brak ciala JSON lub brakujace pola |
| `401` | `INVALID_CREDENTIALS` | Nieprawidlowa nazwa uzytkownika lub haslo |

---

### 3.2 POST `/api/auth/logout`

**Funkcja:** `logout()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Wylogowuje uzytkownika poprzez uniewaznienie jego tokena JWT.

#### Cialo zadania

Brak wymaganego ciala.

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Wyodrebnia token z naglowka `Authorization` (znaki od indeksu 7).
3. Dodaje token do zbioru `_revoked_tokens`.
4. Zwraca odpowiedz `200`.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "message": "Wylogowano pomyslnie"
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Brak, wygasly lub uniewazniony token |

---

## 4. Konfiguracja teleskopu

### 4.1 GET `/api/config`

**Funkcja:** `get_telescope_config()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Pobiera biezaca konfiguracje teleskopu z bazy danych.

#### Parametry zadania

Brak.

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Wywoluje `get_config()` z modulu `database.models`.
3. Zwraca caly slownik konfiguracji jako JSON z kodem `200`.

#### Odpowiedz sukcesu (`200 OK`)

Zwraca slownik `telescope_config` -- jego struktura zalezy od implementacji `get_config()`, ale typowo zawiera pola takie jak:

```json
{
    "latitude": 51.1079,
    "longitude": 17.0385,
    "altitude": 120.0,
    "tracking_interval_seconds": 2.0,
    "is_calibrated": false,
    "calibration_offset_az": 0.0,
    "calibration_offset_alt": 0.0,
    "last_calibration_time": null,
    "pressure": 1013.25,
    "temperature": 10.0,
    "humidity": 0.5,
    "wavelength": 210000.0
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |

---

### 4.2 PUT `/api/config`

**Funkcja:** `update_telescope_config()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Aktualizuje wybrane pola konfiguracji teleskopu.

#### Cialo zadania (JSON)

Dowolny podzbiur pol konfiguracyjnych. Walidowane pola:

| Pole | Typ | Zakres | Opis |
|---|---|---|---|
| `latitude` | `float` | `[-90, 90]` | Szerokosc geograficzna |
| `longitude` | `float` | `[-180, 180]` | Dlugosc geograficzna |
| `tracking_interval_seconds` | `float` | `> 0` | Interwal petli trackingowej (sekundy) |

Inne pola konfiguracyjne moga byc rowniez przeslane -- zostana przekazane do `update_config()`.

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Parsuje cialo zadania jako JSON.
3. Jesli brak danych JSON -> zwraca `400 BAD_REQUEST`.
4. Waliduje poszczegolne pola:
   - `latitude`: musi byc w zakresie [-90, 90].
   - `longitude`: musi byc w zakresie [-180, 180].
   - `tracking_interval_seconds`: musi byc wiekszy od 0.
5. Jesli walidacja nie przejdzie -> zwraca `400 VALIDATION_ERROR` z odpowiednim komunikatem.
6. Wywoluje `update_config(data)` i odbiera zaktualizowana konfiguracje.
7. Zwraca odpowiedz `200`.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "message": "Konfiguracja zaktualizowana pomyslnie",
    "config": { "...zaktualizowany slownik konfiguracji..." }
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `BAD_REQUEST` | Brak ciala JSON |
| `400` | `VALIDATION_ERROR` | Wartosc poza dopuszczalnym zakresem |
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |

---

## 5. Katalog gwiazd

### 5.1 GET `/api/stars`

**Funkcja:** `list_stars()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Pobiera liste gwiazd z katalogu z obsluga paginacji i filtrowania.

#### Parametry zapytania (query params)

| Parametr | Typ | Domyslnie | Opis |
|---|---|---|---|
| `page` | `int` | `1` | Numer strony (min. 1) |
| `per_page` | `int` | `20` | Liczba wynikow na strone (zakres [1, 100]) |
| `search` | `string` | `null` | Fraza wyszukiwania (nazwa gwiazdy) |
| `min_magnitude` | `float` | `null` | Minimalna jasnosc (magnitudo) |
| `max_magnitude` | `float` | `null` | Maksymalna jasnosc (magnitudo) |
| `constellation` | `string` | `null` | Filtrowanie wg gwiazdozbioru |

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Odczytuje parametry zapytania z automatyczna konwersja typow.
3. Waliduje `page` -- musi byc >= 1. Jesli nie -> zwraca `400 BAD_REQUEST`.
4. Waliduje `per_page` -- musi byc w zakresie [1, 100]. Jesli nie -> zwraca `400 BAD_REQUEST`.
5. Wywoluje `get_stars()` z parametrami: `page`, `per_page`, `search`, `min_mag`, `max_mag`, `constellation`.
6. Zwraca wynik jako JSON z kodem `200`.

#### Odpowiedz sukcesu (`200 OK`)

Struktura odpowiedzi zalezy od implementacji `get_stars()`, typowo:

```json
{
    "stars": [ { "...dane gwiazdy..." }, "..." ],
    "page": 1,
    "per_page": 20,
    "total": 1500
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `BAD_REQUEST` | `page` < 1 lub `per_page` poza zakresem [1, 100] |
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |

---

### 5.2 GET `/api/stars/:id`

**Funkcja:** `get_star_detail(star_id)`
**Wymaga autoryzacji:** Tak (`@token_required`)

Pobiera szczegolowe informacje o pojedynczej gwiazdzie.

#### Parametry sciezki

| Parametr | Typ | Opis |
|---|---|---|
| `star_id` | `int` | Identyfikator gwiazdy |

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Wywoluje `get_star(star_id)`.
3. Jesli gwiazda nie istnieje (`None`) -> zwraca `404 NOT_FOUND`.
4. Zwraca slownik gwiazdy jako JSON z kodem `200`.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "id": 1,
    "proper_name": "Sirius",
    "ra": 101.2872,
    "dec": -16.7161,
    "magnitude": -1.46,
    "constellation": "CMa",
    "...inne pola..."
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |
| `404` | `NOT_FOUND` | Gwiazda o podanym `id` nie istnieje |

---

### 5.3 GET `/api/stars/:id/position`

**Funkcja:** `get_star_position(star_id)`
**Wymaga autoryzacji:** Tak (`@token_required`)

Oblicza aktualna pozycje gwiazdy na niebie (wspolrzedne horyzontalne) dla biezacej lokalizacji teleskopu.

#### Parametry sciezki

| Parametr | Typ | Opis |
|---|---|---|
| `star_id` | `int` | Identyfikator gwiazdy |

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Wywoluje `get_star(star_id)`. Jesli gwiazda nie istnieje -> zwraca `404 NOT_FOUND`.
3. Pobiera konfiguracje teleskopu za pomoca `get_config()`. Jesli brak konfiguracji -> zwraca `500 INTERNAL_ERROR`.
4. Wywoluje `get_current_position(star, cfg)` z modulu `tracking.position`, co oblicza wspolrzedne horyzontalne (azymut i elewacje) na podstawie wspolrzednych rownikowych gwiazdy (RA/Dec) oraz lokalizacji obserwatora.
5. Wzbogaca wynik o pola:
   - `star_id` -- identyfikator gwiazdy,
   - `star_name` -- nazwa wlasna gwiazdy (`star.get("proper_name")`).
6. Zwraca wynik jako JSON z kodem `200`.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "alt": 45.1234,
    "az": 180.5678,
    "is_above_horizon": true,
    "star_id": 1,
    "star_name": "Sirius"
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |
| `404` | `NOT_FOUND` | Gwiazda o podanym `id` nie istnieje |
| `500` | `INTERNAL_ERROR` | Brak konfiguracji teleskopu w bazie danych |

---

## 6. Kolejka obserwacji

### 6.1 GET `/api/queue`

**Funkcja:** `list_queue()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Pobiera liste wszystkich obserwacji w kolejce.

#### Parametry zadania

Brak.

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Wywoluje `get_queue()`, ktora zwraca liste obserwacji.
3. Zwraca odpowiedz JSON z lista obserwacji i ich calkowita liczba.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "queue": [
        {
            "id": 1,
            "star_id": 42,
            "star_name": "Vega",
            "duration_minutes": 30,
            "priority": 0,
            "status": "waiting",
            "created_at": "2026-03-27T20:00:00Z"
        }
    ],
    "total": 1
}
```

Pole `total` odpowiada dlugosci listy `queue` (`len(queue)`).

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |

---

### 6.2 POST `/api/queue`

**Funkcja:** `add_to_queue()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Dodaje nowa obserwacje do kolejki.

#### Cialo zadania (JSON)

| Pole | Typ | Wymagane | Domyslnie | Opis |
|---|---|---|---|---|
| `star_id` | `int` | Tak | -- | Identyfikator gwiazdy do obserwacji |
| `duration_minutes` | `int`/`float` | Nie | `30` | Czas trwania obserwacji w minutach |
| `priority` | `int` | Nie | `0` | Priorytet obserwacji (wyzsza wartosc = wyzszy priorytet) |

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Parsuje cialo zadania jako JSON. Jesli brak -> zwraca `400 BAD_REQUEST`.
3. Odczytuje pole `star_id`. Jesli brak -> zwraca `400 BAD_REQUEST`.
4. Sprawdza, czy gwiazda o podanym `star_id` istnieje w katalogu (wywolanie `get_star(star_id)`). Jesli nie -> zwraca `404 NOT_FOUND`.
5. Odczytuje opcjonalne pola `duration_minutes` (domyslnie 30) i `priority` (domyslnie 0).
6. Wywoluje `add_observation(star_id, duration_minutes=duration, priority=priority)`.
7. Zwraca odpowiedz `201 Created`.

#### Odpowiedz sukcesu (`201 Created`)

```json
{
    "message": "Obserwacja dodana do kolejki",
    "observation": {
        "id": 5,
        "star_id": 42,
        "duration_minutes": 30,
        "priority": 0,
        "status": "waiting",
        "created_at": "2026-03-27T21:00:00Z"
    }
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `BAD_REQUEST` | Brak ciala JSON lub brak pola `star_id` |
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |
| `404` | `NOT_FOUND` | Gwiazda o podanym `star_id` nie istnieje |

---

### 6.3 DELETE `/api/queue/:id`

**Funkcja:** `remove_from_queue(obs_id)`
**Wymaga autoryzacji:** Tak (`@token_required`)

Usuwa obserwacje z kolejki. Mozna usunac tylko obserwacje o statusie `"waiting"`.

#### Parametry sciezki

| Parametr | Typ | Opis |
|---|---|---|
| `obs_id` | `int` | Identyfikator obserwacji |

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Wywoluje `delete_observation(obs_id)` wewnatrz bloku `try/except ValueError`.
3. Jesli `delete_observation` rzuci wyjatek `ValueError` (np. proba usuniecia obserwacji o statusie innym niz `"waiting"`) -> zwraca `400 BAD_REQUEST` z komunikatem z wyjatku.
4. Jesli `delete_observation` zwroci `False` (obserwacja nie istnieje) -> zwraca `404 NOT_FOUND`.
5. Jesli usuniecie sie powiodlo -> zwraca `200`.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "message": "Obserwacja usunieta z kolejki",
    "deleted_id": 3
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `BAD_REQUEST` | Proba usuniecia obserwacji o statusie innym niz `"waiting"` |
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |
| `404` | `NOT_FOUND` | Obserwacja o podanym `id` nie istnieje |

---

### 6.4 PUT `/api/queue/:id`

**Funkcja:** `update_queue_item(obs_id)`
**Wymaga autoryzacji:** Tak (`@token_required`)

Aktualizuje parametry obserwacji w kolejce. Mozna modyfikowac tylko obserwacje o statusie `"waiting"`.

#### Parametry sciezki

| Parametr | Typ | Opis |
|---|---|---|
| `obs_id` | `int` | Identyfikator obserwacji |

#### Cialo zadania (JSON)

| Pole | Typ | Wymagane | Opis |
|---|---|---|---|
| `duration_minutes` | `int`/`float` | Nie | Nowy czas trwania obserwacji |
| `priority` | `int` | Nie | Nowy priorytet obserwacji |

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Parsuje cialo zadania jako JSON. Jesli brak -> zwraca `400 BAD_REQUEST`.
3. Wywoluje `update_observation(obs_id, data)` wewnatrz bloku `try/except ValueError`.
4. Jesli `update_observation` rzuci `ValueError` (np. proba modyfikacji obserwacji o statusie innym niz `"waiting"`) -> zwraca `400 BAD_REQUEST` z komunikatem z wyjatku.
5. Jesli `update_observation` zwroci `None` (obserwacja nie istnieje) -> zwraca `404 NOT_FOUND`.
6. Jesli aktualizacja sie powiodla -> zwraca `200`.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "message": "Obserwacja zaktualizowana",
    "observation": {
        "id": 3,
        "star_id": 42,
        "duration_minutes": 60,
        "priority": 5,
        "status": "waiting"
    }
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `BAD_REQUEST` | Brak ciala JSON lub proba modyfikacji obserwacji o niedozwolonym statusie |
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |
| `404` | `NOT_FOUND` | Obserwacja o podanym `id` nie istnieje |

---

## 7. Tracking (sledzenie)

### 7.1 GET `/api/tracking/status`

**Funkcja:** `tracking_status()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Zwraca aktualny status petli trackingowej.

#### Parametry zadania

Brak.

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Wywoluje `tracking_loop.get_status()` -- metode obiektu globalnego `tracking_loop` z modulu `tracking.tracker`.
3. Zwraca zwrocony slownik statusu jako JSON z kodem `200`.

#### Odpowiedz sukcesu (`200 OK`)

Struktura zalezy od implementacji `tracking_loop.get_status()`, typowo zawiera informacje o biezacej obserwacji, czasie, stanie petli itp.

```json
{
    "is_tracking": true,
    "is_paused": false,
    "current_star": {
        "id": 42,
        "name": "Vega"
    },
    "elapsed_time": 120.5,
    "remaining_time": 1679.5,
    "current_position": {
        "alt": 62.34,
        "az": 245.12
    }
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |

---

### 7.2 POST `/api/tracking/start`

**Funkcja:** `tracking_start()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Rozpoczyna sledzenie nastepnej obserwacji z kolejki.

#### Cialo zadania

Brak wymaganego ciala.

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Sprawdza, czy tracking jest juz aktywny (`tracking_loop.is_tracking`). Jesli tak -> zwraca `400 TRACKING_ACTIVE`.
3. Pobiera nastepna obserwacje z kolejki za pomoca `get_next_observation()`. Jesli brak obserwacji (`None`) -> zwraca `400 QUEUE_EMPTY`.
4. Pobiera konfiguracje teleskopu za pomoca `get_config()`. Jesli brak konfiguracji -> zwraca `500 INTERNAL_ERROR`.
5. Oblicza biezaca pozycje gwiazdy na niebie -- wywoluje `get_current_position()` z danymi RA/Dec obserwacji i konfiguracja.
6. Sprawdza, czy gwiazda jest nad horyzontem (`pos["is_above_horizon"]`). Jesli nie -> zwraca `400 STAR_BELOW_HORIZON` z informacja o aktualnej elewacji.
7. Ustawia status obserwacji na `"tracking"` za pomoca `update_observation_status(obs["id"], "tracking")`.
8. Uruchamia petle trackingowa: `tracking_loop.start(observation=obs, cfg=cfg)`.
9. Zwraca odpowiedz `200` z danymi obserwacji i docelowa pozycja.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "message": "Tracking rozpoczety",
    "observation": {
        "id": 1,
        "star_id": 42,
        "star_name": "Vega",
        "duration_minutes": 30,
        "target_alt": 62.3412,
        "target_az": 245.1234
    }
}
```

Pola `target_alt` i `target_az` sa zaokraglone do 4 miejsc po przecinku.

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `TRACKING_ACTIVE` | Tracking jest juz uruchomiony |
| `400` | `QUEUE_EMPTY` | Kolejka obserwacji jest pusta |
| `400` | `STAR_BELOW_HORIZON` | Gwiazda jest ponizej horyzontu |
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |
| `500` | `INTERNAL_ERROR` | Brak konfiguracji teleskopu |

---

### 7.3 POST `/api/tracking/stop`

**Funkcja:** `tracking_stop()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Zatrzymuje aktywne sledzenie.

#### Cialo zadania

Brak wymaganego ciala.

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Sprawdza, czy tracking jest aktywny (`tracking_loop.is_tracking`). Jesli nie -> zwraca `400 TRACKING_INACTIVE`.
3. Zapisuje referencje do biezacej obserwacji (`tracking_loop.observation`).
4. Wywoluje `tracking_loop.stop()` -- zatrzymuje petle trackingowa i otrzymuje slownik `result`.
5. Jesli `result` zawiera `observation_id`, ustawia status tej obserwacji na `"stopped"` za pomoca `update_observation_status()`.
6. Zwraca odpowiedz `200`.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "message": "Tracking zatrzymany",
    "observation": {
        "id": 1,
        "star_name": "Vega",
        "elapsed_time": 542.3,
        "status": "stopped"
    }
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `TRACKING_INACTIVE` | Tracking nie jest aktywny |
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |

---

### 7.4 POST `/api/tracking/pause`

**Funkcja:** `tracking_pause()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Wstrzymuje (pauzuje) aktywne sledzenie.

#### Cialo zadania

Brak wymaganego ciala.

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Sprawdza, czy tracking jest aktywny (`tracking_loop.is_tracking`). Jesli nie -> zwraca `400 TRACKING_INACTIVE`.
3. Wywoluje `tracking_loop.pause()` wewnatrz bloku `try/except RuntimeError`.
4. Jesli `pause()` rzuci `RuntimeError` (np. tracking jest juz wstrzymany) -> zwraca `400 BAD_REQUEST` z komunikatem z wyjatku.
5. Pobiera aktualny status petli za pomoca `tracking_loop.get_status()`.
6. Zwraca odpowiedz `200`.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "message": "Tracking wstrzymany",
    "observation": {
        "id": 1,
        "star_name": "Vega",
        "elapsed_time": 120.5,
        "remaining_time": 1679.5,
        "status": "paused"
    }
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `TRACKING_INACTIVE` | Tracking nie jest aktywny |
| `400` | `BAD_REQUEST` | Tracking jest juz wstrzymany lub inny blad `RuntimeError` |
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |

---

### 7.5 POST `/api/tracking/resume`

**Funkcja:** `tracking_resume()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Wznawia wstrzymane sledzenie.

#### Cialo zadania

Brak wymaganego ciala.

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Sprawdza, czy tracking jest aktywny (`tracking_loop.is_tracking`). Jesli nie -> zwraca `400 TRACKING_INACTIVE`.
3. Wywoluje `tracking_loop.resume()` wewnatrz bloku `try/except RuntimeError`.
4. Jesli `resume()` rzuci `RuntimeError` (np. tracking nie jest wstrzymany) -> zwraca `400 BAD_REQUEST` z komunikatem z wyjatku.
5. Pobiera aktualny status petli za pomoca `tracking_loop.get_status()`.
6. Zwraca odpowiedz `200`.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "message": "Tracking wznowiony",
    "status": {
        "is_tracking": true,
        "is_paused": false,
        "current_star": { "id": 42, "name": "Vega" },
        "elapsed_time": 120.5,
        "remaining_time": 1679.5
    }
}
```

> **Uwaga:** W odroznieniu od endpointu `pause`, ktory zwraca pole `observation`, endpoint `resume` zwraca pole `status` z pelnym obiektem statusu petli trackingowej.

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `TRACKING_INACTIVE` | Tracking nie jest aktywny |
| `400` | `BAD_REQUEST` | Tracking nie jest wstrzymany lub inny blad `RuntimeError` |
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |

---

## 8. Kalibracja

### 8.1 GET `/api/calibration/status`

**Funkcja:** `calibration_status()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Zwraca aktualny status kalibracji teleskopu.

#### Parametry zadania

Brak.

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Pobiera konfiguracje za pomoca `get_config()`.
3. Tworzy odpowiedz z pol konfiguracji:
   - `is_calibrated` -- rzutowanie `cfg.get("is_calibrated")` na `bool`,
   - `last_calibration_time` -- czas ostatniej kalibracji (lub `null`),
   - `offset_az` -- przesuniecie azymutu (domyslnie `0.0`),
   - `offset_alt` -- przesuniecie elewacji (domyslnie `0.0`).
4. Zwraca odpowiedz `200`.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "is_calibrated": true,
    "last_calibration_time": "2026-03-27T18:30:00Z",
    "offset_az": -0.1234,
    "offset_alt": 0.5678
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |

---

### 8.2 POST `/api/calibration/reset`

**Funkcja:** `calibration_reset()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Resetuje kalibracje teleskopu do pozycji zerowej.

#### Cialo zadania

Brak wymaganego ciala.

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Sprawdza, czy tracking jest aktywny (`tracking_loop.is_tracking`). Jesli tak -> zwraca `400 TRACKING_ACTIVE` z komunikatem `"Nie mozna zresetowac podczas aktywnego trackingu"`.
3. Wywoluje `reset_calibration()` z modulu `database.models`.
4. Zwraca odpowiedz `200` z komunikatem o resecie i pozycja zerowa.

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "message": "Teleskop zresetowany do pozycji (0, 0)",
    "position": {
        "alt": 0.0,
        "az": 0.0
    }
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `TRACKING_ACTIVE` | Tracking jest aktywny -- nie mozna resetowac kalibracji |
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |

---

### 8.3 POST `/api/calibration/polaris`

**Funkcja:** `calibration_polaris()`
**Wymaga autoryzacji:** Tak (`@token_required`)

Wykonuje kalibracje teleskopu na podstawie Gwiazdy Polarnej (Polaris). Polaris pelni role punktu odniesienia, poniewaz jej pozycja na niebie jest bardzo bliska biegunowi polnocnemu nieba.

#### Cialo zadania

Brak wymaganego ciala.

#### Stale uzywanej w kalibracji

| Stala | Wartosc | Opis |
|---|---|---|
| `polaris_ra` | `37.9546` stopni | Rektascensja Polaris (epoka J2000) |
| `polaris_dec` | `89.2641` stopni | Deklinacja Polaris (epoka J2000) |

#### Logika krok po kroku

1. Dekorator `@token_required` weryfikuje token.
2. Sprawdza, czy tracking jest aktywny (`tracking_loop.is_tracking`). Jesli tak -> zwraca `400 TRACKING_ACTIVE`.
3. Pobiera konfiguracje teleskopu za pomoca `get_config()`.
4. Oblicza biezaca pozycje Polaris na niebie wywolujac `get_current_position()` z RA=37.9546 i Dec=89.2641 oraz biezaca konfiguracja.
5. Sprawdza, czy Polaris jest nad horyzontem (`pos["is_above_horizon"]`). Jesli nie -> zwraca `400 STAR_BELOW_HORIZON` z komunikatem `"Polaris jest pod horyzontem - kalibracja niemozliwa"`.
6. Oblicza rzeczywista (teoretyczna) pozycje Polaris **bez offsetow kalibracyjnych** za pomoca bezposredniego wywolania `calculate_alt_az()` z parametrami:
   - `ra` = 37.9546, `dec` = 89.2641,
   - `lat`, `lon`, `alt` z konfiguracji teleskopu,
   - parametry atmosferyczne: `pressure` (domyslnie 1013.25 hPa), `temperature` (domyslnie 10.0 C), `humidity` (domyslnie 0.5), `wavelength` (domyslnie 210000.0 nm -- linia wodoru HI 21 cm).
7. Definiuje oczekiwana pozycje Polaris:
   - `expected_alt` = szerokosc geograficzna obserwatora (`cfg["latitude"]`),
   - `expected_az` = 0.0 (polnoc).
8. Oblicza offsety kalibracyjne jako roznice miedzy pozycja oczekiwana a obliczona:
   - `offset_az = expected_az - az_true`,
   - `offset_alt = expected_alt - alt_true`.
9. Zapisuje offsety za pomoca `update_calibration(offset_az, offset_alt)`.
10. Ponownie pobiera konfiguracje (`get_config()`) aby uzyskac zaktualizowany czas kalibracji.
11. Zwraca odpowiedz `200` z danymi kalibracji (offsety zaokraglone do 4 miejsc po przecinku).

#### Odpowiedz sukcesu (`200 OK`)

```json
{
    "message": "Kalibracja na Gwiazde Polnocna zakonczona pomyslnie",
    "calibration": {
        "is_calibrated": true,
        "last_calibration_time": "2026-03-27T19:45:00Z",
        "offset_az": -0.1234,
        "offset_alt": 0.5678
    }
}
```

#### Kody bledow

| Kod HTTP | Kod bledu | Przyczyna |
|---|---|---|
| `400` | `TRACKING_ACTIVE` | Tracking jest aktywny -- nie mozna kalibrowac |
| `400` | `STAR_BELOW_HORIZON` | Polaris jest ponizej horyzontu (np. na poludniowej polkuli) |
| `401` | `TOKEN_MISSING` / `TOKEN_EXPIRED` | Problem z autoryzacja |

---

## 9. Zestawienie kodow bledow

Ponizej znajduje sie kompletne zestawienie kodow bledow uzywanych w API:

| Kod bledu | Kod HTTP | Opis |
|---|---|---|
| `BAD_REQUEST` | `400` | Brak danych JSON, brakujace wymagane pola, lub walidacja parametrow nie przeszla |
| `VALIDATION_ERROR` | `400` | Wartosc parametru konfiguracji poza dopuszczalnym zakresem |
| `TRACKING_ACTIVE` | `400` | Operacja niemozliwa podczas aktywnego trackingu (kalibracja/reset) |
| `TRACKING_INACTIVE` | `400` | Operacja wymaga aktywnego trackingu (stop/pause/resume) |
| `QUEUE_EMPTY` | `400` | Kolejka obserwacji jest pusta (proba rozpoczecia trackingu) |
| `STAR_BELOW_HORIZON` | `400` | Gwiazda docelowa jest ponizej horyzontu |
| `TOKEN_MISSING` | `401` | Brak naglowka Authorization, nieprawidlowy format lub nieprawidlowy token |
| `TOKEN_EXPIRED` | `401` | Token JWT wygasl lub zostal uniewazniony (wylogowanie) |
| `INVALID_CREDENTIALS` | `401` | Nieprawidlowa nazwa uzytkownika lub haslo |
| `NOT_FOUND` | `404` | Zasob (gwiazda, obserwacja) o podanym identyfikatorze nie istnieje |
| `INTERNAL_ERROR` | `500` | Blad wewnetrzny serwera (np. brak konfiguracji teleskopu) |

### Format odpowiedzi bledow

Wszystkie bledy sa zwracane w jednolitym formacie JSON:

```json
{
    "error": "KOD_BLEDU",
    "message": "Czytelny opis problemu"
}
```

---

## Zaleznosci zewnetrzne

| Modul | Zastosowanie |
|---|---|
| `flask` | Framework webowy, Blueprint, request, jsonify |
| `flask_cors` | Obsluga CORS (Cross-Origin Resource Sharing) |
| `jwt` (PyJWT) | Kodowanie i dekodowanie tokenow JWT |
| `database.models` | Operacje na bazie danych (konfiguracja, gwiazdy, kolejka, kalibracja) |
| `tracking.position` | Obliczenia pozycji gwiazd (`calculate_alt_az`, `get_current_position`) |
| `tracking.tracker` | Petla trackingowa (`tracking_loop`) |
| `config` | Stale konfiguracyjne aplikacji |
