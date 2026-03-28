# Silnik trackingowy -- dokumentacja modulu obliczen i petli sledzenia

> Wersja dokumentu: 1.0
> Projekt studencki SeeSky
> Data: 2026-03-27

---

## Spis tresci

1. [Wprowadzenie](#1-wprowadzenie)
2. [Modul obliczen astronomicznych -- `position.py`](#2-modul-obliczen-astronomicznych----positionpy)
   - 2.1 [calculate_alt_az()](#21-calculate_alt_az)
   - 2.2 [get_current_position()](#22-get_current_position)
   - 2.3 [angular_distance()](#23-angular_distance)
   - 2.4 [normalize_delta_az()](#24-normalize_delta_az)
   - 2.5 [is_above_horizon()](#25-is_above_horizon)
3. [Petla trackingowa -- `tracker.py`](#3-petla-trackingowa----trackerpy)
   - 3.1 [Wzorzec Singleton](#31-wzorzec-singleton)
   - 3.2 [Klasa TrackingLoop](#32-klasa-trackingloop)
   - 3.3 [Wlasciwosci (properties)](#33-wlasciwosci-properties)
   - 3.4 [\_\_init\_\_()](#34-__init__)
   - 3.5 [start()](#35-start)
   - 3.6 [stop()](#36-stop)
   - 3.7 [pause()](#37-pause)
   - 3.8 [resume()](#38-resume)
   - 3.9 [get_status()](#39-get_status)
   - 3.10 [_loop()](#310-_loop)
4. [Interpolacja predykcyjna](#4-interpolacja-predykcyjna)
5. [Przeplyw danych w jednym cyklu petli](#5-przeplyw-danych-w-jednym-cyklu-petli)
6. [Parametry atmosferyczne i refrakcja](#6-parametry-atmosferyczne-i-refrakcja)
7. [Offsety kalibracyjne](#7-offsety-kalibracyjne)
8. [Bezpieczenstwo watkow](#8-bezpieczenstwo-watkow)

---

## 1. Wprowadzenie

Silnik trackingowy to rdzen systemu SeeSky. Sklada sie z dwoch plikow Pythona znajdujacych sie w katalogu `backend/tracking/`:

| Plik | Odpowiedzialnosc |
|------|------------------|
| `position.py` | Obliczenia astronomiczne -- transformacja wspolrzednych rownokowych (RA/Dec) na horyzontalne (Alt/Az), odleglosc katowa, normalizacja katow |
| `tracker.py` | Petla sledzenia -- cykliczne przeliczanie pozycji celu, generowanie delt katowych i predkosci katowych dla silnikow teleskopu |

`position.py` dostarcza czyste funkcje obliczeniowe bez stanu. `tracker.py` korzysta z tych funkcji wewnatrz petli dzialjacej w osobnym watku, zarzadzajac stanem obserwacji (start, stop, pauza, wznowienie).

Razem te dwa moduly realizuja pelny cykl: od wspolrzednych katalogowych gwiazdy (rektascensja, deklinacja) do konkretnych przyrostow katowych, ktore sterownik silnikow moze bezposrednio wykorzystac do obrotu czaszy teleskopu.

---

## 2. Modul obliczen astronomicznych -- `position.py`

Plik: `backend/tracking/position.py`

Zaleznosci zewnetrzne:
- `astropy` -- biblioteka astronomiczna (SkyCoord, EarthLocation, AltAz, Time, jednostki)
- `numpy` -- obliczenia numeryczne (haversine)

### 2.1 calculate_alt_az()

Glowna funkcja transformacji wspolrzednych. Przelicza pozycje obiektu niebieskiego z ukladu rownokowego (ICRS) na uklad horyzontalny obserwatora z uwzglednieniem refrakcji atmosferycznej.

**Sygnatura:**

```python
def calculate_alt_az(
    ra: float,
    dec: float,
    lat: float,
    lon: float,
    alt: float,
    obs_time: Time | None = None,
    pressure: float = 1013.25,
    temperature: float = 10.0,
    humidity: float = 0.5,
    wavelength: float = 210000.0,
) -> tuple[float, float]
```

**Parametry:**

| Parametr | Typ | Domyslna | Opis |
|----------|-----|----------|------|
| `ra` | `float` | -- | Rektascensja obiektu w stopniach (0--360) |
| `dec` | `float` | -- | Deklinacja obiektu w stopniach (-90 do +90) |
| `lat` | `float` | -- | Szerokosc geograficzna obserwatora w stopniach |
| `lon` | `float` | -- | Dlugosc geograficzna obserwatora w stopniach |
| `alt` | `float` | -- | Wysokosc n.p.m. obserwatora w metrach |
| `obs_time` | `Time \| None` | `None` | Czas obserwacji jako obiekt `astropy.time.Time`. Jesli `None`, uzywany jest czas biezacy (`Time.now()`) |
| `pressure` | `float` | `1013.25` | Cisnienie atmosferyczne w hPa (hektopaskalach) |
| `temperature` | `float` | `10.0` | Temperatura powietrza w stopniach Celsjusza |
| `humidity` | `float` | `0.5` | Wilgotnosc wzgledna powietrza (0.0--1.0) |
| `wavelength` | `float` | `210000.0` | Dlugosc fali obserwacji w nanometrach. Wartosc domyslna 210 000 nm = 21 cm, co odpowiada linii wodoru HI, typowej dla radioteleskopow |

**Zwraca:** `tuple[float, float]` -- krotka `(altitude_deg, azimuth_deg)`, gdzie:
- `altitude_deg` -- wysokosc nad horyzontem w stopniach (ujemna = pod horyzontem)
- `azimuth_deg` -- azymut w stopniach (0 = polnoc, 90 = wschod, 180 = poludnie, 270 = zachod)

**Logika krok po kroku:**

1. Jesli `obs_time` jest `None`, ustaw go na `Time.now()` (biezacy czas UTC).
2. Utworz obiekt `SkyCoord` w ukladzie ICRS (International Celestial Reference System) z podanym RA i Dec, przeliczonymi na stopnie astropy (`u.deg`).
3. Utworz obiekt `EarthLocation` z wspolrzednych geograficznych obserwatora (lat, lon, height).
4. Utworz ramke odniesienia `AltAz` z:
   - czasem obserwacji (`obstime`),
   - lokalizacja obserwatora (`location`),
   - parametrami atmosferycznymi: cisnienie (`pressure`), temperatura (`temperature`), wilgotnosc wzgledna (`relative_humidity`), dlugosc fali (`obswl`).
5. Przetransformuj obiekt `SkyCoord` do ramki `AltAz` za pomoca `target.transform_to(altaz_frame)`.
6. Zwroc krotke dwoch wartosci `float`: `(result.alt.deg, result.az.deg)`.

**Przyklad uzycia:**

```python
from astropy.time import Time
from tracking.position import calculate_alt_az

alt, az = calculate_alt_az(
    ra=83.633,        # Betelgeza
    dec=22.014,
    lat=51.1,         # Wroclaw
    lon=17.033,
    alt=120.0,
    obs_time=Time("2026-03-27T20:00:00", scale="utc"),
)
print(f"Wysokosc: {alt:.4f} deg, Azymut: {az:.4f} deg")
```

---

### 2.2 get_current_position()

Funkcja wyzszego poziomu. Oblicza biezaca pozycje gwiazdy na niebie, stosujac parametry z konfiguracji teleskopu oraz offsety kalibracyjne.

**Sygnatura:**

```python
def get_current_position(star: dict, cfg: dict) -> dict
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `star` | `dict` | Slownik opisujacy gwiazde. Wymagane klucze: `ra` (float), `dec` (float) |
| `cfg` | `dict` | Slownik konfiguracji teleskopu. Wymagane klucze: `latitude`, `longitude`, `altitude`. Opcjonalne: `pressure`, `temperature`, `humidity`, `wavelength`, `calibration_offset_az`, `calibration_offset_alt` |

**Zwraca:** `dict` o strukturze:

```python
{
    "alt": float,              # wysokosc w stopniach (zaokraglona do 4 miejsc)
    "az": float,               # azymut w stopniach (zaokraglony do 4 miejsc)
    "is_above_horizon": bool,  # True jesli alt > 0
    "calculated_at": str,      # czas obliczenia w formacie ISO (np. "2026-03-27 20:00:00.000")
}
```

**Logika krok po kroku:**

1. Pobierz biezacy czas obserwacji: `obs_time = Time.now()`.
2. Wywolaj `calculate_alt_az()` z parametrami gwiazdy (`star["ra"]`, `star["dec"]`), lokalizacja z konfiguracji (`cfg["latitude"]`, `cfg["longitude"]`, `cfg["altitude"]`) oraz parametrami atmosferycznymi z konfiguracji (z wartosciami domyslnymi jesli brak).
3. Dodaj offsety kalibracyjne do wynikow:
   - `az_deg += cfg.get("calibration_offset_az", 0.0)`
   - `alt_deg += cfg.get("calibration_offset_alt", 0.0)`
4. Zwroc slownik z zaokraglonymi wartosciami (`round(..., 4)`), flaga `is_above_horizon` i znacznikiem czasu w formacie ISO.

**Uwaga:** Flaga `is_above_horizon` jest obliczana po zastosowaniu offsetow kalibracyjnych. Oznacza to, ze jesli offset kalibracyjny przesunie wartosc altitude ponizej zera, gwiazda zostanie oznaczona jako ponizej horyzontu -- jest to zamierzone zachowanie, poniewaz offset kalibracyjny koryguje rzeczywisty blad montazu.

---

### 2.3 angular_distance()

Oblicza odleglosc katowa miedzy dwoma punktami na sferze niebieskiej przy uzyciu formuly haversine. Przydatna do okreslenia, jak daleko teleskop musi sie obrocic.

**Sygnatura:**

```python
def angular_distance(alt1: float, az1: float, alt2: float, az2: float) -> float
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `alt1` | `float` | Wysokosc pierwszego punktu w stopniach |
| `az1` | `float` | Azymut pierwszego punktu w stopniach |
| `alt2` | `float` | Wysokosc drugiego punktu w stopniach |
| `az2` | `float` | Azymut drugiego punktu w stopniach |

**Zwraca:** `float` -- odleglosc katowa w stopniach (zawsze >= 0).

**Logika krok po kroku:**

1. Przelicz wszystkie katy ze stopni na radiany (`np.radians()`).
2. Oblicz roznice katowe: `dalt = alt2 - alt1`, `daz = az2 - az1` (juz w radianach).
3. Zastosuj formule haversine:
   - `a = sin(dalt/2)^2 + cos(alt1) * cos(alt2) * sin(daz/2)^2`
   - `c = 2 * arctan2(sqrt(a), sqrt(1 - a))`
4. Przelicz wynik z radianow na stopnie i zwroc jako `float`.

**Uwaga:** Formula haversine zapewnia poprawne obliczenia nawet dla bardzo malych i bardzo duzych odleglosci katowych, unikajac problemow numerycznych, ktore wystepuja w prostszych wzorach.

---

### 2.4 normalize_delta_az()

Normalizuje roznice azymutu do zakresu [-180, +180] stopni. Jest to kluczowe dla poprawnego sterowania silnikiem azymutu -- gwarantuje, ze silnik zawsze obraca sie najkrotsza droga.

**Sygnatura:**

```python
def normalize_delta_az(delta: float) -> float
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `delta` | `float` | Roznica azymutu w stopniach (dowolna wartosc) |

**Zwraca:** `float` -- znormalizowana roznica w zakresie [-180, +180].

**Logika krok po kroku:**

1. Dopoki `delta > 180`: odejmij 360.
2. Dopoki `delta < -180`: dodaj 360.
3. Zwroc znormalizowana wartosc.

**Przyklad:**

| Wejscie | Wyjscie | Interpretacja |
|---------|---------|---------------|
| `350` | `-10` | Obroc 10 stopni w lewo zamiast 350 w prawo |
| `-200` | `160` | Obroc 160 stopni w prawo zamiast 200 w lewo |
| `45` | `45` | Bez zmiany, juz w zakresie |
| `-180` | `-180` | Wartosc graniczna |

---

### 2.5 is_above_horizon()

Prosta funkcja sprawdzajaca, czy obiekt jest nad horyzontem.

**Sygnatura:**

```python
def is_above_horizon(alt_deg: float) -> bool
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `alt_deg` | `float` | Wysokosc obiektu nad horyzontem w stopniach |

**Zwraca:** `bool` -- `True` jesli `alt_deg > 0`, `False` w przeciwnym razie.

**Uwaga:** Wartosc `alt_deg == 0` (dokladnie na horyzoncie) zwraca `False`. W praktyce obserwacje obiektow blisko horyzontu sa utrudnione ze wzgledu na silna refrakcje i absorpcje atmosferyczna, wiec jest to bezpieczne zachowanie.

---

## 3. Petla trackingowa -- `tracker.py`

Plik: `backend/tracking/tracker.py`

Zaleznosci zewnetrzne:
- `threading` -- wielowatkowosc (watek demona dla petli)
- `time` -- pomiar czasu, usypianie
- `datetime` -- znaczniki czasowe
- `astropy.time.Time` -- precyzyjny czas astronomiczny
- `astropy.units` -- jednostki (sekundy)

Zaleznosci wewnetrzne:
- `tracking.position.calculate_alt_az` -- transformacja wspolrzednych
- `tracking.position.normalize_delta_az` -- normalizacja azymutu
- `tracking.position.angular_distance` -- odleglosc katowa (zaimportowana, dostepna do uzycia)

---

### 3.1 Wzorzec Singleton

Na koncu pliku `tracker.py` znajduje sie linia:

```python
tracking_loop = TrackingLoop()
```

Jest to instancja singletona -- jeden obiekt `TrackingLoop` na caly backend. Kazdy modul, ktory importuje `tracking_loop`, otrzymuje ten sam obiekt:

```python
from tracking.tracker import tracking_loop
```

**Dlaczego singleton?** System SeeSky obsluguje jeden fizyczny teleskop z jednym zestawem silnikow. Nie ma sensu uruchamiac wielu petli sledzenia jednoczesnie -- spowodowalby to konflikty sterowania silnikami. Singleton gwarantuje, ze istnieje dokladnie jedna petla trackingowa w calym procesie backendu.

**Uwaga:** Jest to tzw. "module-level singleton" -- nie uzywa dekoratora ani metaklasy. Instancja jest tworzona raz, przy pierwszym imporcie modulu. Watek Pythona (GIL) zapewnia, ze import jest atomowy.

---

### 3.2 Klasa TrackingLoop

Glowna klasa silnika sledzenia. Zarzadza cyklem zycia obserwacji: start, pauza, wznowienie, stop. Petla sledzenia dziala w osobnym watku demona.

**Stan wewnetrzny:**

| Pole | Typ | Opis |
|------|-----|------|
| `_thread` | `Thread \| None` | Referencja do watku petli |
| `_running` | `bool` | Flaga: czy petla jest aktywna |
| `_paused` | `bool` | Flaga: czy petla jest wstrzymana |
| `_lock` | `threading.Lock` | Blokada dla bezpieczenstwa watkowego |
| `observation` | `dict \| None` | Dane biezacej obserwacji |
| `current_alt` | `float` | Biezaca wysokosc teleskopu (stopnie) |
| `current_az` | `float` | Biezacy azymut teleskopu (stopnie) |
| `target_alt` | `float \| None` | Docelowa wysokosc (stopnie) |
| `target_az` | `float \| None` | Docelowy azymut (stopnie) |
| `delta_alt` | `float \| None` | Roznica wysokosci do pokonania (stopnie) |
| `delta_az` | `float \| None` | Roznica azymutu do pokonania (stopnie) |
| `velocity_alt` | `float` | Predkosc katowa w elewacji (stopnie/s) |
| `velocity_az` | `float` | Predkosc katowa w azymucie (stopnie/s) |
| `start_time` | `float \| None` | Znacznik czasu startu (`time.time()`) |
| `elapsed_seconds` | `int` | Czas trwania obserwacji w sekundach |
| `_cfg` | `dict` | Konfiguracja teleskopu (ustawiana przy starcie) |

---

### 3.3 Wlasciwosci (properties)

```python
@property
def is_tracking(self) -> bool
```

Zwraca `True` jesli petla sledzenia jest aktywna (`_running == True`). Read-only.

```python
@property
def is_paused(self) -> bool
```

Zwraca `True` jesli petla jest wstrzymana (`_paused == True`). Read-only.

---

### 3.4 \_\_init\_\_()

**Sygnatura:**

```python
def __init__(self)
```

**Parametry:** Brak.

**Logika krok po kroku:**

1. Ustaw `_thread = None` (brak watku).
2. Ustaw `_running = False` (petla nieaktywna).
3. Ustaw `_paused = False` (brak pauzy).
4. Utworz blokade watkowa: `_lock = threading.Lock()`.
5. Zainicjalizuj pola stanu domyslnymi wartosciami:
   - `observation = None`
   - `current_alt = 0.0`, `current_az = 0.0`
   - `target_alt = None`, `target_az = None`
   - `delta_alt = None`, `delta_az = None`
   - `velocity_alt = 0.0`, `velocity_az = 0.0`
   - `start_time = None`
   - `elapsed_seconds = 0`
6. Zainicjalizuj pusty slownik konfiguracji: `_cfg = {}`.

---

### 3.5 start()

Rozpoczyna nowa sesje sledzenia obiektu niebieskiego. Oblicza poczatkowa pozycje, ustawia stan i uruchamia watek demona z petla `_loop()`.

**Sygnatura:**

```python
def start(self, observation: dict, cfg: dict) -> None
```

**Parametry:**

| Parametr | Typ | Opis |
|----------|-----|------|
| `observation` | `dict` | Dane obserwacji. Wymagane klucze: `ra` (float), `dec` (float), `duration_minutes` (float/int), `id` albo `star_id` (identyfikator). Opcjonalnie: `star_name`, `proper_name` |
| `cfg` | `dict` | Konfiguracja teleskopu. Wymagane: `latitude`, `longitude`, `altitude`. Opcjonalne: `pressure`, `temperature`, `humidity`, `wavelength`, `calibration_offset_az`, `calibration_offset_alt`, `tracking_interval_seconds` |

**Zwraca:** `None`

**Wyrzuca:** `RuntimeError("Tracking jest juz aktywny")` jesli petla juz dziala.

**Logika krok po kroku:**

1. Uzyskaj blokade `_lock`.
2. Sprawdz czy `_running == True`. Jesli tak -- wyrzuc `RuntimeError`.
3. Zapisz `observation` i `cfg` w polach instancji.
4. Oblicz poczatkowa pozycje celu wywolujac `calculate_alt_az()` z parametrami z `observation` (RA, Dec) i `cfg` (lokalizacja, parametry atmosferyczne). Czas obserwacji nie jest podany -- uzyty zostanie `Time.now()`.
5. Zastosuj offsety kalibracyjne:
   - `az += cfg.get("calibration_offset_az", 0.0)`
   - `alt += cfg.get("calibration_offset_alt", 0.0)`
6. Ustaw stan poczatkowy:
   - `current_alt = alt`, `current_az = az` (teleskop "jest" w pozycji celu)
   - `target_alt = alt`, `target_az = az` (cel jest tam, gdzie teleskop)
   - `delta_alt = 0.0`, `delta_az = 0.0` (brak roznicy -- poczatek)
   - `start_time = time.time()` (znacznik startu)
   - `elapsed_seconds = 0`
   - `_running = True`
   - `_paused = False`
7. Zwolnij blokade.
8. Utworz nowy watek demona (`daemon=True`) z funkcja docelowa `_loop`.
9. Uruchom watek.

**Uwaga:** Watek jest demonem -- zakonczy sie automatycznie gdy zakonczy sie proces glowny. Nie jest wymagane reczne zatrzymywanie watku przy zamykaniu aplikacji.

---

### 3.6 stop()

Zatrzymuje biezaca sesje sledzenia. Czeka na zakonczenie watku i zwraca podsumowanie obserwacji.

**Sygnatura:**

```python
def stop(self) -> dict
```

**Parametry:** Brak.

**Zwraca:** `dict` o strukturze:

```python
{
    "elapsed_time": int,            # czas trwania obserwacji w sekundach
    "status": "stopped",            # zawsze "stopped"
    "observation_id": str | None,   # identyfikator obserwacji (obs["id"]) lub None
}
```

**Wyrzuca:** `RuntimeError("Tracking nie jest aktywny")` jesli petla nie jest aktywna.

**Logika krok po kroku:**

1. Uzyskaj blokade `_lock`.
2. Sprawdz czy `_running == False`. Jesli tak -- wyrzuc `RuntimeError`.
3. Ustaw `_running = False` (sygnalizacja zakonczenia dla petli).
4. Ustaw `_paused = False`.
5. Zwolnij blokade.
6. Jesli `_thread` istnieje, wywolaj `_thread.join(timeout=5)` -- czekaj maksymalnie 5 sekund na zakonczenie watku.
7. Zapisz `elapsed_seconds` i `observation` do zmiennych lokalnych.
8. Wyzeruj stan:
   - `observation = None`
   - `target_alt = None`, `target_az = None`
   - `delta_alt = None`, `delta_az = None`
9. Zwroc slownik podsumowania.

**Uwaga:** Pola `current_alt` i `current_az` nie sa zerowane -- zachowuja ostatnia znana pozycje teleskopu. Moze to byc uzyteczne dla nastepnej sesji (np. do obliczenia obrotu potrzebnego do nowego celu).

---

### 3.7 pause()

Wstrzymuje sledzenie. Petla nadal dziala (watek nie jest zatrzymywany), ale pomija obliczenia pozycji -- silniki pozostaja w miejscu.

**Sygnatura:**

```python
def pause(self) -> None
```

**Parametry:** Brak.

**Zwraca:** `None`

**Wyrzuca:**
- `RuntimeError("Tracking nie jest aktywny")` jesli petla nie dziala.
- `RuntimeError("Tracking jest juz wstrzymany")` jesli pauza jest juz aktywna.

**Logika krok po kroku:**

1. Uzyskaj blokade `_lock`.
2. Walidacja: sprawdz `_running` i `_paused`.
3. Ustaw `_paused = True`.
4. Zwolnij blokade.

**Uwaga:** Podczas pauzy czas obserwacji (`elapsed_seconds`) nadal plynie. Oznacza to, ze obserwacja zakonczy sie po swoim przeznaczonym czasie niezaleznie od dlugosci pauzy. Jest to swiadoma decyzja projektowa -- czas astronomiczny nie czeka.

---

### 3.8 resume()

Wznawia sledzenie po pauzie. Obliczenia pozycji zostana podjete w nastepnym cyklu petli.

**Sygnatura:**

```python
def resume(self) -> None
```

**Parametry:** Brak.

**Zwraca:** `None`

**Wyrzuca:**
- `RuntimeError("Tracking nie jest aktywny")` jesli petla nie dziala.
- `RuntimeError("Tracking nie jest wstrzymany")` jesli pauza nie jest aktywna.

**Logika krok po kroku:**

1. Uzyskaj blokade `_lock`.
2. Walidacja: sprawdz `_running` i `_paused`.
3. Ustaw `_paused = False`.
4. Zwolnij blokade.

---

### 3.9 get_status()

Zwraca kompletny zrzut stanu petli sledzenia. Uzywany przez endpointy REST API do raportowania statusu do frontendu.

**Sygnatura:**

```python
def get_status(self) -> dict
```

**Parametry:** Brak.

**Zwraca:** `dict` o strukturze:

```python
{
    "is_tracking": bool,            # czy petla jest aktywna
    "is_paused": bool,              # czy petla jest wstrzymana
    "current_star": {               # dane sledzonej gwiazdy (None jesli brak obserwacji)
        "id": str | int,            # identyfikator gwiazdy (star_id)
        "name": str | None,         # nazwa gwiazdy (star_name lub proper_name)
        "ra": float,                # rektascensja w stopniach
        "dec": float,               # deklinacja w stopniach
    } | None,
    "current_alt": float,           # biezaca wysokosc teleskopu (4 miejsca po przecinku)
    "current_az": float,            # biezacy azymut teleskopu (4 miejsca po przecinku)
    "target_alt": float | None,     # docelowa wysokosc (4 miejsca) lub None
    "target_az": float | None,      # docelowy azymut (4 miejsca) lub None
    "elapsed_time": int,            # czas od startu obserwacji w sekundach
    "remaining_time": int | None,   # pozostaly czas w sekundach lub None
    "delta_alt": float | None,      # delta elewacji (6 miejsc) lub None
    "delta_az": float | None,       # delta azymutu (6 miejsc) lub None
    "velocity_alt": float,          # predkosc katowa elewacji w stopniach/s (6 miejsc)
    "velocity_az": float,           # predkosc katowa azymutu w stopniach/s (6 miejsc)
}
```

**Logika krok po kroku:**

1. Uzyskaj blokade `_lock`.
2. Odczytaj `observation`. Jesli istnieje, oblicz:
   - `duration = observation["duration_minutes"] * 60` (czas trwania w sekundach)
   - `remaining = max(0, duration - elapsed_seconds)` (pozostaly czas)
3. Zbuduj slownik `current_star` z pol obserwacji (`star_id`, `star_name` / `proper_name`, `ra`, `dec`). Jesli brak obserwacji -- `None`.
4. Zaokraglij wartosci:
   - `current_alt`, `current_az`, `target_alt`, `target_az` -- do 4 miejsc po przecinku
   - `delta_alt`, `delta_az`, `velocity_alt`, `velocity_az` -- do 6 miejsc po przecinku
5. Zwroc kompletny slownik.
6. Zwolnij blokade.

**Uwaga:** Nazwa gwiazdy jest pobierana z klucza `star_name` lub `proper_name` (w tej kolejnosci). To zachowanie uwzglednia rozne formaty danych wejsciowych.

---

### 3.10 _loop()

Glowna petla sledzenia. Metoda prywatna, uruchamiana w watku demona przez `start()`. Cyklicznie oblicza pozycje celu, wyznacza delty katowe i predkosci katowe dla silnikow.

**Sygnatura:**

```python
def _loop(self) -> None
```

**Parametry:** Brak (metoda wewnetrzna, odczytuje stan z `self`).

**Zwraca:** `None`

**Logika krok po kroku:**

1. **Inicjalizacja:**
   - Odczytaj interwal z konfiguracji: `interval = cfg.get("tracking_interval_seconds", 2.0)` (domyslnie 2 sekundy).
   - Oblicz calkowity czas obserwacji: `duration_s = observation["duration_minutes"] * 60`.
   - Przygotuj slownik parametrow atmosferycznych (`pressure`, `temperature`, `humidity`, `wavelength`) z wartosciami domyslnymi.
   - Ustaw znacznik nastepnego kroku: `next_step = time.time()`.

2. **Petla glowna** (`while self._running`):

   a. **Aktualizacja czasu:** Oblicz `elapsed_seconds = int(now - start_time)`.

   b. **Sprawdzenie czasu trwania:** Jesli `elapsed_seconds >= duration_s`, ustaw `_running = False` (pod blokada) i przerwij petle. Obserwacja zakonczyla sie naturalnie.

   c. **Oczekiwanie na nastepny krok:** Jesli `now < next_step`, usypiaj w kawalkach po maksymalnie 0.5 sekundy. Kroki po 0.5s (zamiast jednego dlugiego `sleep`) pozwalaja szybko zareagowac na `stop()` -- po kazdym snie sprawdzany jest `_running`. Jesli `_running == False`, petla konczy sie natychmiast.

   d. **Przesuniecie nastepnego kroku:** `next_step += interval`.

   e. **Sprawdzenie pauzy:** Jesli `_paused == True`, pomin obliczenia i wroc na poczatek petli.

   f. **Obliczenie biezacej pozycji celu:**
      - Pobierz biezacy czas: `obs_time = Time.now()`.
      - Wywolaj `calculate_alt_az()` z RA/Dec obserwowanego obiektu, lokalizacja i parametrami atmosferycznymi.
      - Zastosuj offsety kalibracyjne do wyniku.
      - Wynik: `alt_cel`, `az_cel` -- pozycja celu TERAZ.

   g. **Interpolacja predykcyjna:**
      - Oblicz czas za jeden interwal: `obs_time_next = obs_time + interval * u.s`.
      - Wywolaj `calculate_alt_az()` dla tego przyszlego czasu.
      - Zastosuj offsety kalibracyjne.
      - Wynik: `alt_pred`, `az_pred` -- przewidywana pozycja celu za `interval` sekund.

   h. **Aktualizacja stanu** (pod blokada `_lock`):
      - **Delty:** Roznica miedzy pozycja celu a biezaca pozycja teleskopu:
        - `delta_alt = alt_cel - current_alt`
        - `delta_az = normalize_delta_az(az_cel - current_az)`
      - **Predkosci katowe:** Tempo zmian pozycji celu:
        - `velocity_alt = (alt_pred - alt_cel) / interval` [stopnie/s]
        - `velocity_az = normalize_delta_az(az_pred - az_cel) / interval` [stopnie/s]
      - **Pozycja:** Aktualizuj `target_alt`, `target_az` na pozycje celu. Aktualizuj `current_alt`, `current_az` rowniez na pozycje celu (zakladamy, ze silnik nadaza).

**Mechanizm usypiania w kawalkach po 0.5s:**

```
Interwal = 2.0s

time  0.0s  petla: oblicz, zaktualizuj, next_step = 2.0
time  0.1s  sleep(0.5), sprawdz _running
time  0.6s  sleep(0.5), sprawdz _running
time  1.1s  sleep(0.5), sprawdz _running
time  1.6s  sleep(0.4), sprawdz _running   <-- min(0.4, 0.5) = 0.4
time  2.0s  petla: oblicz, zaktualizuj, next_step = 4.0
...
```

Uzytkownik wola `stop()` w chwili 1.3s -- najblizsze wybudzenie nastapi w okolicy 1.6s (najwyzej 0.5s opoznienia). Bez tego mechanizmu, przy interwale np. 5s, petla mogłaby czekac nawet 5s zanim zareaguje na `stop()`.

---

## 4. Interpolacja predykcyjna

Interpolacja predykcyjna to kluczowy mechanizm petli trackingowej. W kazdym cyklu petla oblicza pozycje celu w **dwoch** momentach czasu:

1. **Teraz** (`obs_time = Time.now()`) -- pozycja celu w biezacej chwili.
2. **Za interwal** (`obs_time + interval * u.s`) -- przewidywana pozycja celu za `interval` sekund (np. za 2s).

Na podstawie tych dwoch pomiarow obliczane sa:

### Delty katowe (delta_alt, delta_az)

Roznica miedzy pozycja celu (teraz) a biezaca pozycja teleskopu:

```
delta_alt = alt_cel - current_alt
delta_az  = normalize(az_cel - current_az)
```

Delty mowia silnikom: "o ile musisz sie teraz obrocic, zeby wskazywac na cel".

### Predkosci katowe (velocity_alt, velocity_az)

Tempo, w jakim cel przemieszcza sie po niebie:

```
velocity_alt = (alt_pred - alt_cel) / interval   [stopnie/s]
velocity_az  = normalize(az_pred - az_cel) / interval   [stopnie/s]
```

Predkosci mowia silnikom: "w jakim tempie musisz sie obracac, zeby nadazac za celem".

### Dlaczego to jest potrzebne?

Gwiazdy pozornie przemieszczaja sie po niebie z powodu obrotu Ziemi (ok. 15 stopni/godzine, ale ruch w ukladzie Alt/Az jest nieliniowy i zalezy od deklinacji i pozycji na niebie). Bez predkosci katowej silnik obracalby sie "skokowo" -- co 2 sekundy natychmiastowy skok do nowej pozycji. Z predkosciami katowymi sterownik silnikow moze interpolowac ruch miedzy kolejnymi aktualizacjami, zapewniajac plynne sledzenie.

### Schemat dzialania

```
czas:       t           t + interval
            |           |
pozycja:    alt_cel     alt_pred
            az_cel      az_pred
            |           |
            +----+------+
                 |
          velocity = (pred - cel) / interval
                 |
          delta  = cel - current (teleskop)
```

Sterownik silnikow otrzymuje:
- `delta` -- natychmiastowa korekta pozycji
- `velocity` -- predkosc, z jaka ma kontynuowac ruch do nastepnej aktualizacji

---

## 5. Przeplyw danych w jednym cyklu petli

Ponizszy schemat ilustruje pelny przeplyw danych w jednym cyklu petli trackingowej:

```
+------------------+
|  RA, Dec gwiazdy |  (ze slownika observation)
+--------+---------+
         |
         v
+--------+---------+    +-------------------+    +-----------------------+
| calculate_alt_az | <--| lat, lon, alt     | <--| Konfiguracja (cfg)    |
| (obs_time = now) |    | pressure, temp    |    | Parametry teleskop.   |
+--------+---------+    | humidity, wavelen.|    +-----------------------+
         |              +-------------------+
         v
+--------+---------+
| + offsety kalib. |  calibration_offset_az, calibration_offset_alt
+--------+---------+
         |
         v
    alt_cel, az_cel  ----+
         |               |
         v               |
+--------+---------+     |      +------------------+
| calculate_alt_az |     +----->| delta_alt =      |
| (obs_time+inter.)|           | alt_cel - current |
+--------+---------+     +---->| delta_az =        |
         |               |     | norm(az_cel-curr) |
         v               |     +------------------+
    alt_pred, az_pred     |
         |                |     +------------------+
         +--------------->+---->| velocity_alt =   |
                                | (pred-cel)/inter |
                                | velocity_az =    |
                                | norm(pred-cel)/i |
                                +------------------+
```

---

## 6. Parametry atmosferyczne i refrakcja

Biblioteka astropy uwzglednia refrakcje atmosferyczna przy transformacji wspolrzednych. Refrakcja powoduje, ze obiekty blisko horyzontu wydaja sie wyzej niz sa w rzeczywistosci. Efekt ten zalezy od:

| Parametr | Domyslna | Jednostka | Wplyw na refrakcje |
|----------|----------|-----------|-------------------|
| `pressure` | 1013.25 | hPa | Wyzsze cisnienie = silniejsza refrakcja |
| `temperature` | 10.0 | stopnie C | Nizsza temperatura = silniejsza refrakcja |
| `humidity` | 0.5 | 0.0--1.0 | Wyzej wilgotnosc = nieznaczna zmiana |
| `wavelength` | 210000.0 | nm (= 21 cm) | Dlugosc fali obserwacji. 21 cm = linia wodoru HI |

**Uwaga o dlugosci fali:** Wartosc domyslna 210 000 nm (21 cm) odpowiada linii wodorowej HI, ktora jest typowa czestotliwoscia obserwacyjna radioteleskopow amatorskich. Refrakcja dla fal radiowych jest inna niz dla swiatla widzialnego. Astropy oblicza ja na podstawie modelu atmosfery z uwzglednieniem podanej dlugosci fali.

---

## 7. Offsety kalibracyjne

System obsluguje dwa offsety kalibracyjne zapisane w konfiguracji:

| Klucz konfiguracji | Domyslna | Opis |
|---------------------|----------|------|
| `calibration_offset_az` | `0.0` | Stala poprawka do azymutu (stopnie) |
| `calibration_offset_alt` | `0.0` | Stala poprawka do elewacji (stopnie) |

Offsety sa **dodawane** do obliczonej pozycji:

```python
az_deg += cfg.get("calibration_offset_az", 0.0)
alt_deg += cfg.get("calibration_offset_alt", 0.0)
```

**Cel:** Kompensacja stalych bledow montazu teleskopu. Na przyklad, jesli podstawa teleskopu nie jest idealnie wypoziomowana, offsety pozwalaja skorygowac systematyczne przesuniecie.

**Gdzie sa stosowane:**
- W `get_current_position()` (position.py)
- W `start()` (tracker.py) -- przy obliczaniu pozycji poczatkowej
- W `_loop()` (tracker.py) -- w kazdym cyklu petli, zarowno dla pozycji biezacej (`alt_cel`, `az_cel`), jak i predykcyjnej (`alt_pred`, `az_pred`)

---

## 8. Bezpieczenstwo watkow

Petla trackingowa dziala w osobnym watku (daemon thread), co wymaga synchronizacji dostepu do wspoldzielonych danych. Uzywany jest `threading.Lock`:

**Operacje chronione blokada (`with self._lock`):**

| Metoda | Co jest chronione |
|--------|-------------------|
| `start()` | Walidacja `_running`, ustawianie calego stanu poczatkowego |
| `stop()` | Walidacja `_running`, ustawianie flag |
| `pause()` | Walidacja i ustawianie `_paused` |
| `resume()` | Walidacja i ustawianie `_paused` |
| `get_status()` | Odczyt wszystkich pol stanu |
| `_loop()` | Aktualizacja delt, predkosci, pozycji -- w kazdym cyklu |
| `_loop()` | Ustawianie `_running = False` przy koncu czasu obserwacji |

**Watek glowny** (serwer Flask) wywoluje: `start()`, `stop()`, `pause()`, `resume()`, `get_status()`.
**Watek petli** (daemon) wywoluje: `_loop()`, ktory modyfikuje stan pod blokada.

Blokada gwarantuje, ze `get_status()` zwroci spojny zrzut stanu -- nie zobaczy np. `delta_alt` z jednego cyklu i `delta_az` z innego.

**Uwaga dotyczaca `_paused`:** Flaga `_paused` jest sprawdzana w `_loop()` bez blokady. Jest to bezpieczne, poniewaz:
- Jest to pojedyncza wartosc `bool` (odczyt/zapis sa atomowe w CPython dzieki GIL).
- W najgorszym przypadku petla wykona jeden dodatkowy cykl zanim "zobaczy" pauze -- opoznienie rzędu 0.5s, co jest akceptowalne.
