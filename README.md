# SeeSky Tracking

SeeSky Tracking is a control and observation interface for an amateur radio telescope on an altitude-azimuth mount. It combines astronomical coordinate calculations, a REST API, an observation queue, and a browser-based control panel.

## System overview

- Python and Flask backend with JWT authentication
- Astropy-based conversion from right ascension and declination to altitude and azimuth
- Tracking loop with start, stop, pause, resume, and predictive interpolation
- SQLite catalog built from HYG v4.1 data
- Node.js, Express, and EJS frontend
- Interactive sky map, target browser, observation queue, configuration, and calibration views

The software can run on a Raspberry Pi 4 or 5 or on a regular development computer. Hardware motor control is outside the current repository.

## Requirements

- Python 3.11 or newer
- Node.js 18 or newer
- npm

## Installation

Create and activate a Python environment from the repository root:

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Download and convert the HYG star catalog:

```bash
python scripts/download_hyg.py
python scripts/parse_catalog.py
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

## Running the system

Start the backend in one terminal:

```bash
python backend/app.py
```

Start the frontend in another terminal:

```bash
cd frontend
node server.js
```

Open `http://localhost:3000`.

The repository contains development authentication defaults. Change the JWT secret and login credentials before exposing the service to another device or network.

## Project structure

- `backend/api/` - REST endpoints and authentication
- `backend/database/` - SQLite models and generated star catalog
- `backend/tracking/` - position calculations and tracking loop
- `frontend/views/` - EJS interface
- `frontend/public/` - browser scripts, styles, and images
- `scripts/` - catalog preparation, benchmarks, and tracking tests
- `docs/` - architecture, API, tracking, and setup documentation

## Validation

The repository includes focused scripts rather than a single automated test suite:

```bash
python scripts/test_position.py
python scripts/test_tracking_loop.py
python scripts/benchmark_astropy.py
```

The tracking loop test does not require physical motors.

## Documentation

Start with the [documentation index](docs/README.md) for detailed component and API references.

## Current limitations

- No physical mount driver is included
- Deployment hardening is still required
- The interactive sky map may need additional tuning depending on browser and display size

## License

No license has been granted for this repository unless a license file states otherwise.
