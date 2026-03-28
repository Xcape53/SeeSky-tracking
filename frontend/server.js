/**
 * SeeSky Frontend - serwer Node.js Express.
 *
 * Serwuje strone www (EJS) i proxy-uje zapytania API
 * do backendu Flask na porcie 5000.
 */

const express = require("express");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3000;
const API_URL = process.env.API_URL || "http://localhost:5000";

// Konfiguracja EJS
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

// Pliki statyczne
app.use(express.static(path.join(__dirname, "public")));

// Strona glowna - przekierowuje na login lub dashboard
app.get("/", (req, res) => {
  res.render("index", { apiUrl: API_URL });
});

app.listen(PORT, () => {
  console.log(`SeeSky frontend: http://localhost:${PORT}`);
  console.log(`Backend API:     ${API_URL}`);
});
