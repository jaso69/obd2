// OBD2Desk · páginas de códigos de avería VAG: menú móvil, idioma y buscador

const EN = document.documentElement.lang === "en";
const T = EN
  ? { nada: "No code found. Try the 5-digit code, the P code or another word.", mas: (n) => `and ${n} more: type more to narrow it down.`, cargando: "Loading…", fallo: "Could not load the search index; browse the lists below." }
  : { nada: "No hay ningún código así. Prueba con las 5 cifras, el código P u otra palabra.", mas: (n) => `y ${n} más: escribe algo más para afinar.`, cargando: "Cargando…", fallo: "No se ha podido cargar el buscador; recorre las listas de abajo." };

// Selector de idioma: recuerda la elección (idioma.js la respeta en la portada)
document.querySelectorAll("[data-idioma]").forEach((a) => {
  a.addEventListener("click", () => {
    try { localStorage.setItem("idioma", a.dataset.idioma); } catch (e) { /* sin almacenamiento */ }
  });
});

// Menú en móvil
const menuBoton = document.querySelector(".menu-boton");
const menu = document.getElementById("menu");
menuBoton.addEventListener("click", () => {
  const abierto = menu.classList.toggle("abierto");
  menuBoton.setAttribute("aria-expanded", abierto);
});

// Buscador: carga el índice de todos los códigos la primera vez que se escribe
const entrada = document.getElementById("buscar");
const salida = document.getElementById("resultados");
const MAX = 30;
let indice = null;
let cargando = null;

const normal = (s) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

function cargar() {
  if (!cargando) {
    cargando = fetch(entrada.dataset.indice)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((datos) => {
        const base = new URL(entrada.dataset.indice, location.href);
        indice = datos.map((d) => ({ vag: d[0], p: d[1], desc: d[2], url: new URL(d[3], base).href, texto: normal(d[2]) }));
      })
      .catch(() => { salida.textContent = T.fallo; });
  }
  return cargando;
}

function buscar(q) {
  q = normal(q.trim());
  if (!q) return [];
  const cifras = q.replace(/\s/g, "");
  if (/^\d+$/.test(cifras) && indice.some((d) => d.vag)) {
    // 5 cifras o el principio; se aceptan sin ceros a la izquierda (532 = 00532)
    return indice.filter((d) => d.vag.startsWith(cifras) || d.vag.replace(/^0+/, "").startsWith(cifras.replace(/^0+/, "")));
  }
  if (/^\d+$/.test(cifras)) return indice.filter((d) => normal(d.p).slice(1).startsWith(cifras));   // «0420» = P0420
  // código OBD (P0420, U0100, c0035…): por el principio
  if (/^[pbcu][0-9a-f]*\d[0-9a-f]*$/.test(cifras)) return indice.filter((d) => normal(d.p).startsWith(cifras));
  const palabras = q.split(/\s+/);
  return indice.filter((d) => palabras.every((w) => d.texto.includes(w)));
}

function mostrar() {
  if (!indice) { salida.textContent = T.cargando; cargar().then(mostrar); return; }
  salida.replaceChildren();
  if (!entrada.value.trim()) return;
  const encontrados = buscar(entrada.value);
  if (!encontrados.length) { salida.textContent = T.nada; return; }
  const lista = document.createElement("ul");
  encontrados.slice(0, MAX).forEach((d) => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = d.url;
    const cod = document.createElement("strong");
    cod.textContent = [d.vag, d.p].filter(Boolean).join(" · ");
    a.append(cod, " ", d.desc);
    li.append(a);
    lista.append(li);
  });
  salida.append(lista);
  if (encontrados.length > MAX) {
    const p = document.createElement("p");
    p.className = "pequeno";
    p.textContent = T.mas(encontrados.length - MAX);
    salida.append(p);
  }
}

if (entrada) {
  entrada.addEventListener("focus", cargar, { once: true });
  entrada.addEventListener("input", mostrar);
}

// Al llegar a un código (#17978), resaltarlo
function resaltar() {
  document.querySelectorAll(".tabla-codigos tr.resaltado").forEach((tr) => tr.classList.remove("resaltado"));
  const id = decodeURIComponent(location.hash.slice(1));
  const el = id && document.getElementById(id);
  if (el) (el.closest("tr") || el).classList.add("resaltado");
}
window.addEventListener("hashchange", resaltar);
resaltar();
