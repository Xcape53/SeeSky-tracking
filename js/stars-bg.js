/**
 * Animowane tlo z gwiazdami na ekranie logowania.
 * Rysuje migoczace gwiazdy i delikatne "shooting stars" na canvas.
 */
(function () {
  var canvas = document.getElementById("star-canvas");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");
  var stars = [];
  var shootingStars = [];
  var W, H;

  function resize() {
    W = canvas.width = canvas.offsetWidth;
    H = canvas.height = canvas.offsetHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  // Generuj gwiazdy
  for (var i = 0; i < 200; i++) {
    var isBordo = Math.random() < 0.08;
    var isBlue = Math.random() < 0.06;
    stars.push({
      x: Math.random() * 2000,
      y: Math.random() * 2000,
      r: Math.random() * 1.5 + 0.3,
      alpha: Math.random() * 0.6 + 0.2,
      speed: Math.random() * 0.005 + 0.002,
      phase: Math.random() * Math.PI * 2,
      color: isBordo ? "178,47,87" : isBlue ? "74,106,255" : "255,255,255",
    });
  }

  function spawnShootingStar() {
    if (shootingStars.length >= 2) return;
    shootingStars.push({
      x: Math.random() * W * 0.8,
      y: Math.random() * H * 0.4,
      len: Math.random() * 80 + 40,
      speed: Math.random() * 4 + 3,
      alpha: 1,
      angle: Math.PI / 6 + Math.random() * 0.3,
    });
  }

  function draw(t) {
    ctx.clearRect(0, 0, W, H);

    // Gwiazdy
    for (var i = 0; i < stars.length; i++) {
      var s = stars[i];
      var flicker = Math.sin(t * s.speed + s.phase) * 0.3 + 0.7;
      var a = s.alpha * flicker;
      ctx.beginPath();
      ctx.arc(s.x % W, s.y % H, s.r, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(" + s.color + "," + a.toFixed(2) + ")";
      ctx.fill();
    }

    // Spadajace gwiazdy
    for (var j = shootingStars.length - 1; j >= 0; j--) {
      var ss = shootingStars[j];
      var dx = Math.cos(ss.angle) * ss.len;
      var dy = Math.sin(ss.angle) * ss.len;

      // Smuga ciagnie sie ZA gwiazda (w przeciwnym kierunku ruchu)
      var grad = ctx.createLinearGradient(ss.x, ss.y, ss.x - dx, ss.y - dy);
      grad.addColorStop(0, "rgba(178,47,87," + ss.alpha.toFixed(2) + ")");
      grad.addColorStop(1, "rgba(178,47,87,0)");

      ctx.beginPath();
      ctx.moveTo(ss.x, ss.y);
      ctx.lineTo(ss.x - dx, ss.y - dy);
      ctx.strokeStyle = grad;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ss.x += Math.cos(ss.angle) * ss.speed;
      ss.y += Math.sin(ss.angle) * ss.speed;
      ss.alpha -= 0.008;

      if (ss.alpha <= 0 || ss.x > W || ss.y > H) {
        shootingStars.splice(j, 1);
      }
    }

    // Co jakis czas dodaj spadajaca gwiazde
    if (Math.random() < 0.015) spawnShootingStar();

    // Kontynuuj animacje tylko jesli login jest widoczny
    if (!document.getElementById("login-screen").hidden) {
      requestAnimationFrame(draw);
    }
  }

  requestAnimationFrame(draw);

  // Wznow animacje po wylogowaniu
  var origLogout = document.getElementById("logout-btn");
  if (origLogout) {
    origLogout.addEventListener("click", function () {
      setTimeout(function () {
        if (!document.getElementById("login-screen").hidden) {
          requestAnimationFrame(draw);
        }
      }, 100);
    });
  }
})();
