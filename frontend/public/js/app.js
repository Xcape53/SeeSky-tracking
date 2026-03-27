/**
 * SeeSky Frontend - logika klienta.
 * Komunikuje sie z Flask API poprzez fetch().
 */

let token = null;
let trackingInterval = null;
let starPage = 1;
let starTotalPages = 1;
let skyMapInitialized = false;
let telescopeRA = null;
let telescopeDec = null;
let telescopeIsTracking = false;
let observerLat = 51.1079;
let observerLon = 17.0385;

// --- Pomocnicze ---

async function api(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (token) opts.headers["Authorization"] = "Bearer " + token;
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(API_URL + path, opts);
  const data = await res.json();
  if (!res.ok) throw { status: res.status, ...data };
  return data;
}

function formatTime(seconds) {
  if (seconds == null) return "-";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m + "m " + s + "s";
}

function deg(val) {
  if (val == null) return "-";
  return val.toFixed(4) + "\u00b0";
}

function degPerSec(val) {
  if (val == null) return "-";
  return val.toFixed(6) + "\u00b0/s";
}

function hoursToHMS(h) {
  if (h == null) return "-";
  var neg = h < 0;
  h = Math.abs(h);
  var hh = Math.floor(h);
  var mm = Math.floor((h - hh) * 60);
  var ss = ((h - hh) * 3600 - mm * 60).toFixed(1);
  return (neg ? "-" : "") + pad2(hh) + "h " + pad2(mm) + "m " + ss + "s";
}

function pad2(n) { return n < 10 ? "0" + n : "" + n; }
function pad3(n) { return n < 10 ? "00" + n : n < 100 ? "0" + n : "" + n; }

// --- Nawigacja ---

document.querySelectorAll(".nav-btn[data-tab]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn[data-tab]").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".tab-content").forEach((t) => (t.hidden = true));
    document.getElementById("tab-" + btn.dataset.tab).hidden = false;

    // Zaladuj dane po przelaczeniu taba
    if (btn.dataset.tab === "catalog") loadStars();
    if (btn.dataset.tab === "queue") loadQueue();
    if (btn.dataset.tab === "config") loadConfig();
    if (btn.dataset.tab === "calibration") loadCalibration();
    if (btn.dataset.tab === "skymap") initSkyMap();
  });
});

// --- Login / Logout ---

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errEl = document.getElementById("login-error");
  errEl.hidden = true;
  try {
    const data = await api("POST", "/api/auth/login", {
      username: document.getElementById("login-user").value,
      password: document.getElementById("login-pass").value,
    });
    token = data.token;
    document.getElementById("login-screen").hidden = true;
    document.getElementById("dashboard").hidden = false;
    startTrackingPolling();
  } catch (err) {
    errEl.textContent = err.message || "Blad logowania";
    errEl.hidden = false;
  }
});

document.getElementById("logout-btn").addEventListener("click", async () => {
  try { await api("POST", "/api/auth/logout"); } catch (_) {}
  token = null;
  stopTrackingPolling();
  document.getElementById("dashboard").hidden = true;
  document.getElementById("login-screen").hidden = false;
});

// --- Tracking ---

async function updateTrackingStatus() {
  try {
    const s = await api("GET", "/api/tracking/status");
    const ind = document.getElementById("tracking-indicator");
    if (s.is_tracking && s.is_paused) {
      ind.textContent = "WSTRZYMANY";
      ind.className = "status-indicator paused";
    } else if (s.is_tracking) {
      ind.textContent = "AKTYWNY";
      ind.className = "status-indicator active";
    } else {
      ind.textContent = "NIEAKTYWNY";
      ind.className = "status-indicator";
    }

    const star = s.current_star;
    document.getElementById("tracking-star").textContent =
      star ? (star.name || "Gwiazda #" + star.id) : "-";

    // Detale gwiazdy
    const details = document.getElementById("tracking-star-details");
    if (star) {
      var parts = [];
      if (star.constellation) parts.push("Gwiazdozbior: " + star.constellation);
      if (star.magnitude != null) parts.push("Mag: " + star.magnitude.toFixed(2));
      details.innerHTML = parts.map(function(p) { return "<span>" + p + "</span>"; }).join("");
    } else {
      details.innerHTML = "";
    }

    document.getElementById("t-alt").textContent = deg(s.current_alt);
    document.getElementById("t-az").textContent = deg(s.current_az);
    document.getElementById("t-tgt-alt").textContent = deg(s.target_alt);
    document.getElementById("t-tgt-az").textContent = deg(s.target_az);
    document.getElementById("t-d-alt").textContent = deg(s.delta_alt);
    document.getElementById("t-d-az").textContent = deg(s.delta_az);
    document.getElementById("t-v-alt").textContent = degPerSec(s.velocity_alt);
    document.getElementById("t-v-az").textContent = degPerSec(s.velocity_az);
    document.getElementById("t-elapsed").textContent = formatTime(s.elapsed_time);
    document.getElementById("t-remaining").textContent = formatTime(s.remaining_time);

    // Nowe pola
    document.getElementById("t-ang-dist").textContent =
      s.angular_distance != null ? s.angular_distance.toFixed(6) + "\u00b0" : "-";
    document.getElementById("t-radec").textContent =
      star ? star.ra.toFixed(4) + "\u00b0 / " + star.dec.toFixed(4) + "\u00b0" : "-";
    document.getElementById("t-ha").textContent = hoursToHMS(s.hour_angle);
    document.getElementById("t-lst").textContent = hoursToHMS(s.lst_hours);

    // Aktualizuj dane dla mapy nieba
    if (s.current_star && s.current_star.ra != null) {
      telescopeRA = s.current_star.ra;
      telescopeDec = s.current_star.dec;
      telescopeIsTracking = true;
    } else {
      // Nie kasuj RA/Dec - zachowaj ostatnia znana pozycje
      telescopeIsTracking = false;
    }

    // Aktualizuj info na mapie nieba
    const skyInfo = document.getElementById("skymap-tracking-info");
    if (s.is_tracking && s.current_star) {
      skyInfo.innerHTML = '<span class="tracking-active">Tracking aktywny:</span> ' +
        (s.current_star.name || "Gwiazda #" + s.current_star.id) +
        " | Alt: " + deg(s.current_alt) + " Az: " + deg(s.current_az);
    } else if (telescopeRA != null) {
      skyInfo.innerHTML = '<span style="color:#7b87ab">Ostatnia pozycja:</span> RA:' +
        telescopeRA.toFixed(2) + "\u00b0 Dec:" + telescopeDec.toFixed(2) + "\u00b0";
    } else {
      skyInfo.textContent = "Tracking nieaktywny";
    }

    // Przerysuj mape nieba
    if (skyMapInitialized) updateSkyMapPointer();

    // Przyciski
    document.getElementById("btn-start").disabled = s.is_tracking;
    document.getElementById("btn-pause").disabled = !s.is_tracking || s.is_paused;
    document.getElementById("btn-resume").disabled = !s.is_tracking || !s.is_paused;
    document.getElementById("btn-stop").disabled = !s.is_tracking;
  } catch (_) {}
}

function startTrackingPolling() {
  updateTrackingStatus();
  trackingInterval = setInterval(updateTrackingStatus, 500);
}

function stopTrackingPolling() {
  if (trackingInterval) clearInterval(trackingInterval);
}

// --- Zegar zsynchronizowany z NTP (WorldTimeAPI) ---
(function runClock() {
  var ntpOffsetMs = 0; // roznica: czas_atomowy - czas_lokalny
  var ntpSynced = false;

  // Synchronizuj z WorldTimeAPI (czas atomowy)
  function syncNTP() {
    var t0 = Date.now();
    fetch("https://worldtimeapi.org/api/timezone/Etc/UTC")
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var t1 = Date.now();
        var rtt = t1 - t0; // round-trip time
        var serverMs = new Date(data.utc_datetime).getTime();
        // Kompensuj polowe opoznienia sieciowego
        ntpOffsetMs = serverMs - t0 - Math.round(rtt / 2);
        ntpSynced = true;
        var syncEl = document.getElementById("clock-sync");
        if (syncEl) {
          syncEl.textContent = "NTP: " + (ntpOffsetMs >= 0 ? "+" : "") + ntpOffsetMs + "ms";
          syncEl.className = "clock-sync synced";
        }
        console.log("NTP sync OK, offset: " + ntpOffsetMs + "ms (RTT: " + rtt + "ms)");
      })
      .catch(function() {
        console.warn("NTP sync failed - using local clock");
        var syncEl = document.getElementById("clock-sync");
        if (syncEl && !ntpSynced) {
          syncEl.textContent = "NTP: brak";
          syncEl.className = "clock-sync unsynced";
        }
      });
  }

  syncNTP();
  // Resynchronizuj co 5 minut
  setInterval(syncNTP, 5 * 60 * 1000);

  function tick() {
    var corrected = new Date(Date.now() + ntpOffsetMs);
    var utcEl = document.getElementById("clock-utc");
    var locEl = document.getElementById("clock-local");
    if (utcEl) {
      utcEl.textContent =
        pad2(corrected.getUTCHours()) + ":" + pad2(corrected.getUTCMinutes()) + ":" +
        pad2(corrected.getUTCSeconds()) + "." + pad3(corrected.getUTCMilliseconds());
    }
    if (locEl) {
      var local = new Date(corrected.getTime());
      locEl.textContent =
        pad2(local.getHours()) + ":" + pad2(local.getMinutes()) + ":" +
        pad2(local.getSeconds()) + "." + pad3(local.getMilliseconds());
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
})();

document.getElementById("btn-start").addEventListener("click", async () => {
  try {
    await api("POST", "/api/tracking/start");
  } catch (err) {
    alert(err.message || "Blad startu trackingu");
  }
});

document.getElementById("btn-stop").addEventListener("click", async () => {
  try {
    await api("POST", "/api/tracking/stop");
  } catch (err) {
    alert(err.message || "Blad stopu trackingu");
  }
});

document.getElementById("btn-pause").addEventListener("click", async () => {
  try {
    await api("POST", "/api/tracking/pause");
  } catch (err) {
    alert(err.message || "Blad pauzy");
  }
});

document.getElementById("btn-resume").addEventListener("click", async () => {
  try {
    await api("POST", "/api/tracking/resume");
  } catch (err) {
    alert(err.message || "Blad wznowienia");
  }
});

// --- Katalog gwiazd ---

async function loadStars() {
  const search = document.getElementById("star-search").value;
  const maxMag = document.getElementById("star-max-mag").value;
  const constellation = document.getElementById("star-constellation").value;

  let params = `?page=${starPage}&per_page=20`;
  if (search) params += `&search=${encodeURIComponent(search)}`;
  if (maxMag) params += `&max_magnitude=${maxMag}`;
  if (constellation) params += `&constellation=${encodeURIComponent(constellation)}`;

  try {
    const data = await api("GET", "/api/stars" + params);
    const tbody = document.getElementById("star-tbody");
    tbody.innerHTML = "";
    for (const s of data.stars) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${s.name || "-"}</td>
        <td>${s.constellation || "-"}</td>
        <td>${s.magnitude != null ? s.magnitude.toFixed(2) : "-"}</td>
        <td>${s.ra != null ? s.ra.toFixed(4) : "-"}</td>
        <td>${s.dec != null ? s.dec.toFixed(4) : "-"}</td>
        <td>
          <button class="btn btn-blue" onclick="addToQueue(${s.id})">Dodaj</button>
          <button class="btn" onclick="showPosition(${s.id})">Pozycja</button>
        </td>
      `;
      tbody.appendChild(tr);
    }
    starTotalPages = data.pagination.total_pages;
    document.getElementById("star-page-info").textContent =
      data.pagination.page + " / " + starTotalPages;
    document.getElementById("star-prev").disabled = starPage <= 1;
    document.getElementById("star-next").disabled = starPage >= starTotalPages;
  } catch (err) {
    console.error("loadStars error:", err);
  }
}

document.getElementById("star-filter-btn").addEventListener("click", () => {
  starPage = 1;
  loadStars();
});

document.getElementById("star-prev").addEventListener("click", () => {
  if (starPage > 1) { starPage--; loadStars(); }
});
document.getElementById("star-next").addEventListener("click", () => {
  if (starPage < starTotalPages) { starPage++; loadStars(); }
});

async function addToQueue(starId) {
  const duration = prompt("Czas obserwacji (minuty):", "30");
  if (!duration) return;
  const priority = prompt("Priorytet (0 = domyslny):", "0");
  try {
    await api("POST", "/api/queue", {
      star_id: starId,
      duration_minutes: parseInt(duration),
      priority: parseInt(priority || "0"),
    });
    alert("Dodano do kolejki!");
  } catch (err) {
    alert(err.message || "Blad dodawania do kolejki");
  }
}

async function showPosition(starId) {
  try {
    const pos = await api("GET", "/api/stars/" + starId + "/position");
    const aboveText = pos.is_above_horizon ? "TAK" : "NIE";
    alert(
      `Pozycja gwiazdy:\nAlt: ${pos.alt}\u00b0\nAz: ${pos.az}\u00b0\nNad horyzontem: ${aboveText}\nObliczono: ${pos.calculated_at}`
    );
  } catch (err) {
    alert(err.message || "Blad obliczania pozycji");
  }
}

// Expose to inline onclick
window.addToQueue = addToQueue;
window.showPosition = showPosition;

// --- Kolejka ---

async function loadQueue() {
  try {
    const data = await api("GET", "/api/queue");
    const tbody = document.getElementById("queue-tbody");
    const emptyMsg = document.getElementById("queue-empty");
    tbody.innerHTML = "";

    if (data.queue.length === 0) {
      emptyMsg.hidden = false;
      return;
    }
    emptyMsg.hidden = true;

    for (const o of data.queue) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${o.id}</td>
        <td>${o.star_name || "Gwiazda #" + o.star_id}</td>
        <td>${o.duration_minutes}</td>
        <td>${o.priority}</td>
        <td>${o.status}</td>
        <td>
          <button class="btn btn-red" onclick="removeFromQueue(${o.id})">Usun</button>
        </td>
      `;
      tbody.appendChild(tr);
    }
  } catch (err) {
    console.error("loadQueue error:", err);
  }
}

async function removeFromQueue(obsId) {
  if (!confirm("Usunac obserwacje #" + obsId + "?")) return;
  try {
    await api("DELETE", "/api/queue/" + obsId);
    loadQueue();
  } catch (err) {
    alert(err.message || "Blad usuwania");
  }
}
window.removeFromQueue = removeFromQueue;

// --- Konfiguracja ---

async function loadConfig() {
  try {
    const cfg = await api("GET", "/api/config");
    observerLat = cfg.latitude;
    observerLon = cfg.longitude;
    document.getElementById("cfg-lat").value = cfg.latitude;
    document.getElementById("cfg-lon").value = cfg.longitude;
    document.getElementById("cfg-alt").value = cfg.altitude;
    document.getElementById("cfg-interval").value = cfg.tracking_interval_seconds;
    document.getElementById("cfg-duration").value = cfg.default_observation_duration_minutes;
    document.getElementById("cfg-pressure").value = cfg.pressure;
    document.getElementById("cfg-temp").value = cfg.temperature;
    document.getElementById("cfg-humidity").value = cfg.humidity;
  } catch (err) {
    console.error("loadConfig error:", err);
  }
}

document.getElementById("config-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msgEl = document.getElementById("config-msg");
  try {
    await api("PUT", "/api/config", {
      latitude: parseFloat(document.getElementById("cfg-lat").value),
      longitude: parseFloat(document.getElementById("cfg-lon").value),
      altitude: parseFloat(document.getElementById("cfg-alt").value),
      tracking_interval_seconds: parseFloat(document.getElementById("cfg-interval").value),
      default_observation_duration_minutes: parseInt(document.getElementById("cfg-duration").value),
      pressure: parseFloat(document.getElementById("cfg-pressure").value),
      temperature: parseFloat(document.getElementById("cfg-temp").value),
      humidity: parseFloat(document.getElementById("cfg-humidity").value),
    });
    msgEl.textContent = "Konfiguracja zapisana!";
    msgEl.className = "success";
    msgEl.hidden = false;
    setTimeout(() => (msgEl.hidden = true), 3000);
  } catch (err) {
    msgEl.textContent = err.message || "Blad zapisu";
    msgEl.className = "error";
    msgEl.hidden = false;
  }
});

// --- Kalibracja ---

async function loadCalibration() {
  try {
    const cal = await api("GET", "/api/calibration/status");
    document.getElementById("cal-status").textContent =
      cal.is_calibrated ? "SKALIBROWANY" : "NIESKALIBROWANY";
    document.getElementById("cal-status").style.color =
      cal.is_calibrated ? "var(--green)" : "var(--text2)";
    document.getElementById("cal-offset-az").textContent = cal.offset_az.toFixed(4) + "\u00b0";
    document.getElementById("cal-offset-alt").textContent = cal.offset_alt.toFixed(4) + "\u00b0";
    document.getElementById("cal-time").textContent = cal.last_calibration_time || "-";
  } catch (err) {
    console.error("loadCalibration error:", err);
  }
}

document.getElementById("btn-cal-polaris").addEventListener("click", async () => {
  const msgEl = document.getElementById("cal-msg");
  try {
    const data = await api("POST", "/api/calibration/polaris");
    msgEl.textContent = data.message;
    msgEl.className = "success";
    msgEl.hidden = false;
    loadCalibration();
  } catch (err) {
    msgEl.textContent = err.message || "Blad kalibracji";
    msgEl.className = "error";
    msgEl.hidden = false;
  }
});

document.getElementById("btn-cal-reset").addEventListener("click", async () => {
  if (!confirm("Resetowac kalibracje?")) return;
  const msgEl = document.getElementById("cal-msg");
  try {
    await api("POST", "/api/calibration/reset");
    msgEl.textContent = "Kalibracja zresetowana";
    msgEl.className = "success";
    msgEl.hidden = false;
    loadCalibration();
  } catch (err) {
    msgEl.textContent = err.message || "Blad resetu";
    msgEl.className = "error";
    msgEl.hidden = false;
  }
});

// --- Mapa nieba (d3-celestial) ---

// Konwersja RA stopnie (0-360) na format d3-celestial (-180..+180)
function raToD3(raDeg) {
  return raDeg > 180 ? raDeg - 360 : raDeg;
}

var celestialConfig = null;

function initSkyMap() {
  if (skyMapInitialized) {
    // Odswierz czas i pozycje
    if (typeof Celestial !== "undefined") {
      Celestial.date(new Date());
      updateSkyMapPointer();
    }
    return;
  }

  if (typeof Celestial === "undefined") {
    document.getElementById("celestial-map").innerHTML =
      '<p style="color:#888;padding:40px;text-align:center">Ladowanie biblioteki d3-celestial...</p>';
    setTimeout(initSkyMap, 500);
    return;
  }

  // Pobierz konfiguracje obserwatora
  api("GET", "/api/config").then(function(cfg) {
    observerLat = cfg.latitude;
    observerLon = cfg.longitude;
    buildSkyMap();
  }).catch(function() {
    buildSkyMap();
  });
}

function buildSkyMap() {
  // Wyczysc kontener
  document.getElementById("celestial-map").innerHTML = "";

  celestialConfig = {
    width: 0,  // 0 = pełna szerokosc rodzica
    projection: "airy",
    geopos: [observerLat, observerLon],
    follow: "zenith",
    container: "celestial-map",
    datapath: "https://ofrohn.github.io/data/",

    // Tło
    background: { fill: "#0a0e17", opacity: 1, stroke: "#1a2235", width: 1 },

    // Gwiazdy
    stars: {
      show: true,
      limit: 6,
      colors: true,
      style: { fill: "#ffffff", opacity: 1 },
      designation: false,
      propername: true,
      propernameStyle: {
        fill: "#8899bb", font: "11px 'Segoe UI', sans-serif",
        align: "left", baseline: "top"
      },
      propernameLimit: 2.5,
      size: 7,
      exponent: -0.28
    },

    // Mgławice
    dsos: {
      show: true,
      limit: 6,
      colors: true,
      style: { fill: "#444444", stroke: "#444444", width: 2, opacity: 1 },
      names: true,
      namesLimit: 4,
      nameStyle: { fill: "#556677", font: "10px 'Segoe UI', sans-serif" }
    },

    // Gwiazdozbiory
    constellations: {
      names: true,
      namesType: "iau",
      nameStyle: {
        fill: "#334466", font: "bold 13px 'Segoe UI', sans-serif",
        align: "center", baseline: "middle"
      },
      lines: true,
      lineStyle: { stroke: "#2a3555", width: 1.2, opacity: 0.6 },
      bounds: false
    },

    // Droga Mleczna
    mw: {
      show: true,
      style: { fill: "#0d1525", opacity: 0.15 }
    },

    // Linie siatki
    lines: {
      graticule: {
        show: true,
        stroke: "#1a2235",
        width: 0.5,
        opacity: 0.4,
        lon: { pos: [], fill: "#334466", font: "9px sans-serif" },
        lat: { pos: [], fill: "#334466", font: "9px sans-serif" }
      },
      equatorial: { show: true, stroke: "#2244aa", width: 0.8, opacity: 0.3 },
      ecliptic: { show: false },
      galactic: { show: false },
      supergalactic: { show: false }
    },

    // Horyzont - wyrazna linia oddzielajaca widoczne niebo
    horizon: {
      show: true,
      stroke: "#b22f57",
      width: 3,
      fill: "#000000",
      opacity: 0.5
    },

    // Planety
    planets: { show: false },
    daylight: { show: false },

    // Ukryj panele kontrolne
    controls: false,
    formFields: {
      location: false, general: false, stars: false, dsos: false,
      constellations: false, lines: false, other: false, download: false
    }
  };

  // Zarejestruj callback rysowania - po kazdym renderze mapy odswiez overlay
  Celestial.add({
    type: "raw",
    callback: function(error) {
      if (error) return console.warn(error);
    },
    redraw: function() {
      drawOverlay();
    }
  });

  Celestial.display(celestialConfig);
  skyMapInitialized = true;

  // Stworz overlay canvas na wierzchu mapy
  setupOverlayCanvas();

  // Odswierzaj czas co 30s
  setInterval(function() {
    if (skyMapInitialized && !document.getElementById("tab-skymap").hidden) {
      Celestial.date(new Date());
      // Po zmianie czasu przerysuj overlay
      setTimeout(drawOverlay, 200);
    }
  }, 30000);
}

var overlayCanvas = null;
var overlayCtx = null;
var mapClip = null;
var svgOffsetX = 0; // przesuniecie SVG wzgledem kontenera
var svgOffsetY = 0;
var projScaleX = 1; // skala SVG coords -> piksele kontenera
var projScaleY = 1;

function setupOverlayCanvas() {
  var container = document.getElementById("celestial-map");
  container.style.position = "relative";

  overlayCanvas = document.createElement("canvas");
  overlayCanvas.id = "telescope-overlay";
  overlayCanvas.style.cssText =
    "position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:50;";
  container.appendChild(overlayCanvas);
  overlayCtx = overlayCanvas.getContext("2d");

  function tryInit(attempt) {
    recalcOverlay();
    if (overlayCanvas.width > 10 && mapClip) {
      drawOverlay();
    } else if (attempt < 15) {
      setTimeout(function() { tryInit(attempt + 1); }, 400);
    }
  }
  setTimeout(function() { tryInit(0); }, 300);

  window.addEventListener("resize", function() { recalcOverlay(); drawOverlay(); });

  // Przerysuj po pan/drag mapy — obserwuj tylko SVG, nie canvas
  var drawPending = false;
  var observer = new MutationObserver(function(mutations) {
    // Ignoruj zmiany w naszym ukladzie overlay
    for (var i = 0; i < mutations.length; i++) {
      if (mutations[i].target === overlayCanvas) return;
    }
    if (!drawPending) {
      drawPending = true;
      requestAnimationFrame(function() {
        drawPending = false;
        drawOverlay();
      });
    }
  });
  var svg = container.querySelector("svg");
  if (svg) {
    observer.observe(svg, { childList: true, subtree: true, attributes: true });
  }
}

function recalcOverlay() {
  if (!overlayCanvas) return;
  var container = document.getElementById("celestial-map");
  overlayCanvas.width = container.clientWidth;
  overlayCanvas.height = container.clientHeight;

  var svg = container.querySelector("svg");
  if (!svg) return;

  // Offset SVG w kontenerze (SVG moze byc wycentrowany margin:0 auto)
  var cRect = container.getBoundingClientRect();
  var sRect = svg.getBoundingClientRect();
  svgOffsetX = sRect.left - cRect.left;
  svgOffsetY = sRect.top - cRect.top;

  // Skala: SVG wewnetrzne coords -> piksele wyswietlane
  var svgAttrW = parseFloat(svg.getAttribute("width")) || svg.clientWidth;
  var svgAttrH = parseFloat(svg.getAttribute("height")) || svg.clientHeight;
  projScaleX = sRect.width / svgAttrW;
  projScaleY = sRect.height / svgAttrH;

  // Okrag mapy
  mapClip = null;
  var outline = svg.querySelector("path.outline");
  if (outline) {
    try {
      var bb = outline.getBBox();
      if (bb.width > 10) {
        mapClip = {
          cx: svgOffsetX + (bb.x + bb.width / 2) * projScaleX,
          cy: svgOffsetY + (bb.y + bb.height / 2) * projScaleY,
          r: Math.min(bb.width * projScaleX, bb.height * projScaleY) / 2
        };
      }
    } catch (e) {}
  }
  if (!mapClip) {
    mapClip = {
      cx: svgOffsetX + sRect.width / 2,
      cy: svgOffsetY + sRect.height / 2,
      r: Math.min(sRect.width, sRect.height) / 2 - 2
    };
  }
}

// Przelicz punkt z projekcji d3-celestial na piksele canvasa
function projToCanvas(svgPt) {
  if (!svgPt) return null;
  return [
    svgOffsetX + svgPt[0] * projScaleX,
    svgOffsetY + svgPt[1] * projScaleY
  ];
}

function getProjection() {
  if (typeof Celestial.mapProjection === "function") return Celestial.mapProjection;
  if (typeof Celestial.projection === "function") return Celestial.projection;
  return null;
}

function drawOverlay() {
  if (!overlayCtx || !overlayCanvas) return;
  recalcOverlay();
  if (overlayCanvas.width < 10 || !mapClip || mapClip.r < 10) return;
  overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

  // Przytnij do okragu mapy
  overlayCtx.save();
  overlayCtx.beginPath();
  overlayCtx.arc(mapClip.cx, mapClip.cy, mapClip.r - 2, 0, 2 * Math.PI);
  overlayCtx.clip();

  drawAltitudeGrid();
  drawTelescopePointer();

  overlayCtx.restore();
}

// Rysuje pierscienie elewacji (Alt = 0, 15, 30, 45, 60, 75) i etykiety azymutalne
function drawAltitudeGrid() {
  var proj = getProjection();
  if (!proj) return;

  var ctx = overlayCtx;
  var W = overlayCanvas.width;
  var H = overlayCanvas.height;

  // Potrzebujemy LST (local sidereal time) do konwersji Alt/Az -> RA/Dec
  // Oblicz LST z pozycji obserwatora
  var now = new Date();
  // Przyblizony Julian Date
  var JD = now.getTime() / 86400000 + 2440587.5;
  var T = (JD - 2451545.0) / 36525.0;
  // Greenwich Mean Sidereal Time w godzinach
  var GMST = 280.46061837 + 360.98564736629 * (JD - 2451545.0) + 0.000387933 * T * T;
  GMST = ((GMST % 360) + 360) % 360; // 0-360 stopni
  var LST = GMST + observerLon; // Local Sidereal Time w stopniach
  LST = ((LST % 360) + 360) % 360;

  var latRad = observerLat * Math.PI / 180;

  // Funkcja: Alt/Az -> RA/Dec
  function altAzToRaDec(altDeg, azDeg) {
    var altR = altDeg * Math.PI / 180;
    var azR = azDeg * Math.PI / 180;
    var sinDec = Math.sin(altR) * Math.sin(latRad) + Math.cos(altR) * Math.cos(latRad) * Math.cos(azR);
    var dec = Math.asin(sinDec);
    var cosHA = (Math.sin(altR) - Math.sin(latRad) * sinDec) / (Math.cos(latRad) * Math.cos(dec));
    cosHA = Math.max(-1, Math.min(1, cosHA));
    var HA = Math.acos(cosHA);
    if (Math.sin(azR) > 0) HA = 2 * Math.PI - HA;
    var raDeg = LST - HA * 180 / Math.PI;
    raDeg = ((raDeg % 360) + 360) % 360;
    return [raToD3(raDeg), dec * 180 / Math.PI];
  }

  // Rysuj pierscienie elewacji
  var altitudes = [
    { alt: 0, color: "#b22f57", width: 2.5, dash: [], label: "HORYZONT (0\u00b0)" },
    { alt: 15, color: "#553344", width: 0.8, dash: [6, 4], label: "15\u00b0" },
    { alt: 30, color: "#444466", width: 0.8, dash: [6, 4], label: "30\u00b0" },
    { alt: 45, color: "#444466", width: 0.8, dash: [4, 4], label: "45\u00b0" },
    { alt: 60, color: "#444466", width: 0.8, dash: [4, 4], label: "60\u00b0" },
    { alt: 75, color: "#334455", width: 0.5, dash: [3, 5], label: "75\u00b0" },
  ];

  for (var a = 0; a < altitudes.length; a++) {
    var ring = altitudes[a];
    var points = [];

    // Sampluj 72 punkty co 5 stopni azymutu
    for (var az = 0; az < 360; az += 5) {
      var rd = altAzToRaDec(ring.alt, az);
      var raw = proj(rd);
      var pt = projToCanvas(raw);
      if (pt && !isNaN(pt[0]) && !isNaN(pt[1]) && pt[0] > -100 && pt[0] < W + 100 && pt[1] > -100 && pt[1] < H + 100) {
        points.push(pt);
      }
    }

    if (points.length < 3) continue;

    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    for (var p = 1; p < points.length; p++) {
      ctx.lineTo(points[p][0], points[p][1]);
    }
    ctx.closePath();
    ctx.strokeStyle = ring.color;
    ctx.lineWidth = ring.width;
    ctx.setLineDash(ring.dash);
    ctx.stroke();
    ctx.setLineDash([]);

    // Etykieta na pozycji Az=0 (polnoc)
    var labelRd = altAzToRaDec(ring.alt, 0);
    var labelPt = projToCanvas(proj(labelRd));
    if (labelPt && !isNaN(labelPt[0]) && labelPt[0] > 10 && labelPt[0] < W - 10 &&
        labelPt[1] > 10 && labelPt[1] < H - 10) {
      ctx.font = ring.alt === 0 ? "bold 11px 'Segoe UI', sans-serif" : "10px 'Segoe UI', sans-serif";
      ctx.fillStyle = ring.color;
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      ctx.fillText(ring.label, labelPt[0], labelPt[1] - 4);
    }
  }

  // Etykiety kierunkow swiata na horyzoncie
  var directions = [
    { az: 0, label: "N" }, { az: 90, label: "E" },
    { az: 180, label: "S" }, { az: 270, label: "W" }
  ];
  for (var d = 0; d < directions.length; d++) {
    var dir = directions[d];
    var drd = altAzToRaDec(0, dir.az);
    var dpt = projToCanvas(proj(drd));
    if (dpt && !isNaN(dpt[0]) && dpt[0] > 5 && dpt[0] < W - 5 && dpt[1] > 5 && dpt[1] < H - 5) {
      ctx.font = "bold 14px 'Segoe UI', sans-serif";
      ctx.fillStyle = "#b22f57";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(dir.label, dpt[0], dpt[1]);
    }
  }
}

function drawTelescopePointer() {
  if (telescopeRA == null || telescopeDec == null) return;
  if (!overlayCtx || !overlayCanvas) return;

  try {
    var proj = getProjection();
    if (!proj) {
      console.warn("Brak projekcji d3-celestial");
      return;
    }

    var coords = [raToD3(telescopeRA), telescopeDec];
    var pt = projToCanvas(proj(coords));
    if (!pt || isNaN(pt[0]) || isNaN(pt[1])) return;

    var W = overlayCanvas.width;
    var H = overlayCanvas.height;

    // Sprawdz czy punkt jest w widocznym obszarze
    if (pt[0] < -50 || pt[0] > W + 50 || pt[1] < -50 || pt[1] > H + 50) return;

    var ctx = overlayCtx;
    var active = telescopeIsTracking;
    var mainColor = active ? "#ff3333" : "#666688";
    var ringColor = active ? "#33ff33" : "#444466";
    var accentColor = active ? "#b22f57" : "#555577";
    var labelColor = active ? "#ff5555" : "#7777aa";
    var coordColor = active ? "#33ff33" : "#666688";
    var glowColor = active ? "#ff3333" : "#555577";
    var label = active ? "TELESKOP" : "OSTATNIA POZYCJA";

    // Zewnetrzny pierscien
    ctx.beginPath();
    ctx.arc(pt[0], pt[1], 16, 0, 2 * Math.PI);
    ctx.strokeStyle = ringColor;
    ctx.lineWidth = active ? 2 : 1.5;
    if (!active) ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Drugi pierscien (bordowy/szary)
    ctx.beginPath();
    ctx.arc(pt[0], pt[1], 10, 0, 2 * Math.PI);
    ctx.strokeStyle = accentColor;
    ctx.lineWidth = 1.5;
    if (!active) ctx.setLineDash([3, 3]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Krzyzyk celownika
    ctx.beginPath();
    ctx.moveTo(pt[0] - 24, pt[1]);
    ctx.lineTo(pt[0] - 10, pt[1]);
    ctx.moveTo(pt[0] + 10, pt[1]);
    ctx.lineTo(pt[0] + 24, pt[1]);
    ctx.moveTo(pt[0], pt[1] - 24);
    ctx.lineTo(pt[0], pt[1] - 10);
    ctx.moveTo(pt[0], pt[1] + 10);
    ctx.lineTo(pt[0], pt[1] + 24);
    ctx.strokeStyle = mainColor;
    ctx.lineWidth = active ? 2.5 : 1.5;
    ctx.stroke();

    // Srodkowa kropka z poswiatą
    ctx.beginPath();
    ctx.arc(pt[0], pt[1], 3, 0, 2 * Math.PI);
    ctx.fillStyle = mainColor;
    ctx.shadowColor = glowColor;
    ctx.shadowBlur = active ? 10 : 4;
    ctx.fill();
    ctx.shadowBlur = 0;

    // Etykieta
    ctx.font = "bold 13px 'Segoe UI', sans-serif";
    ctx.fillStyle = labelColor;
    ctx.textAlign = "left";
    ctx.textBaseline = "bottom";
    ctx.fillText(label, pt[0] + 26, pt[1] - 8);

    // Wspolrzedne RA/Dec
    ctx.font = "11px 'Segoe UI', sans-serif";
    ctx.fillStyle = coordColor;
    ctx.textBaseline = "top";
    ctx.fillText("RA:" + telescopeRA.toFixed(2) + "\u00b0 Dec:" + telescopeDec.toFixed(2) + "\u00b0", pt[0] + 26, pt[1] + 4);
  } catch (e) {
    console.warn("drawTelescopePointer error:", e);
  }
}

function updateSkyMapPointer() {
  if (!skyMapInitialized || typeof Celestial === "undefined") return;
  // Rysuj na overlay canvas - siatke elewacji + pointer
  drawOverlay();
}
