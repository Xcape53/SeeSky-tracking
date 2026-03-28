# SeeSky Tracking

System sledzenia obiektow niebieskich dla radioteleskopu amatorskiego.

## Architektura

- **Backend** (Python 3.11 + Flask) - REST API z JWT, silnik trackingowy (Astropy), SQLite z katalogiem 119 626 gwiazd (HYG v4.1)
- **Frontend** (Node.js + Express + EJS) - dashboard z 6 zakladkami: tracking, katalog gwiazd, kolejka obserwacji, konfiguracja, kalibracja, mapa nieba (d3-celestial)

## Wymagania

- Python 3.11+
- Node.js 18+

## Instalacja

```bash
# 1. Srodowisko Python
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. Katalog gwiazd
cd scripts
python download_hyg.py
python parse_catalog.py
cd ..

# 3. Frontend
cd frontend
npm install
cd ..
```

## Uruchomienie

Odpal dwa terminale (albo uzyj `start_backend.bat` i `start_frontend.bat`):

```bash
# Terminal 1 - Backend (port 5000)
cd backend
python app.py

# Terminal 2 - Frontend (port 3000)
cd frontend
node server.js
```

Otworz `http://localhost:3000` — login: `operator` / `operator123`

## Struktura projektu

```
tracking/
  backend/
    app.py              # Flask application factory
    config.py           # Konfiguracja (JWT, GPS, atmosfera)
    api/
      routes.py         # 19 endpointow REST API
    database/
      models.py         # SQLite (gwiazdy, kolejka, config)
    tracking/
      position.py       # Transformacje RA/Dec -> Alt/Az (Astropy)
      tracker.py        # Petla sledzenia z interpolacja
  frontend/
    server.js           # Express + EJS
    views/
      index.ejs         # SPA - login + dashboard
    public/
      css/style.css     # Dark theme, bordowe akcenty
      js/app.js         # Logika klienta, mapa nieba
      js/stars-bg.js    # Animowane tlo logowania
      images/           # Logo SVG/PNG
  scripts/
    download_hyg.py     # Pobieranie katalogu HYG v4.1
    parse_catalog.py    # Parsowanie CSV -> SQLite
    test_position.py    # Testy obliczen pozycji
  docs/                 # Szczegolowa dokumentacja
```

## Znane problemy (WIP)

- **Overlay mapy nieba** - pierscienie elewacji i horyzont na mapie d3-celestial nie renderuja sie poprawnie (problem z mapowaniem wspolrzednych projekcji SVG na canvas overlay). Wbudowany horyzont d3-celestial dziala poprawnie.

## Dokumentacja

Szczegolowa dokumentacja znajduje sie w folderze [docs/](docs/README.md).

## Licencja

Projekt studencki - SeeSky.
