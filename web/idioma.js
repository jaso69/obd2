// OBD2Desk · solo en la página en español: la primera visita de un navegador que no
// esté en español va a la versión en inglés. Si el usuario elige idioma con el
// selector, se respeta siempre. Los buscadores no se redirigen.
(function () {
  try {
    var elegido = localStorage.getItem("idioma");
    if (elegido === "es") return;
    if (elegido === "en") { location.replace("en/" + location.hash); return; }
    if (/bot|crawl|spider|slurp|preview/i.test(navigator.userAgent)) return;
    var idiomas = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ""];
    var habla = idiomas.some(function (l) { return /^(es|ca|gl|eu)\b/i.test(l); });
    if (!habla) location.replace("en/" + location.hash);
  } catch (e) { /* sin localStorage: se queda en español */ }
})();
