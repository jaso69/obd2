// OBD2Desk · menú móvil, selector de capturas, visor y enlaces de descarga

const EN = document.documentElement.lang === "en";
const T = EN
  ? { sinPaquete: "No package published yet: open the releases page",
      version: (v, f) => `Latest version: <strong>${v}</strong> (${f}). All versions on `, locale: "en-GB" }
  : { sinPaquete: "Todavía no hay paquete publicado: abre la página de versiones",
      version: (v, f) => `Última versión: <strong>${v}</strong> (${f}). Todas las versiones en `, locale: "es-ES" };

// Selector de idioma: recuerda la elección (idioma.js la respeta)
document.querySelectorAll("[data-idioma]").forEach((a) => {
  a.addEventListener("click", () => {
    try { localStorage.setItem("idioma", a.dataset.idioma); } catch (e) { /* sin almacenamiento */ }
    a.href = a.getAttribute("href").split("#")[0] + location.hash;
  });
});

// Menú en móvil
const menuBoton = document.querySelector(".menu-boton");
const menu = document.getElementById("menu");
menuBoton.addEventListener("click", () => {
  const abierto = menu.classList.toggle("abierto");
  menuBoton.setAttribute("aria-expanded", abierto);
});
menu.addEventListener("click", (e) => {
  if (e.target.tagName === "A") {
    menu.classList.remove("abierto");
    menuBoton.setAttribute("aria-expanded", "false");
  }
});

// Selector KKL / OBD2 de las capturas
document.querySelectorAll(".selector").forEach((sel) => {
  const enlace = document.querySelector(`.ampliar[data-grupo="${sel.dataset.grupo}"]`);
  sel.querySelectorAll("button").forEach((b) => {
    b.addEventListener("click", () => {
      sel.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      enlace.href = b.dataset.img;
      enlace.querySelector("img").src = b.dataset.img;
      enlace.querySelector("img").alt = b.dataset.alt;
    });
  });
});

// Visor de capturas a tamaño completo
const visor = document.getElementById("visor");
document.querySelectorAll(".ampliar").forEach((a) => {
  a.addEventListener("click", (e) => {
    if (!visor.showModal) return;          // navegador sin <dialog>: abre la imagen
    e.preventDefault();
    const img = visor.querySelector("img");
    img.src = a.href;
    img.alt = a.querySelector("img").alt;
    visor.showModal();
  });
});
visor.addEventListener("click", () => visor.close());

// Enlaces de descarga: la última versión publicada (también pre-releases).
// Sin JavaScript o si falla la API, los botones llevan a la página de releases.
fetch("https://api.github.com/repos/jaso69/obd2/releases?per_page=10")
  .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
  .then((releases) => {
    const publicadas = releases.filter((r) => !r.draft);
    const buscar = (patron) => {
      for (const r of publicadas) {
        const a = r.assets.find((x) => patron.test(x.name));
        if (a) return { url: a.browser_download_url, version: r.tag_name, mb: Math.round(a.size / 1048576) };
      }
      return null;
    };
    const archivos = { windows: buscar(/\.exe$/i), linux: buscar(/linux.*\.tar\.gz$/i) };
    document.querySelectorAll("[data-descarga]").forEach((b) => {
      const f = archivos[b.dataset.descarga];
      if (f) {
        b.href = f.url;
        b.title = `${f.version} · ${f.mb} MB`;
      } else {
        b.title = T.sinPaquete;
      }
    });
    if (publicadas.length) {
      const v = publicadas[0];
      const fecha = new Date(v.published_at).toLocaleDateString(T.locale, { day: "numeric", month: "long", year: "numeric" });
      document.getElementById("version-actual").innerHTML =
        T.version(v.tag_name, fecha) +
        `<a href="https://github.com/jaso69/obd2/releases">GitHub Releases</a>.`;
    }
  })
  .catch(() => {});
