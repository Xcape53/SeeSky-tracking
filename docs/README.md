# SeeSky Tracking - Dokumentacja

> System sledzenia obiektow niebieskich dla radioteleskopu amatorskiego
>
> Wersja dokumentu: 1.0 | Data: 2026-03-27

---

## Przeglad systemu

SeeSky Tracking to system sledzenia obiektow niebieskich przeznaczony do pracy z radioteleskopem zamontowanym na montazu azymutalnym (alt-az). System sklada sie z trzech glownych warstw:

- **Backend** (Python 3.11 + Flask) - REST API z autentykacja JWT, silnik trackingowy oparty na bibliotece Astropy do transformacji wspolrzednych rownokowych (RA/Dec) na horyzontalne (Alt/Az) z korekcja refrakcji atmosferycznej, petla sledzenia z interpolacja predykcyjna oraz warstwa dostepu do bazy danych.
- **Frontend** (Node.js + Express) - serwer HTTP serwujacy interfejs uzytkowy oparty na szablonach EJS, z dashboardem do sterowania teleskopem, przegladarka katalogu gwiazd, kolejka obserwacji, panelem kalibracji i interaktywna mapa nieba (d3-celestial).
- **Baza danych** (SQLite) - katalog 119 626 gwiazd z katalogu HYG v4.1 (Hipparcos-Yale-Gliese), tabela konfiguracji teleskopu i kolejka obserwacji.

System zostal zaprojektowany do pracy na Raspberry Pi 4/5, ale dziala rowniez na dowolnym komputerze z Pythonem 3.11+ i Node.js 18+.

---

## Struktura dokumentacji

| Dokument | Opis |
|----------|------|
| Glowny [README.md](../README.md) | Przewodnik instalacji, uruchomienia i przeglad projektu. |
| [docs/backend/config-i-baza-danych.md](backend/config-i-baza-danych.md) | Dokumentacja warstwy konfiguracji (`config.py`) i bazy danych (`models.py`) - schemat tabel SQLite, funkcje dostepu do danych, konfiguracja teleskopu, kolejka obserwacji, kalibracja. |
| [docs/backend/silnik-trackingu.md](backend/silnik-trackingu.md) | Dokumentacja silnika trackingowego - modul obliczen pozycji (`position.py`) z transformacja wspolrzednych i korekcja refrakcji oraz petla sledzenia (`tracker.py`) z interpolacja predykcyjna i obsluga start/stop/pause. |
| [docs/backend/api-routes.md](backend/api-routes.md) | Dokumentacja implementacji endpointow REST API (`routes.py`) - 19 endpointow obejmujacych autentykacje JWT, konfiguracje teleskopu, katalog gwiazd, kolejke obserwacji, tracking i kalibracje. |
| [docs/frontend/frontend.md](frontend/frontend.md) | Dokumentacja frontendu - serwer Express (`server.js`), szablon EJS (`index.ejs`), logika klienta (`app.js`), mapa nieba (`stars-bg.js`), style CSS i zasoby statyczne. |
| [docs/scripts/skrypty-pomocnicze.md](scripts/skrypty-pomocnicze.md) | Dokumentacja skryptow pomocniczych - pobieranie katalogu HYG (`download_hyg.py`), parsowanie CSV do SQLite (`parse_catalog.py`), benchmark wydajnosci Astropy, testy obliczen pozycji i symulacja petli sledzenia. |
| [docs/api-endpoints.md](api-endpoints.md) | Referencja endpointow REST API - formaty zadan i odpowiedzi dla wszystkich 19 endpointow, kody bledow, przyklady uzycia z `curl`. |
| [docs/architecture.md](architecture.md) | Diagramy architektury systemu - schemat komunikacji komponentow, opis plikow projektu, modele danych, przeplyw danych, zastosowane technologie. |
| [docs/tracking-system.md](tracking-system.md) | Teoria i algorytmy systemu trackingowego - uklady wspolrzednych, inicjalizacja systemu, kalibracja, obliczanie pozycji, petla trackingowa, kolejka obserwacji, synchronizacja czasu, tryb offline, obsluga bledow. |

---

## Struktura projektu

```
tracking/
│
├── backend/                          # Backend Python (Flask REST API)
│   ├── app.py                        # Glowna aplikacja Flask - tworzenie i konfiguracja serwera
│   ├── config.py                     # Centralna konfiguracja (lokalizacja, porty, JWT, tracking)
│   │
│   ├── api/
│   │   ├── __init__.py               # Inicjalizacja modulu api
│   │   └── routes.py                 # 19 endpointow REST API (auth, config, stars, queue, tracking, calibration)
│   │
│   ├── database/
│   │   ├── __init__.py               # Inicjalizacja modulu database
│   │   ├── models.py                 # Warstwa dostepu do SQLite (katalog gwiazd, kolejka, konfiguracja)
│   │   └── star_catalog.db           # Baza danych SQLite z 119 626 gwiazdami (generowana przez parse_catalog.py)
│   │
│   └── tracking/
│       ├── __init__.py               # Inicjalizacja modulu tracking
│       ├── position.py               # Obliczenia astronomiczne (RA/Dec -> Alt/Az, refrakcja, haversine)
│       └── tracker.py                # Petla sledzenia z interpolacja predykcyjna (start/stop/pause)
│
├── frontend/                         # Frontend Node.js (Express + EJS)
│   ├── server.js                     # Serwer Express - renderowanie widokow i proxy API
│   ├── package.json                  # Definicja pakietu Node.js i zaleznosci (express, ejs)
│   │
│   ├── views/
│   │   └── index.ejs                 # Glowny szablon HTML - ekran logowania i dashboard z 6 zakladkami
│   │
│   └── public/
│       ├── css/
│       │   └── style.css             # Style CSS calego interfejsu
│       ├── js/
│       │   ├── app.js                # Logika klienta - komunikacja z API, nawigacja, obsluga dashboardu
│       │   └── stars-bg.js           # Animowane tlo gwiazd na ekranie logowania (canvas)
│       └── images/
│           ├── seesky.svg            # Logo SeeSky (wektorowe)
│           └── seesky.png            # Logo SeeSky (rastrowe)
│
├── scripts/                          # Skrypty pomocnicze
│   ├── download_hyg.py               # Pobieranie katalogu HYG v4.1 z GitHub (~32 MB CSV)
│   ├── parse_catalog.py              # Parsowanie CSV -> SQLite (konwersja jednostek, indeksy)
│   ├── benchmark_astropy.py          # Benchmark wydajnosci transformacji wspolrzednych
│   ├── test_position.py              # Test obliczania pozycji gwiazdy na niebie (Alt/Az)
│   ├── test_tracking_loop.py         # Symulacja petli sledzenia bez fizycznych silnikow
│   └── data/
│       └── hygdata_v41.csv           # Pobrany katalog HYG (generowany przez download_hyg.py)
│
├── docs/                             # Dokumentacja
│   ├── README.md                     # Ten plik - indeks dokumentacji
│   ├── api-endpoints.md              # Referencja REST API (formaty zadan/odpowiedzi)
│   ├── architecture.md               # Diagramy architektury systemu
│   ├── tracking-system.md            # Teoria i algorytmy trackingu
│   ├── setup/
│   │   └── instalacja-i-uruchomienie.md  # Przewodnik instalacji i uruchomienia
│   ├── backend/
│   │   ├── config-i-baza-danych.md   # Konfiguracja i warstwa bazy danych
│   │   ├── silnik-trackingu.md       # Silnik trackingowy (position.py + tracker.py)
│   │   └── api-routes.md             # Implementacja endpointow REST API
│   ├── frontend/
│   │   └── frontend.md              # Dokumentacja frontendu (serwer, UI, mapa nieba)
│   └── scripts/
│       └── skrypty-pomocnicze.md     # Dokumentacja skryptow pomocniczych
│
├── requirements.txt                  # Zaleznosci Python (astropy, flask, numpy, PyJWT, ...)
├── start_backend.bat                 # Skrypt uruchomieniowy backendu (Windows)
├── start_frontend.bat                # Skrypt uruchomieniowy frontendu (Windows)
└── venv/                             # Srodowisko wirtualne Python (generowane lokalnie)
```

---

## Technologie

### Backend

| Technologia              | Wersja  | Zastosowanie                                                   |
|--------------------------|---------|----------------------------------------------------------------|
| **Python**               | 3.11+   | Jezyk backendu                                                 |
| **Flask**                | 3.1.3   | Framework REST API                                             |
| **Astropy**              | 7.2.0   | Obliczenia astronomiczne (transformacja wspolrzednych, refrakcja, czas) |
| **NumPy**                | 2.4.3   | Obliczenia numeryczne (trygonometria, tablice)                 |
| **SQLite**               | 3.x     | Baza danych (katalog gwiazd, konfiguracja, kolejka)            |
| **PyJWT**                | 2.12.1  | Autentykacja tokenami JSON Web Token                           |
| **Flask-CORS**           | 6.0.2   | Obsluga Cross-Origin Resource Sharing                          |
| **pyerfa**               | 2.0.1.5 | Biblioteka ERFA (fundamentalne transformacje astronomiczne)    |
| **astropy-iers-data**    | 0.2026.x | Dane IERS do precyzyjnych obliczen rotacji Ziemi              |
| **certifi**              | 2026.2.25 | Certyfikaty SSL do bezpiecznych polaczen                     |
| **PyYAML**               | 6.0.3   | Parsowanie konfiguracji YAML (zaleznosc astropy)               |

### Frontend

| Technologia              | Wersja  | Zastosowanie                                                   |
|--------------------------|---------|----------------------------------------------------------------|
| **Node.js**              | 18+     | Srodowisko uruchomieniowe JavaScript                           |
| **Express**              | 5.2.1   | Framework serwera HTTP                                         |
| **EJS**                  | 5.0.1   | Silnik szablonow HTML                                          |
| **d3-celestial**         | 0.7.35  | Interaktywna mapa nieba (ladowana z CDN)                       |

### Narzedzia i dane

| Narzedzie / Dane         | Opis                                                            |
|--------------------------|-----------------------------------------------------------------|
| **Katalog HYG v4.1**    | Baza 119 626 gwiazd (Hipparcos-Yale-Gliese), zrodlo danych katalogu |
| **IERS Data**            | Tablice rotacji Ziemi do precyzyjnych obliczen czasu             |

---

## Szybki start

Aby szybko uruchomic system, postepuj zgodnie z przewodnikiem:
**[Instalacja i uruchomienie](setup/instalacja-i-uruchomienie.md)**

Najwazniejsze kroki:

1. Zainstaluj Python 3.11+ i Node.js 18+.
2. Utworz srodowisko wirtualne: `python -m venv venv` i aktywuj je.
3. Zainstaluj zaleznosci: `pip install -r requirements.txt`.
4. Pobierz i sparsuj katalog gwiazd: `cd scripts && python download_hyg.py && python parse_catalog.py`.
5. Zainstaluj frontend: `cd frontend && npm install`.
6. Uruchom backend: `cd backend && python app.py`.
7. Uruchom frontend: `cd frontend && node server.js`.
8. Otworz **http://localhost:3000** i zaloguj sie: `operator` / `seesky123`.

---

## Endpointy API - przeglad

System udostepnia 19 endpointow REST API pogrupowanych w 6 kategorii:

| Kategoria           | Endpointy                                         | Opis                                       |
|---------------------|---------------------------------------------------|--------------------------------------------|
| **Autentykacja**    | `POST /api/auth/login`, `POST /api/auth/logout`  | Logowanie JWT, wylogowanie                 |
| **Konfiguracja**    | `GET /api/config`, `PUT /api/config`              | Odczyt i modyfikacja konfiguracji teleskopu |
| **Katalog gwiazd**  | `GET /api/stars`, `GET /api/stars/:id`, `GET /api/stars/:id/position` | Przegladanie katalogu i obliczanie pozycji |
| **Kolejka obserwacji** | `GET /api/queue`, `POST /api/queue`, `PUT /api/queue/:id`, `DELETE /api/queue/:id` | Zarzadzanie kolejka obserwacji |
| **Tracking**        | `GET /api/tracking/status`, `POST /api/tracking/start`, `POST /api/tracking/stop`, `POST /api/tracking/pause`, `POST /api/tracking/resume` | Sterowanie petla sledzenia |
| **Kalibracja**      | `GET /api/calibration/status`, `POST /api/calibration/reset`, `POST /api/calibration/polaris` | Kalibracja teleskopu |

Szczegolowa dokumentacja: **[Referencja API](api-endpoints.md)**

---

## Kluczowe parametry domyslne

| Parametr                        | Wartosc                | Zrodlo          |
|---------------------------------|------------------------|-----------------|
| Lokalizacja obserwatora         | Wroclaw (51.1079 N, 17.0385 E, 120 m n.p.m.) | `config.py` |
| Interwal petli trackingowej     | 2.0 s                  | `config.py`     |
| Czas trwania obserwacji         | 30 minut               | `config.py`     |
| Cisnienie atmosferyczne         | 1013.25 hPa            | `config.py`     |
| Temperatura                     | 10.0 C                 | `config.py`     |
| Wilgotnosc wzgledna             | 0.5 (50%)              | `config.py`     |
| Dlugosc fali obserwacji         | 210 000 nm (~21 cm, linia HI wodoru) | `config.py` |
| Waznosc tokena JWT              | 3600 s (1 godzina)     | `config.py`     |
| Port backendu                   | 5000                   | `config.py`     |
| Port frontendu                  | 3000                   | `server.js`     |
