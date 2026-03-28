# SeeSky Frontend - Dokumentacja techniczna

Kompletna dokumentacja warstwy frontendowej systemu trackingu radioteleskopowego SeeSky.
Frontend jest aplikacja Node.js/Express serwujaca interfejs webowy (EJS), ktory komunikuje sie
z backendowym API (Flask) poprzez zapytania HTTP (fetch). Interfejs umozliwia sterowanie
teleskopem, przegladanie katalogu gwiazd, zarzadzanie kolejka obserwacji, konfiguracje
parametrow, kalibracje oraz wizualizacje mapy nieba w czasie rzeczywistym.

---

## Spis tresci

1. [Struktura plikow](#1-struktura-plikow)
2. [server.js - Serwer Express](#2-serverjs---serwer-express)
3. [views/index.ejs - Szablon HTML](#3-viewsindexejs---szablon-html)
4. [public/js/app.js - Logika klienta](#4-publicjsappjs---logika-klienta)
5. [public/js/stars-bg.js - Animacja tla](#5-publicjsstars-bgjs---animacja-tla)
6. [public/css/style.css - Arkusz stylow](#6-publiccssstylecss---arkusz-stylow)
7. [Zewnetrzne zaleznosci](#7-zewnetrzne-zaleznosci)
8. [Zmienne srodowiskowe](#8-zmienne-srodowiskowe)
9. [Komunikacja z API](#9-komunikacja-z-api)

---

## 1. Struktura plikow

```
frontend/
  server.js                 # Serwer Express (punkt wejscia)
  views/
    index.ejs               # Glowny szablon HTML (EJS)
  public/
    js/
      app.js                # Logika klienta (autoryzacja, tracking, katalog, kolejka, konfiguracja, kalibracja, mapa nieba)
      stars-bg.js           # Animacja gwiezdzistego tla na ekranie logowania
    css/
      style.css             # Kompletny arkusz stylow
    images/
      seesky.svg            # Logo projektu SeeSky (plik SVG)
```

---

## 2. server.js - Serwer Express

**Sciezka:** `frontend/server.js`

Minimalistyczny serwer Node.js oparty na frameworku Express. Jego jedynym zadaniem jest
serwowanie szablonu EJS oraz plikow statycznych (CSS, JS, obrazy) z katalogu `public/`.

### Zaleznosci

| Modul     | Opis                                    |
|-----------|-----------------------------------------|
| `express` | Framework webowy do obslugi HTTP        |
| `path`    | Modul Node.js do operacji na sciezkach  |

### Konfiguracja

```js
const PORT    = process.env.PORT    || 3000;
const API_URL = process.env.API_URL || "http://localhost:5000";
```

- **PORT** - port, na ktorym nasluchuje serwer frontendowy (domyslnie `3000`).
- **API_URL** - adres bazowy backendowego API Flask (domyslnie `http://localhost:5000`).

### Silnik szablonow

Serwer korzysta z silnika **EJS** (Embedded JavaScript). Szablony sa odczytywane
z katalogu `views/` (wzglednie do `__dirname`).

```js
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));
```

### Pliki statyczne

Katalog `public/` jest udostepniany jako korzeń plikow statycznych:

```js
app.use(express.static(path.join(__dirname, "public")));
```

Dzieki temu pliki sa dostepne pod sciezkami:
- `/css/style.css`
- `/js/app.js`
- `/js/stars-bg.js`
- `/images/seesky.svg`

### Trasa (route)

Serwer definiuje dokladnie jedna trase:

| Metoda | Sciezka | Opis                                                       |
|--------|---------|------------------------------------------------------------|
| GET    | `/`     | Renderuje `index.ejs`, przekazujac zmienna `apiUrl: API_URL` |

Zmienna `apiUrl` jest wstrzykiwana do szablonu EJS, skad trafia do kodu JavaScript
klienta jako stala `API_URL`. Pozwala to na dynamiczna konfiguracje adresu backendu
bez modyfikacji kodu frontendowego.

### Uruchomienie

Po starcie serwer wypisuje na konsole:

```
SeeSky frontend: http://localhost:3000
Backend API:     http://localhost:5000
```

---

## 3. views/index.ejs - Szablon HTML

**Sciezka:** `frontend/views/index.ejs`

Glowny (i jedyny) szablon aplikacji. Jest to jednostronicowa aplikacja (SPA-like) -
caly interfejs jest zawarty w jednym pliku HTML. Widocznosc poszczegolnych sekcji
jest przelaczana dynamicznie przez JavaScript (atrybut `hidden`).

### Naglowek dokumentu (`<head>`)

```html
<html lang="pl">
```

- Jezyk dokumentu: **polski**.
- Tytul: `SeeSky - Tracking Radioteleskopowy`.
- Ladowane arkusze stylow:
  - `/css/style.css` - wlasne style.
  - `d3-celestial@0.7.35/celestial.css` - style biblioteki d3-celestial (z CDN).

### Ekran logowania (`#login-screen`)

Pierwszy widoczny ekran po wejsciu na strone. Zawiera:

| Element              | ID / Klasa         | Opis                                               |
|----------------------|--------------------|------------------------------------------------------|
| Canvas               | `#star-canvas`     | Platno do animacji gwiezdzistego tla (rysowane przez `stars-bg.js`) |
| Kontener logowania   | `.login-box`       | Szklany panel (glass-morphism) wycentrowany na ekranie |
| Logo SVG             | `.login-logo`      | Grafika `seesky.svg` z efektem swiecenia (drop-shadow) |
| Tytul                | `<h1>`             | "SeeSky"                                              |
| Podtytul             | `.subtitle`        | "System trackingu radioteleskopowego"                 |
| Formularz            | `#login-form`      | Pola: nazwa uzytkownika i haslo                       |
| Pole uzytkownika     | `#login-user`      | Typ `text`, domyslna wartosc: `operator`              |
| Pole hasla           | `#login-pass`      | Typ `password`                                        |
| Przycisk logowania   | `<button>`         | Tekst: "Zaloguj"                                      |
| Komunikat bledu      | `#login-error`     | Ukryty paragraf (`hidden`), klasa `.error`            |

### Dashboard (`#dashboard`)

Glowny panel sterowania, domyslnie ukryty (`hidden`). Uaktywniany po pomyslnym zalogowaniu.

#### Naglowek (header)

- **Marka** (`.header-brand`): logo (`seesky.svg`, 32px) + tytul "SeeSky".
- **Nawigacja** (`<nav>`): 7 przyciskow klasy `.nav-btn`:

| Przycisk       | `data-tab`    | Opis                            |
|----------------|---------------|---------------------------------|
| Tracking       | `tracking`    | Zakladka trackingu (domyslnie aktywna) |
| Katalog        | `catalog`     | Katalog gwiazd                  |
| Kolejka        | `queue`       | Kolejka obserwacji              |
| Konfiguracja   | `config`      | Ustawienia teleskopu            |
| Kalibracja     | `calibration` | Kalibracja teleskopu            |
| Mapa nieba     | `skymap`      | Interaktywna mapa nieba         |
| Wyloguj        | (brak)        | Przycisk wylogowania, ID: `#logout-btn`, klasa `.logout` |

#### Zakladka: Tracking (`#tab-tracking`)

Wyswietla biezacy status trackingu teleskopu.

**Karta statusu** (`.status-card`):
- Wskaznik statusu (`#tracking-indicator`) - wyswietla jeden z trzech stanow:
  - `NIEAKTYWNY` - klasa bazowa (szary)
  - `AKTYWNY` - klasa `.active` (zielony gradient)
  - `WSTRZYMANY` - klasa `.paused` (zolty gradient)
- Nazwa sledzonej gwiazdy (`#tracking-star`).

**Siatka metryk** (`.tracking-grid`) - 10 pol metrycznych:

| ID              | Etykieta        | Format wartosci   |
|-----------------|-----------------|-------------------|
| `#t-alt`        | Aktualna Alt    | `X.XXXX°`        |
| `#t-az`         | Aktualna Az     | `X.XXXX°`        |
| `#t-tgt-alt`    | Docelowa Alt    | `X.XXXX°`        |
| `#t-tgt-az`     | Docelowa Az     | `X.XXXX°`        |
| `#t-d-alt`      | Delta Alt       | `X.XXXX°`        |
| `#t-d-az`       | Delta Az        | `X.XXXX°`        |
| `#t-v-alt`      | Predkosc Alt    | `X.XXXXXX°/s`    |
| `#t-v-az`       | Predkosc Az     | `X.XXXXXX°/s`    |
| `#t-elapsed`    | Czas trwania    | `Xm Ys`          |
| `#t-remaining`  | Pozostalo       | `Xm Ys`          |

**Przyciski sterowania** (`.tracking-controls`):

| ID            | Tekst  | Klasa         | Stan poczatkowy |
|---------------|--------|---------------|-----------------|
| `#btn-start`  | Start  | `.btn-green`  | Aktywny         |
| `#btn-pause`  | Pauza  | `.btn-yellow` | Wylaczony       |
| `#btn-resume` | Wznow  | `.btn-blue`   | Wylaczony       |
| `#btn-stop`   | Stop   | `.btn-red`    | Wylaczony       |

#### Zakladka: Katalog gwiazd (`#tab-catalog`)

**Filtry** (`.filters`):

| ID                    | Typ      | Placeholder                 |
|-----------------------|----------|-----------------------------|
| `#star-search`        | `text`   | "Szukaj po nazwie..."       |
| `#star-max-mag`       | `number` | "Max magnitudo" (krok 0.1)  |
| `#star-constellation` | `text`   | "Gwiazdozbior (np. UMa)"   |
| `#star-filter-btn`    | button   | "Filtruj"                   |

**Tabela** (`#star-table`):

| Kolumna       | Opis                                      |
|---------------|-------------------------------------------|
| Nazwa         | Nazwa gwiazdy                             |
| Gwiazdozbior  | Skrot gwiazdozbioru                       |
| Magnitudo     | Jasnosc obserwowana (im mniej, tym jasniej)|
| RA (deg)      | Rektascensja w stopniach                  |
| Dec (deg)     | Deklinacja w stopniach                    |
| Akcje         | Przyciski: "Dodaj" (do kolejki), "Pozycja"|

**Paginacja** (`.pagination`):
- Przycisk `#star-prev` - "< Poprzednia"
- Informacja o stronie `#star-page-info` - format: "X / Y"
- Przycisk `#star-next` - "Nastepna >"

#### Zakladka: Kolejka obserwacji (`#tab-queue`)

**Tabela** (`#queue-table`):

| Kolumna    | Opis                                  |
|------------|---------------------------------------|
| ID         | Identyfikator obserwacji              |
| Gwiazda    | Nazwa gwiazdy                         |
| Czas (min) | Czas trwania obserwacji w minutach    |
| Priorytet  | Priorytet obserwacji (0 = domyslny)   |
| Status     | Status obserwacji                     |
| Akcje      | Przycisk "Usun"                       |

- Komunikat o pustej kolejce: `#queue-empty` (domyslnie ukryty).

#### Zakladka: Konfiguracja (`#tab-config`)

**Formularz** (`#config-form`) z siatka pol (`.form-grid`):

| ID               | Etykieta                         | Typ      | Krok   | Walidacja      |
|------------------|----------------------------------|----------|--------|----------------|
| `#cfg-lat`       | Szerokosc geograficzna (deg)     | `number` | 0.0001 | `required`     |
| `#cfg-lon`       | Dlugosc geograficzna (deg)       | `number` | 0.0001 | `required`     |
| `#cfg-alt`       | Wysokosc n.p.m. (m)             | `number` | 1      | `required`     |
| `#cfg-interval`  | Interwal trackingu (s)           | `number` | 0.5    | `min=0.5, required` |
| `#cfg-duration`  | Domyslny czas obserwacji (min)   | `number` | 1      | `min=1, required`   |
| `#cfg-pressure`  | Cisnienie (hPa)                  | `number` | 0.01   | Opcjonalne     |
| `#cfg-temp`      | Temperatura (C)                  | `number` | 0.1    | Opcjonalne     |
| `#cfg-humidity`  | Wilgotnosc (0-1)                 | `number` | 0.01   | `min=0, max=1` |

- Przycisk zapisu: "Zapisz konfiguracje" (`.btn-green`).
- Komunikat zwrotny: `#config-msg` (ukryty, klasy `.success` lub `.error`).

#### Zakladka: Kalibracja (`#tab-calibration`)

**Metryki statusu** (`.calibration-status`):

| ID               | Etykieta              | Opis                                     |
|------------------|-----------------------|------------------------------------------|
| `#cal-status`    | Status                | "SKALIBROWANY" (zielony) / "NIESKALIBROWANY" (szary) |
| `#cal-offset-az` | Offset Azymut         | Offset kalibracyjny azymutu w stopniach  |
| `#cal-offset-alt`| Offset Elewacja       | Offset kalibracyjny elewacji w stopniach |
| `#cal-time`      | Ostatnia kalibracja   | Data/czas ostatniej kalibracji           |

**Przyciski** (`.calibration-controls`):

| ID                 | Tekst                 | Klasa       | Opis                    |
|--------------------|-----------------------|-------------|-------------------------|
| `#btn-cal-polaris` | Kalibruj na Polaris   | `.btn-blue` | Kalibracja wzgledem Gwiazdy Polarnej |
| `#btn-cal-reset`   | Resetuj kalibracje    | `.btn-red`  | Resetuje offsety kalibracyjne        |

- Komunikat zwrotny: `#cal-msg` (ukryty).

#### Zakladka: Mapa nieba (`#tab-skymap`)

| Element             | ID / Klasa          | Opis                                          |
|---------------------|---------------------|-----------------------------------------------|
| Pasek informacyjny  | `.skymap-info`      | Wyswietla status trackingu i wspolrzedne      |
| Info o trackingu    | `#skymap-tracking-info` | "Tracking nieaktywny" lub dane aktywnego sledzenia |
| Kontener mapy       | `#celestial-map`    | Div, w ktorym d3-celestial renderuje mape SVG/Canvas |
| Legenda             | `.skymap-legend`    | Dwa elementy: pozycja teleskopu (czerwony) i cel obserwacji (zielony) |

### Skrypty zewnetrzne (CDN)

Ladowane na koncu `<body>` w podanej kolejnosci:

1. **d3 v3.5.17** (`d3.min.js`) - biblioteka do wizualizacji danych.
2. **d3.geo.projection** (`d3.geo.projection.min.js`) - rozszerzenie d3 o dodatkowe projekcje geograficzne.
3. **d3-celestial** (`celestial.min.js`) - biblioteka do renderowania mapy nieba.

### Wstrzykniecie zmiennej EJS

```html
<script>
  const API_URL = "<%= apiUrl %>";
</script>
```

Zmienna `API_URL` jest dostepna globalnie dla skryptow `app.js` i `stars-bg.js`.

---

## 4. public/js/app.js - Logika klienta

**Sciezka:** `frontend/public/js/app.js`

Glowny plik JavaScript odpowiedzialny za cala logike interfejsu: autoryzacje,
nawigacje miedzy zakladkami, polling statusu trackingu, zarzadzanie katalogiem
gwiazd, kolejka obserwacji, konfiguracja, kalibracja i mapa nieba.

### Stan globalny

| Zmienna              | Typ             | Wartosc poczatkowa | Opis                                                |
|----------------------|-----------------|--------------------|------------------------------------------------------|
| `token`              | `string\|null`  | `null`             | Token JWT do autoryzacji zapytan API                 |
| `trackingInterval`   | `number\|null`  | `null`             | ID intervalu `setInterval` dla pollingu statusu      |
| `starPage`           | `number`        | `1`                | Biezaca strona katalogu gwiazd                       |
| `starTotalPages`     | `number`        | `1`                | Calkowita liczba stron katalogu                      |
| `skyMapInitialized`  | `boolean`       | `false`            | Flaga: czy mapa nieba zostala zainicjalizowana       |
| `telescopeRA`        | `number\|null`  | `null`             | Rektascensja teleskopu w stopniach (0-360)           |
| `telescopeDec`       | `number\|null`  | `null`             | Deklinacja teleskopu w stopniach                     |
| `observerLat`        | `number`        | `51.1079`          | Szerokosc geograficzna obserwatora (domyslnie Wroclaw) |
| `observerLon`        | `number`        | `17.0385`          | Dlugosc geograficzna obserwatora (domyslnie Wroclaw)   |

### Funkcje pomocnicze

#### `api(method, path, body)`

Uniwersalny wrapper na `fetch()` do komunikacji z backendowym API.

**Parametry:**
- `method` (`string`) - metoda HTTP: `"GET"`, `"POST"`, `"PUT"`, `"DELETE"`.
- `path` (`string`) - sciezka API, np. `"/api/tracking/status"`.
- `body` (`object|undefined`) - opcjonalne cialo zapytania (serializowane do JSON).

**Dzialanie:**
1. Tworzy obiekt opcji z naglowkiem `Content-Type: application/json`.
2. Jesli `token` jest ustawiony, dodaje naglowek `Authorization: Bearer <token>`.
3. Jesli `body` jest podane, serializuje je do JSON i dodaje do opcji.
4. Wykonuje `fetch(API_URL + path, opts)`.
5. Parsuje odpowiedz JSON.
6. Jesli status HTTP nie jest 2xx (`!res.ok`), rzuca obiekt bledu zawierajacy `status` i dane odpowiedzi.
7. W przeciwnym wypadku zwraca sparsowane dane.

**Zwraca:** `Promise<object>` - sparsowana odpowiedz JSON z serwera.

**Rzuca:** Obiekt z polami `status` (kod HTTP) i polami z odpowiedzi serwera (np. `message`).

---

#### `formatTime(seconds)`

Formatuje czas w sekundach do postaci czytelnej dla uzytkownika.

**Parametr:** `seconds` (`number|null`) - czas w sekundach.

**Zwraca:** `string` - sformatowany czas w postaci `"Xm Ys"`, lub `"-"` jesli wartosc to `null`.

**Przyklad:** `formatTime(125)` zwraca `"2m 5s"`.

---

#### `deg(val)`

Formatuje wartosc kata do postaci z czterema miejscami po przecinku i symbolem stopnia.

**Parametr:** `val` (`number|null`) - wartosc kata w stopniach.

**Zwraca:** `string` - np. `"45.1234°"`, lub `"-"` jesli wartosc to `null`.

---

#### `degPerSec(val)`

Formatuje predkosc katowa do postaci z szescioma miejscami po przecinku.

**Parametr:** `val` (`number|null`) - wartosc predkosci katowej w stopniach na sekunde.

**Zwraca:** `string` - np. `"0.004167°/s"`, lub `"-"` jesli wartosc to `null`.

---

### Nawigacja miedzy zakladkami

Mechanizm nawigacji oparty jest na atrybutach `data-tab` przyciskow `.nav-btn`.

**Dzialanie (obsluga klikniecia):**
1. Usuwa klase `active` ze wszystkich przyciskow nawigacji.
2. Dodaje klase `active` do kliknietego przycisku.
3. Ukrywa wszystkie sekcje `.tab-content` (ustawia `hidden = true`).
4. Odkrywa sekcje o ID `tab-<data-tab>` (ustawia `hidden = false`).
5. Laduje dane odpowiednie dla wybranej zakladki:
   - `catalog` -> wywoluje `loadStars()`
   - `queue` -> wywoluje `loadQueue()`
   - `config` -> wywoluje `loadConfig()`
   - `calibration` -> wywoluje `loadCalibration()`
   - `skymap` -> wywoluje `initSkyMap()`

### Logowanie i wylogowywanie

#### Logowanie (`#login-form` submit)

**Przebieg:**
1. Zapobiega domyslnej akcji formularza (`e.preventDefault()`).
2. Ukrywa ewentualny poprzedni komunikat bledu.
3. Wysyla `POST /api/auth/login` z polami `username` i `password`.
4. Po sukcesie:
   - Zapisuje `token` z odpowiedzi.
   - Ukrywa ekran logowania (`#login-screen`).
   - Pokazuje dashboard (`#dashboard`).
   - Uruchamia polling statusu trackingu (`startTrackingPolling()`).
5. Po bledzie:
   - Wyswietla komunikat bledu w `#login-error`.

#### Wylogowywanie (`#logout-btn` click)

**Przebieg:**
1. Wysyla `POST /api/auth/logout` (bledy sa ignorowane).
2. Ustawia `token = null`.
3. Zatrzymuje polling trackingu (`stopTrackingPolling()`).
4. Ukrywa dashboard.
5. Pokazuje ekran logowania.

### Modul trackingu

#### `updateTrackingStatus()`

Pobiera biezacy status trackingu i aktualizuje caly interfejs.

**Endpoint:** `GET /api/tracking/status`

**Dzialanie:**
1. Pobiera dane statusu z API.
2. Aktualizuje wskaznik statusu (`#tracking-indicator`):
   - Jesli `is_tracking && is_paused` -> tekst "WSTRZYMANY", klasa `paused`.
   - Jesli `is_tracking` -> tekst "AKTYWNY", klasa `active`.
   - W przeciwnym razie -> tekst "NIEAKTYWNY", klasa bazowa.
3. Aktualizuje nazwe sledzonej gwiazdy (`#tracking-star`).
4. Aktualizuje 10 pol metrycznych (alt, az, docelowe, delta, predkosc, czasy).
5. Aktualizuje zmienne `telescopeRA` i `telescopeDec` (jesli tracking jest aktywny i gwiazda ma wspolrzedne RA/Dec).
6. Aktualizuje pasek informacyjny mapy nieba (`#skymap-tracking-info`).
7. Jesli mapa nieba jest zainicjalizowana, wywoluje `updateSkyMapPointer()`.
8. Aktualizuje stany przyciskow sterowania (disabled/enabled):
   - **Start**: wylaczony gdy tracking jest aktywny.
   - **Pauza**: wylaczony gdy tracking nie jest aktywny lub jest wstrzymany.
   - **Wznow**: wylaczony gdy tracking nie jest aktywny lub nie jest wstrzymany.
   - **Stop**: wylaczony gdy tracking nie jest aktywny.

**Obsluga bledow:** Bledy sa cicho ignorowane (pusty `catch`), aby polling nie przerwal dzialania
w przypadku tymczasowych problemow z polaczeniem.

---

#### `startTrackingPolling()`

Uruchamia cykliczne odpytywanie statusu trackingu.

**Dzialanie:**
1. Natychmiast wywoluje `updateTrackingStatus()`.
2. Ustawia `setInterval` co **2000 ms** (2 sekundy), wywolujacy `updateTrackingStatus()`.
3. Zapisuje ID intervalu w zmiennej `trackingInterval`.

---

#### `stopTrackingPolling()`

Zatrzymuje cykliczne odpytywanie.

**Dzialanie:** Wywoluje `clearInterval(trackingInterval)`, jesli interval istnieje.

---

#### Przyciski sterowania trackingiem

Kazdy przycisk wysyla zapytanie POST do odpowiedniego endpointu. W przypadku bledu
wyswietla `alert()` z komunikatem.

| Przycisk        | Endpoint                    | Blad                        |
|-----------------|-----------------------------|-----------------------------|
| `#btn-start`    | `POST /api/tracking/start`  | "Blad startu trackingu"     |
| `#btn-stop`     | `POST /api/tracking/stop`   | "Blad stopu trackingu"      |
| `#btn-pause`    | `POST /api/tracking/pause`  | "Blad pauzy"                |
| `#btn-resume`   | `POST /api/tracking/resume` | "Blad wznowienia"           |

### Modul katalogu gwiazd

#### `loadStars()`

Pobiera strone katalogu gwiazd z API i buduje tabele HTML.

**Endpoint:** `GET /api/stars` z parametrami query.

**Parametry query:**
- `page` - numer strony (ze zmiennej `starPage`).
- `per_page` - stala wartosc `20`.
- `search` - fraza z pola `#star-search` (opcjonalnie, kodowana URL).
- `max_magnitude` - z pola `#star-max-mag` (opcjonalnie).
- `constellation` - z pola `#star-constellation` (opcjonalnie, kodowana URL).

**Dzialanie:**
1. Buduje string parametrow query na podstawie wartosci pol filtrowania.
2. Wywoluje `GET /api/stars` z parametrami.
3. Czyści cialo tabeli (`#star-tbody`).
4. Iteruje po tablicy `data.stars`, tworzac wiersze `<tr>` z kolumnami:
   - Nazwa (lub "-").
   - Gwiazdozbior (lub "-").
   - Magnitudo (2 miejsca po przecinku, lub "-").
   - RA (4 miejsca po przecinku, lub "-").
   - Dec (4 miejsca po przecinku, lub "-").
   - Przyciski akcji: "Dodaj" (`addToQueue(id)`) i "Pozycja" (`showPosition(id)`).
5. Aktualizuje paginacje:
   - `starTotalPages` z `data.pagination.total_pages`.
   - Tekst `#star-page-info`.
   - Stan przyciskow `#star-prev` i `#star-next`.

---

#### Przycisk filtrowania (`#star-filter-btn`)

Resetuje `starPage` do 1 i wywoluje `loadStars()`.

#### Paginacja (`#star-prev`, `#star-next`)

- **Poprzednia**: dekrementuje `starPage` (jesli > 1) i wywoluje `loadStars()`.
- **Nastepna**: inkrementuje `starPage` (jesli < `starTotalPages`) i wywoluje `loadStars()`.

---

#### `addToQueue(starId)`

Dodaje gwiazde do kolejki obserwacji.

**Parametr:** `starId` (`number`) - ID gwiazdy.

**Dzialanie:**
1. Wyswietla `prompt()` z pytaniem o czas obserwacji (domyslnie 30 min).
2. Jesli uzytkownik anuluje, przerywa.
3. Wyswietla `prompt()` z pytaniem o priorytet (domyslnie 0).
4. Wysyla `POST /api/queue` z cialem:
   ```json
   {
     "star_id": <starId>,
     "duration_minutes": <parseInt(duration)>,
     "priority": <parseInt(priority)>
   }
   ```
5. Po sukcesie wyswietla `alert("Dodano do kolejki!")`.
6. Po bledzie wyswietla `alert()` z komunikatem bledu.

**Dostepnosc:** Funkcja jest eksponowana globalnie jako `window.addToQueue`, poniewaz jest
wywolywana z atrybutow `onclick` w dynamicznie generowanym HTML tabeli.

---

#### `showPosition(starId)`

Wyswietla biezaca pozycje gwiazdy (wspolrzedne horyzontalne).

**Parametr:** `starId` (`number`) - ID gwiazdy.

**Endpoint:** `GET /api/stars/<starId>/position`

**Dzialanie:**
1. Pobiera pozycje gwiazdy z API.
2. Wyswietla `alert()` z informacjami:
   - Wysokosc (Alt) w stopniach.
   - Azymut (Az) w stopniach.
   - Czy gwiazda jest nad horyzontem (TAK/NIE).
   - Czas obliczenia.

**Dostepnosc:** Eksponowana globalnie jako `window.showPosition`.

### Modul kolejki obserwacji

#### `loadQueue()`

Pobiera kolejke obserwacji i buduje tabele HTML.

**Endpoint:** `GET /api/queue`

**Dzialanie:**
1. Pobiera dane kolejki z API.
2. Czysci cialo tabeli (`#queue-tbody`).
3. Jesli kolejka jest pusta (`data.queue.length === 0`):
   - Pokazuje komunikat `#queue-empty`.
   - Konczy dzialanie.
4. Ukrywa komunikat `#queue-empty`.
5. Iteruje po tablicy `data.queue`, tworzac wiersze z kolumnami:
   - ID obserwacji.
   - Nazwa gwiazdy (lub "Gwiazda #ID").
   - Czas trwania w minutach.
   - Priorytet.
   - Status.
   - Przycisk "Usun" (`removeFromQueue(id)`).

---

#### `removeFromQueue(obsId)`

Usuwa obserwacje z kolejki.

**Parametr:** `obsId` (`number`) - ID obserwacji.

**Dzialanie:**
1. Wyswietla `confirm()` z pytaniem "Usunac obserwacje #X?".
2. Jesli uzytkownik anuluje, przerywa.
3. Wysyla `DELETE /api/queue/<obsId>`.
4. Po sukcesie ponownie laduje kolejke (`loadQueue()`).
5. Po bledzie wyswietla `alert()`.

**Dostepnosc:** Eksponowana globalnie jako `window.removeFromQueue`.

### Modul konfiguracji

#### `loadConfig()`

Pobiera biezaca konfiguracje teleskopu i wypelnia formularz.

**Endpoint:** `GET /api/config`

**Dzialanie:**
1. Pobiera konfiguracje z API.
2. Aktualizuje zmienne `observerLat` i `observerLon` (uzywane przez mape nieba).
3. Wypelnia pola formularza wartosciami z odpowiedzi:
   - `cfg-lat` <- `latitude`
   - `cfg-lon` <- `longitude`
   - `cfg-alt` <- `altitude`
   - `cfg-interval` <- `tracking_interval_seconds`
   - `cfg-duration` <- `default_observation_duration_minutes`
   - `cfg-pressure` <- `pressure`
   - `cfg-temp` <- `temperature`
   - `cfg-humidity` <- `humidity`

---

#### Zapis konfiguracji (`#config-form` submit)

**Endpoint:** `PUT /api/config`

**Dzialanie:**
1. Zapobiega domyslnej akcji formularza.
2. Wysyla `PUT /api/config` z cialem zawierajacym 8 pol:
   ```json
   {
     "latitude": <float>,
     "longitude": <float>,
     "altitude": <float>,
     "tracking_interval_seconds": <float>,
     "default_observation_duration_minutes": <int>,
     "pressure": <float>,
     "temperature": <float>,
     "humidity": <float>
   }
   ```
3. Po sukcesie:
   - Wyswietla "Konfiguracja zapisana!" w `#config-msg` (klasa `.success`).
   - Ukrywa komunikat po 3 sekundach (`setTimeout`).
4. Po bledzie:
   - Wyswietla komunikat bledu w `#config-msg` (klasa `.error`).

### Modul kalibracji

#### `loadCalibration()`

Pobiera status kalibracji teleskopu.

**Endpoint:** `GET /api/calibration/status`

**Dzialanie:**
1. Pobiera dane kalibracji z API.
2. Aktualizuje metryki:
   - `#cal-status`: tekst "SKALIBROWANY" (zielony) lub "NIESKALIBROWANY" (szary).
   - `#cal-offset-az`: offset azymutu (4 miejsca po przecinku + "°").
   - `#cal-offset-alt`: offset elewacji (4 miejsca po przecinku + "°").
   - `#cal-time`: czas ostatniej kalibracji lub "-".

---

#### Przycisk "Kalibruj na Polaris" (`#btn-cal-polaris`)

**Endpoint:** `POST /api/calibration/polaris`

**Dzialanie:**
1. Wysyla zapytanie kalibracji.
2. Po sukcesie:
   - Wyswietla komunikat z odpowiedzi serwera (`data.message`) w `#cal-msg` (klasa `.success`).
   - Ponownie laduje status kalibracji (`loadCalibration()`).
3. Po bledzie:
   - Wyswietla komunikat bledu w `#cal-msg` (klasa `.error`).

---

#### Przycisk "Resetuj kalibracje" (`#btn-cal-reset`)

**Endpoint:** `POST /api/calibration/reset`

**Dzialanie:**
1. Wyswietla `confirm("Resetowac kalibracje?")`.
2. Jesli uzytkownik anuluje, przerywa.
3. Wysyla zapytanie resetu.
4. Po sukcesie:
   - Wyswietla "Kalibracja zresetowana" w `#cal-msg` (klasa `.success`).
   - Ponownie laduje status kalibracji.
5. Po bledzie:
   - Wyswietla komunikat bledu.

### Modul mapy nieba (d3-celestial)

Modul odpowiedzialny za interaktywna wizualizacje mapy nieba z zaznaczona pozycja teleskopu.
Wykorzystuje biblioteke **d3-celestial** do renderowania gwiazd, gwiazdzobiorow, mglawic,
Drogi Mlecznej i horyzontu.

#### Zmienna `celestialConfig`

Typ: `object|null`. Przechowuje obiekt konfiguracyjny d3-celestial.
Inicjalizowana w `buildSkyMap()`.

---

#### `raToD3(raDeg)`

Konwertuje rektascensje ze standardowego zakresu astronomicznego na format
wymagany przez d3-celestial.

**Parametr:** `raDeg` (`number`) - rektascensja w stopniach, zakres 0-360.

**Zwraca:** `number` - wartosc w zakresie -180 do +180.

**Logika:** Jesli `raDeg > 180`, zwraca `raDeg - 360`. W przeciwnym razie zwraca wartosc bez zmian.

---

#### `initSkyMap()`

Inicjalizuje mape nieba lub odswieza ja, jesli juz istnieje.

**Dzialanie:**
1. **Jesli mapa juz zainicjalizowana** (`skyMapInitialized === true`):
   - Aktualizuje date w d3-celestial (`Celestial.date(new Date())`).
   - Wywoluje `updateSkyMapPointer()`.
   - Konczy dzialanie.
2. **Jesli biblioteka Celestial nie jest jeszcze dostepna** (`typeof Celestial === "undefined"`):
   - Wyswietla komunikat ladowania w kontenerze `#celestial-map`.
   - Ponawia probe po 500 ms (`setTimeout(initSkyMap, 500)`).
3. **Jesli biblioteka jest dostepna:**
   - Pobiera konfiguracje obserwatora (`GET /api/config`).
   - Aktualizuje `observerLat` i `observerLon`.
   - Wywoluje `buildSkyMap()`.
   - Jesli pobranie konfiguracji sie nie powiedzie, wywoluje `buildSkyMap()` z domyslnymi wspolrzednymi.

---

#### `buildSkyMap()`

Tworzy i wyswietla mape nieba z pelna konfiguracja d3-celestial.

**Dzialanie:**
1. Czysci kontener `#celestial-map`.
2. Tworzy obiekt `celestialConfig` z nastepujacymi ustawieniami:

**Projekcja i pozycja:**
- `width: 0` - automatyczna pelna szerokosc rodzica.
- `projection: "airy"` - projekcja Airy'ego (optymalna dla obserwacji nieba).
- `geopos: [observerLat, observerLon]` - wspolrzedne obserwatora.
- `follow: "zenith"` - mapa podaza za zenitem (punkt nad glowa).
- `container: "celestial-map"` - ID elementu-kontenera.
- `datapath` - sciezka do danych gwiazd z serwera ofrohn.github.io.

**Tlo:**
- Kolor wypelnienia: `#0a0e17` (bardzo ciemny granat).
- Obramowanie: `#1a2235`.

**Gwiazdy (`stars`):**
- Widoczne do granicy jasnosci (`limit: 6` magnitudo).
- Kolorowe (`colors: true`).
- Nazwy wlasne widoczne do 2.5 magnitudo.
- Styl nazw: `#8899bb`, czcionka 11px.
- Rozmiar: 7, wykladnik jasnosci: -0.28.
- Oznaczenia katalogowe wylaczone (`designation: false`).

**Mgławice / obiekty glebokiego nieba (`dsos`):**
- Widoczne do 6 magnitudo.
- Styl: `#444444`, nazwy widoczne do 4 magnitudo.
- Styl nazw: `#556677`, czcionka 10px.

**Gwiazdozbiory (`constellations`):**
- Nazwy widoczne, typ IAU (skroty miedzynarodowe).
- Styl nazw: `#334466`, pogrubiona czcionka 13px, wycentrowane.
- Linie laczace gwiazdy: `#2a3555`, szerokosc 1.2px, przezroczystosc 0.6.
- Granice gwiazdzobiorow wylaczone.

**Droga Mleczna (`mw`):**
- Widoczna, kolor `#0d1525`, przezroczystosc 0.15 (subtelna).

**Linie siatki (`lines`):**
- Siatka wspolrzednych (`graticule`): widoczna, `#1a2235`, subtelna.
- Rownik niebieski (`equatorial`): widoczny, `#2244aa`, szerokosc 0.8px.
- Ekliptyka, plaszczyzna galaktyczna, supergalaktyczna: wylaczone.

**Horyzont (`horizon`):**
- Widoczny, kolor kreski: `#4a9eff`, wypelnienie ponizej: `#000000`.

**Wylaczone elementy:**
- Planety (`planets: { show: false }`).
- Efekt dziennego swiatla (`daylight: { show: false }`).
- Panele kontrolne (`controls: false`).
- Wszystkie pola formularzy.

3. Rejestruje niestandardowa warstwe rysowania (`Celestial.add()`):
   - Typ: `"raw"`.
   - Funkcja `redraw` wywoluje `drawTelescopePointer()` przy kazdym przerysowaniu mapy.

4. Wywoluje `Celestial.display(celestialConfig)` - renderuje mape.

5. Ustawia `skyMapInitialized = true`.

6. Uruchamia `setInterval` co **30 sekund**, ktory aktualizuje date na mapie
   (aby mapa odswieza la pozycje gwiazd zgodnie z czasem syderycznym),
   ale tylko jesli zakladka mapy nieba jest widoczna.

---

#### `drawTelescopePointer()`

Rysuje wskaznik pozycji teleskopu na mapie nieba przy uzyciu Canvas API.

**Warunek:** Funkcja konczy sie natychmiast, jesli `telescopeRA` lub `telescopeDec` jest `null`
(tracking nieaktywny lub brak wspolrzednych gwiazdy).

**Dzialanie:**
1. Konwertuje wspolrzedne RA za pomoca `raToD3()`.
2. Sprawdza, czy punkt jest widoczny na mapie (`Celestial.clip(coords)`). Jesli nie, konczy sie.
3. Projektuje wspolrzedne na wspolrzedne pikseli (`Celestial.mapProjection(coords)`).
4. Pobiera kontekst Canvas (`Celestial.context`).
5. Rysuje trzy elementy graficzne:

**Zewnetrzny pierscien (cel):**
- Okrag o promieniu 14px.
- Kolor kreski: `#33ff33` (zielony).
- Szerokosc kreski: 1.5px.

**Krzyzyk celownika:**
- Cztery linie tworzace krzyz z przerwa w srodku (8px gap).
- Rozpietosc: 20px od centrum.
- Kolor kreski: `#ff3333` (czerwony).
- Szerokosc kreski: 2px.

**Centralna kropka:**
- Okrag o promieniu 3px.
- Wypelnienie: `#ff3333` (czerwony).
- Efekt swiecenia (shadow): `#ff3333`, rozmycie 8px.

**Etykieta "TELESKOP":**
- Czcionka: bold 12px, Segoe UI.
- Kolor: `#ff5555` (jasny czerwony).
- Pozycja: 22px na prawo i 6px nad punktem.
- Wyrownanie: lewy, dolny.

---

#### `updateSkyMapPointer()`

Wymusza przerysowanie mapy nieba, co powoduje ponowne wywolanie `drawTelescopePointer()`.

**Warunek:** Konczy sie jesli `skyMapInitialized === false` lub `Celestial` nie jest zdefiniowany.

**Dzialanie:** Wywoluje `Celestial.redraw()`.

---

## 5. public/js/stars-bg.js - Animacja tla

**Sciezka:** `frontend/public/js/stars-bg.js`

Samowywolujace sie wyrazenie funkcyjne (IIFE), ktore tworzy animowane gwiezdziste tlo
na ekranie logowania. Animacja jest renderowana na elemencie `<canvas>`.

### Inicjalizacja

1. Pobiera element `#star-canvas`. Jesli nie istnieje, konczy dzialanie.
2. Pobiera kontekst 2D canvas.
3. Inicjalizuje tablice: `stars` (gwiazdy statyczne) i `shootingStars` (spadajace gwiazdy).
4. Definiuje zmienne `W` i `H` (szerokosc i wysokosc canvas).

### Funkcja `resize()`

Dopasowuje wymiary canvas do rozmiaru elementu (`offsetWidth`, `offsetHeight`).
Wywolywana:
- Natychmiast przy inicjalizacji.
- Przy zdarzeniu `window.resize`.

### Generowanie gwiazd

Tworzy tablice **200 gwiazd** z nastepujacymi wlasciwosciami:

| Wlasciwosc | Zakres / Logika                                           |
|-------------|-----------------------------------------------------------|
| `x`         | Losowa pozycja 0-2000                                     |
| `y`         | Losowa pozycja 0-2000                                     |
| `r`         | Promien: 0.3 - 1.8 px                                    |
| `alpha`     | Przezroczystosc bazowa: 0.2 - 0.8                        |
| `speed`     | Predkosc migotania: 0.002 - 0.007                         |
| `phase`     | Przesuniecie fazowe: 0 - 2*PI                             |
| `color`     | Kolor RGB: 8% szans na bordo (178,47,87), 6% na niebieski (74,106,255), reszta bialy (255,255,255) |

Kolory odpowiadaja palecie kolorystycznej projektu SeeSky - bordo jest kolorem przewodnim,
a niebieski jest kolorem dodatkowym.

### Funkcja `spawnShootingStar()`

Tworzy spadajaca gwiazde (maksymalnie 2 naraz na ekranie).

| Wlasciwosc | Zakres / Opis                                 |
|-------------|-----------------------------------------------|
| `x`         | Pozycja startowa X: 0 - 80% szerokosci       |
| `y`         | Pozycja startowa Y: 0 - 40% wysokosci        |
| `len`       | Dlugosc ogona: 40 - 120 px                    |
| `speed`     | Predkosc ruchu: 3 - 7 px/klatke              |
| `alpha`     | Poczatkowa przezroczystosc: 1                 |
| `angle`     | Kat ruchu: ~30° + losowe odchylenie (PI/6 + 0-0.3 rad) |

### Funkcja `draw(t)` - Petla animacji

Glowna petla renderowania, wywolywana przez `requestAnimationFrame`.

**Rysowanie gwiazd statycznych:**
1. Czysci caly canvas.
2. Dla kazdej gwiazdy:
   - Oblicza efekt migotania: `sin(t * speed + phase) * 0.3 + 0.7` (wartosc 0.4-1.0).
   - Mnozy migotanie przez bazowa przezroczystosc.
   - Rysuje okrag na pozycji `(x % W, y % H)` - modulowanie zapewnia widocznosc niezaleznie od rozmiaru okna.
   - Wypelnia kolorem RGBA z obliczona przezroczystoscia.

**Rysowanie spadajacych gwiazd:**
1. Iteruje od konca tablicy (aby bezpiecznie usuwac elementy).
2. Oblicza wektor kierunku na podstawie kata i dlugosci.
3. Tworzy gradient liniowy od punktu startowego do koncowego:
   - Poczatek: bordo `rgba(178,47,87, alpha)`.
   - Koniec: bordo calkowicie przezroczyste `rgba(178,47,87, 0)`.
4. Rysuje linie z gradientem (szerokosc 1.5px).
5. Przesuwa pozycje spadajacej gwiazdy o wektor predkosci.
6. Zmniejsza przezroczystosc o 0.008 na klatke.
7. Usuwa spadajaca gwiazde, jesli:
   - Przezroczystosc spadla do 0 lub ponizej.
   - Pozycja wyszla poza granice canvas.

**Tworzenie nowych spadajacych gwiazd:**
- W kazdej klatce jest 0.3% szans na wywolanie `spawnShootingStar()`.

**Kontrola petli animacji:**
- Animacja kontynuuje sie tylko, gdy ekran logowania jest widoczny (`!document.getElementById("login-screen").hidden`).
- Zapobiega to marnowaniu zasobow CPU/GPU, gdy uzytkownik jest zalogowany.

### Wznawianie animacji po wylogowaniu

Skrypt dodaje obsluge klikniecia na przycisk `#logout-btn`. Po wylogowaniu,
z opoznieniem 100 ms sprawdza, czy ekran logowania jest widoczny. Jesli tak,
wznawia petle `requestAnimationFrame(draw)`.

---

## 6. public/css/style.css - Arkusz stylow

**Sciezka:** `frontend/public/css/style.css`

Kompletny arkusz stylow definiujacy wyglad calego interfejsu. Oparty na ciemnym motywie
z granatowym tlem i bordowymi akcentami nawiazujacymi do kolorystyki logo SeeSky.

### Reset i zmienne CSS

**Reset globalny:**
```css
* { margin: 0; padding: 0; box-sizing: border-box; }
```

**Zmienne CSS (`:root`):**

| Zmienna            | Wartosc                           | Zastosowanie                      |
|--------------------|-----------------------------------|-----------------------------------|
| `--bg`             | `#080b14`                         | Glowny kolor tla                  |
| `--bg-gradient`    | Gradient 135deg (ciemne granaty)  | Tlo ekranu logowania              |
| `--surface`        | `#0f1429`                         | Tlo kart, metryk, tabel           |
| `--surface2`       | `#161b35`                         | Tlo naglowkow tabel, stanow domyslnych |
| `--border`         | `#1e2548`                         | Obramowanie elementow             |
| `--border-accent`  | `#2a1a30`                         | Obramowanie z akcentem            |
| `--text`           | `#e0e4f0`                         | Glowny kolor tekstu               |
| `--text2`          | `#7b87ab`                         | Kolor tekstu drugorzednego        |
| `--accent`         | `#b22f57`                         | Glowny akcent bordowy             |
| `--accent-dark`    | `#7b1b38`                         | Ciemniejszy akcent bordowy        |
| `--accent-glow`    | `rgba(178, 47, 87, 0.3)`         | Efekt swiecenia bordowego         |
| `--accent-light`   | `#d44a73`                         | Jasniejszy akcent bordowy         |
| `--blue`           | `#4a6aff`                         | Akcent niebieski                  |
| `--blue-soft`      | `#3a4f99`                         | Stonowany niebieski               |
| `--purple`         | `#7c4dff`                         | Akcent fioletowy                  |
| `--purple-soft`    | `rgba(124, 77, 255, 0.15)`       | Stonowany fioletowy               |
| `--green`          | `#22c55e`                         | Kolor statusu: aktywny/sukces     |
| `--yellow`         | `#eab308`                         | Kolor statusu: wstrzymany/ostrzezenie |
| `--red`            | `#ef4444`                         | Kolor statusu: blad/stop          |

### Sekcja: Body

```css
body {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
}
```

Czcionka bazowa to **Segoe UI** z fallbackiem na czcionki systemowe.
Minimalna wysokosc strony: pelna wysokosc viewportu.

### Sekcja: Ekran logowania (`#login-screen`)

**Kontener glowny:**
- Minimalna wysokosc: `100vh` (pelny ekran).
- Tlo: `--bg-gradient` (gradient 135deg przez odcienie granatu i fioletu).
- `position: relative` + `overflow: hidden` - kontener dla absolutnie pozycjonowanych elementow.

**Canvas gwiazd (`#star-canvas`):**
- `position: absolute`, rozciagniety na caly ekran (`inset: 0`).
- Szerokos c i wysokosc: 100%.
- `z-index: 0` - pod pozostalymi elementami.

**Pseudo-element `::before` - gwiazdy CSS (fallback):**
- 16 gradientow radialnych symulujacych gwiazdy na wypadek, gdyby canvas nie zadzialal.
- Zawiera gwiazdy w trzech kolorach: biale, bordowe (`rgba(178,47,87,0.6)`) i niebieskie (`rgba(74,106,255,0.5)`).
- Animacja `twinkle`: przezroczystosc oscyluje miedzy 0.6 a 1.0, cykl 4 sekundy.

**Pseudo-element `::after` - bordowy blask:**
- Gradient radialny `rgba(123,27,56,0.15)` na srodku gornej czesci ekranu.
- Rozmiar: 600x600px.
- Tworzy subteln a poswiate za panelem logowania.

**Panel logowania (`.login-box`):**
- Absolutne centrowanie: `top: 50%; left: 50%; transform: translate(-50%, -50%)`.
- Efekt **glass-morphism**: `backdrop-filter: blur(20px)` + polprzezroczyste tlo `rgba(15, 20, 41, 0.85)`.
- Zaokraglone rogi: `16px`.
- Obramowanie: polprzezroczyste bordowe `rgba(178, 47, 87, 0.25)`.
- Padding: `44px` gora, `40px` boki, `36px` dol.
- Szerokosc: `380px`.
- Podwojny cien: bordowy blask (`rgba(178, 47, 87, 0.08)`) + gleboki cien (`rgba(0, 0, 0, 0.4)`).
- `z-index: 1` - nad canvasem i pseudo-elementami.

**Logo logowania (`.login-logo`):**
- Szerokosc: 64px, proporcjonalna wysokosc.
- Efekt: `drop-shadow` z bordowym blaskiem.

**Tytul (`h1`) w panelu logowania:**
- Gradient tekstu: od `--accent-light` do `--accent` (135deg).
- Realizacja: `background-clip: text` + `-webkit-text-fill-color: transparent`.

**Podtytul (`.subtitle`):**
- Kolor: `--text2` (szary).
- Rozmiar: 13px, rozstaw liter: 0.5px.

**Pola input w panelu logowania:**
- Pelna szerokosc, padding 11px.
- Ciemne tlo `rgba(8, 11, 20, 0.6)`.
- Zaokraglone rogi: 8px.
- **Focus**: bordowe obramowanie + efekt swiecenia (`box-shadow: 0 0 0 3px var(--accent-glow)`).

**Przycisk logowania:**
- Pelna szerokosc.
- Gradient: od `--accent-dark` do `--accent`.
- **Hover**: przesuniecie do gory o 1px (`translateY(-1px)`) + bordowy cien.

**Komunikaty bledu/sukcesu:**
- `.error`: kolor `--red`, rozmiar 13px.
- `.success`: kolor `--green`, rozmiar 13px.

### Sekcja: Naglowek (`header`)

- Layout: `flex`, wyrownanie do centrow, rozmieszczenie `space-between`.
- Padding: `10px 24px`.
- Tlo: gradient pionowy od `#0f1429` do `#0c1022`.
- Dolne obramowanie + cien (`box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3)`).

**Marka naglowka (`.header-brand`):**
- Flex z `gap: 10px`.
- Logo 32px z bordowym efektem `drop-shadow`.
- Tytul z gradientem tekstu (jak w panelu logowania).

**Nawigacja (`nav`):**
- Flex z `gap: 4px`, zawijanie elementow (`flex-wrap: wrap`).

**Przyciski nawigacji (`.nav-btn`):**
- Domyslnie: przezroczyste tlo, tekst `--text2`, obramowanie `--border`, 6px rogi.
- **Hover**: tlo `--surface2`, tekst `--text`, obramowanie `--blue-soft`.
- **Active** (`.active`): gradient bordowy tla, bialy tekst, bordowe obramowanie, efekt swiecenia.

**Przycisk wylogowania (`.nav-btn.logout`):**
- Obramowanie: polprzezroczysty czerwony.
- Tekst: `#ef7777`.
- **Hover**: pelne czerwone tlo i obramowanie, bialy tekst.

### Sekcja: Zakladki (`tab-content`)

- Padding: `24px`.
- Maksymalna szerokosc: `1100px`, wycentrowanie (`margin: 0 auto`).
- Naglowek `h2`: dolne obramowanie, margines dolny 20px.

### Sekcja: Tracking

**Karta statusu (`.status-card`):**
- Tlo `--surface`, obramowanie `--border`, zaokraglone rogi 10px.
- Pseudo-element `::before` tworzy cienka kolorowa linie na gorze
  (gradient: przezroczysty -> bordowy -> fioletowy -> przezroczysty).

**Wskaznik statusu (`.status-indicator`):**
- Zaokraglona kapsula (`border-radius: 20px`).
- Domyslnie: `--surface2` tlo, `--text2` tekst.
- `.active`: gradient zielony, bialy tekst, zielone swiecenie (`box-shadow`).
- `.paused`: gradient zolty, czarny tekst.

**Nazwa gwiazdy (`#tracking-star`):**
- Kolor `--text2`, rozmiar 14px.

**Siatka metryk (`.tracking-grid`):**
- CSS Grid: `repeat(auto-fill, minmax(180px, 1fr))`.
- Gap: 10px.

**Kafelki metryk (`.metric`):**
- Tlo `--surface`, obramowanie `--border`, rogi 8px.
- **Hover**: obramowanie zmienia sie na `--accent-dark`.
- Etykieta (`.label`): `--text2`, 11px, wielkie litery (`text-transform: uppercase`), `letter-spacing: 0.5px`.
- Wartosc (`.value`): 17px, pogrubiona, czcionka tabelaryczna (`font-variant-numeric: tabular-nums`).

**Kontrolki trackingu (`.tracking-controls`):**
- Flex wycentrowany, gap 10px.

### Sekcja: Przyciski (`.btn`)

**Styl bazowy:**
- Padding: `10px 20px`, rogi 6px.
- Czcionka: 13px, pogrubiona 600.
- Domyslne tlo: `--surface2`, obramowanie `--border`.
- Przejscia animowane (`transition: all 0.2s`).

**Stany:**
- `:disabled` - przezroczystosc 0.35, kursor `not-allowed`.
- `:hover:not(:disabled)` - przesuniecie do gory o 1px.

**Warianty kolorystyczne:**

| Klasa         | Tlo           | Hover glow                          |
|---------------|---------------|-------------------------------------|
| `.btn-green`  | `--green`     | `rgba(34,197,94,0.3)`              |
| `.btn-yellow` | `--yellow`    | (brak dedykowanego glow)            |
| `.btn-blue`   | `--blue`      | `rgba(74,106,255,0.3)`             |
| `.btn-red`    | `--red`       | `rgba(239,68,68,0.3)`              |
| `.btn-accent` | Gradient bordowy | `var(--accent-glow)`             |

Uwaga: `.btn-yellow` ustawia tekst na czarny (`color: #000`) ze wzgledu na jasne tlo.

### Sekcja: Tabele

- Pelna szerokosc, `border-collapse: collapse`.
- Tlo: `--surface`, rogi 10px, `overflow: hidden`.
- Zewnetrzne obramowanie: `--border`.

**Naglowki (`th`):**
- Tlo: `--surface2`.
- Tekst: `--text2`, 11px, wielkie litery.
- Dolne obramowanie.

**Komorki (`td`):**
- Padding: `10px 14px`, rozmiar 13px.
- Gorne obramowanie: polprzezroczyste.

**Hover na wierszu (`tr:hover td`):**
- Subtelny bordowy tint: `rgba(178, 47, 87, 0.05)`.

**Przyciski w komorkach:**
- Zmniejszony padding (4px 12px) i rozmiar czcionki (12px).

### Sekcja: Filtry (`.filters`)

- Flex z zawijaniem, gap 10px.
- Pola input: tlo `--surface`, obramowanie `--border`, rogi 6px.
- Focus na input: bordowe obramowanie.

### Sekcja: Paginacja (`.pagination`)

- Flex wycentrowany, gap 16px.
- Info o stronie: `--text2`, 13px.

### Sekcja: Formularz konfiguracji

**Siatka formularza (`.form-grid`):**
- CSS Grid: `repeat(auto-fill, minmax(220px, 1fr))`.
- Gap: 16px.

**Grupa pol (`.form-group`):**
- Etykieta: `--text2`, 11px, wielkie litery.
- Input: pelna szerokosc, tlo `--surface`, rogi 6px.
- Focus: bordowe obramowanie + efekt swiecenia (`box-shadow: 0 0 0 3px var(--accent-glow)`).

### Sekcja: Kalibracja

**Status kalibracji (`.calibration-status`):**
- CSS Grid: `repeat(auto-fill, minmax(220px, 1fr))`.
- Gap: 12px.

**Kontrolki (`.calibration-controls`):**
- Flex, gap 10px.

**Komunikat (`#cal-msg`):**
- Rozmiar czcionki: 13px.

### Sekcja: Mapa nieba

**Kontener mapy (`#celestial-map`):**
- Tlo: `#050810` (niemal czarne).
- Obramowanie: `--border`, rogi 10px.
- Minimalna wysokosc: `500px`.
- SVG wewnatrz: `display: block`, wycentrowane.

**Pasek informacyjny (`.skymap-info`):**
- Tlo `--surface`, obramowanie, rogi 8px.
- Tekst: 14px, kolor `--text2`.
- Napis "Tracking aktywny" (`.tracking-active`): kolor `--accent-light`, pogrubiony.

**Legenda (`.skymap-legend`):**
- Flex, gap 24px.
- Elementy legendy (`.legend-item`): flex z gap 6px.
- Kropki legendy (`.legend-dot`): 12x12px, okragle.
  - `.telescope-dot`: kolor `--accent` z bordowym swieceniem.
  - `.target-dot`: kolor `--green` z zielonym swieceniem.

### Sekcja: Pasek przewijania (scrollbar)

Stylowanie dla przegladarek opartych na WebKit:

- Track: kolor tla `--bg`.
- Thumb: kolor `--border`, zaokraglone (4px).
- Thumb hover: kolor `--accent-dark`.
- Szerokosc: 8px.

### Sekcja: Responsywnosc

Punkt przelomowy (breakpoint) przy `max-width: 800px`:

| Element               | Zmiana                                           |
|-----------------------|--------------------------------------------------|
| `header`              | Uklad kolumnowy (pionowy), gap 10px             |
| `nav`                 | Zawijanie, centrowanie                           |
| `.tracking-grid`      | 2 kolumny (`1fr 1fr`)                            |
| `.form-grid`          | 1 kolumna (`1fr`)                                |
| `.calibration-status` | 2 kolumny (`1fr 1fr`)                            |
| `.login-box`          | Szerokosc 92%, zmniejszony padding (30px 24px)   |

---

## 7. Zewnetrzne zaleznosci

### Serwer (Node.js)

| Pakiet    | Wersja | Zastosowanie                     |
|-----------|--------|----------------------------------|
| `express` | -      | Framework HTTP, serwowanie plikow |

### Klient (CDN)

| Biblioteka              | Wersja  | URL                                                                | Zastosowanie                          |
|-------------------------|---------|--------------------------------------------------------------------|---------------------------------------|
| d3                      | 3.5.17  | `cdn.jsdelivr.net/npm/d3@3.5.17/d3.min.js`                        | Bazowa biblioteka wizualizacji        |
| d3.geo.projection       | 0.7.35  | `cdn.jsdelivr.net/npm/d3-celestial@0.7.35/lib/d3.geo.projection.min.js` | Dodatkowe projekcje geograficzne |
| d3-celestial             | 0.7.35  | `cdn.jsdelivr.net/npm/d3-celestial@0.7.35/celestial.min.js`       | Renderowanie mapy nieba               |
| d3-celestial CSS        | 0.7.35  | `cdn.jsdelivr.net/npm/d3-celestial@0.7.35/celestial.css`          | Style mapy nieba                      |

**Uwaga:** d3-celestial wymaga d3 w wersji 3.x (nie 4+), stad uzycie `d3@3.5.17`.

---

## 8. Zmienne srodowiskowe

| Zmienna   | Domyslna                  | Opis                                      |
|-----------|---------------------------|--------------------------------------------|
| `PORT`    | `3000`                    | Port serwera frontendowego                 |
| `API_URL` | `http://localhost:5000`   | Adres bazowy backendowego API Flask        |

**Przyklad uruchomienia z niestandardowymi wartosciami:**

```bash
PORT=8080 API_URL=http://192.168.1.100:5000 node server.js
```

---

## 9. Komunikacja z API

Frontend komunikuje sie z backendem Flask wylacznie poprzez zapytania HTTP (funkcja `api()`).
Ponizej zestawienie wszystkich uzywanych endpointow:

### Autoryzacja

| Metoda | Endpoint              | Cialo zapytania                      | Opis                  |
|--------|-----------------------|--------------------------------------|-----------------------|
| POST   | `/api/auth/login`     | `{ username, password }`             | Logowanie, zwraca token |
| POST   | `/api/auth/logout`    | (brak)                               | Wylogowanie           |

### Tracking

| Metoda | Endpoint               | Cialo zapytania | Opis                           |
|--------|------------------------|-----------------|--------------------------------|
| GET    | `/api/tracking/status` | (brak)          | Status trackingu (polling co 2s) |
| POST   | `/api/tracking/start`  | (brak)          | Uruchomienie trackingu         |
| POST   | `/api/tracking/stop`   | (brak)          | Zatrzymanie trackingu          |
| POST   | `/api/tracking/pause`  | (brak)          | Wstrzymanie trackingu          |
| POST   | `/api/tracking/resume` | (brak)          | Wznowienie trackingu           |

### Katalog gwiazd

| Metoda | Endpoint                    | Parametry query                                          | Opis                     |
|--------|-----------------------------|----------------------------------------------------------|--------------------------|
| GET    | `/api/stars`                | `page`, `per_page`, `search`, `max_magnitude`, `constellation` | Lista gwiazd z paginacja |
| GET    | `/api/stars/:id/position`   | (brak)                                                   | Biezaca pozycja gwiazdy  |

### Kolejka obserwacji

| Metoda | Endpoint          | Cialo zapytania                                    | Opis                   |
|--------|-------------------|----------------------------------------------------|------------------------|
| GET    | `/api/queue`      | (brak)                                             | Lista obserwacji       |
| POST   | `/api/queue`      | `{ star_id, duration_minutes, priority }`          | Dodanie do kolejki     |
| DELETE | `/api/queue/:id`  | (brak)                                             | Usuniecie z kolejki    |

### Konfiguracja

| Metoda | Endpoint      | Cialo zapytania                                                                                   | Opis               |
|--------|---------------|---------------------------------------------------------------------------------------------------|---------------------|
| GET    | `/api/config` | (brak)                                                                                            | Pobranie konfiguracji |
| PUT    | `/api/config` | `{ latitude, longitude, altitude, tracking_interval_seconds, default_observation_duration_minutes, pressure, temperature, humidity }` | Zapis konfiguracji |

### Kalibracja

| Metoda | Endpoint                   | Cialo zapytania | Opis                       |
|--------|----------------------------|-----------------|----------------------------|
| GET    | `/api/calibration/status`  | (brak)          | Status kalibracji          |
| POST   | `/api/calibration/polaris` | (brak)          | Kalibracja na Polaris      |
| POST   | `/api/calibration/reset`   | (brak)          | Reset kalibracji           |

---

*Dokumentacja wygenerowana dla projektu SeeSky - system trackingu radioteleskopowego.*
