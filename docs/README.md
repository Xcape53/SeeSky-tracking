# SeeSky Tracking Documentation

This directory contains the detailed technical documentation for the SeeSky radio telescope tracking system.

## Documentation map

| Document | Scope |
| --- | --- |
| [Configuration and database](backend/config-i-baza-danych.md) | Runtime settings, SQLite schema, telescope configuration, queue, and calibration data |
| [Tracking engine](backend/silnik-trackingu.md) | Coordinate conversion, atmospheric refraction, predictive interpolation, and tracking state |
| [API implementation](backend/api-routes.md) | Flask route implementation for authentication, configuration, catalog, queue, tracking, and calibration |
| [Frontend](frontend/frontend.md) | Express server, EJS interface, browser logic, sky map, and styling |
| [Utility scripts](scripts/skrypty-pomocnicze.md) | Catalog download and conversion, benchmarks, position checks, and tracking simulation |

Some linked documents retain Polish filenames and content. This index provides the English entry point while those longer documents are migrated separately.

## Architecture at a glance

1. The browser interface sends authenticated requests to the Flask API.
2. The API reads configuration and observation data from SQLite.
3. Astropy converts catalog coordinates for the configured observer location and time.
4. The tracking loop updates the desired altitude and azimuth at a fixed interval.
5. A future hardware adapter can consume those coordinates to drive the physical mount.

## Local endpoints

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5000/api`

Treat the included credentials and JWT configuration as development defaults only. Replace them before network deployment.

## Generated data

The HYG CSV and SQLite catalog are generated artifacts. Rebuild them with:

```bash
python scripts/download_hyg.py
python scripts/parse_catalog.py
```

Run these commands from the repository root.
