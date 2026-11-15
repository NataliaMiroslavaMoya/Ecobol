const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("msg");
const chips = document.getElementById("chips");
const SEL = { categoria: document.getElementById("f-tipo"), departamento: document.getElementById("f-ambito"), subtipo: document.getElementById("f-area") };
const CLAVE = { categoria: "c", departamento: "d", subtipo: "s" };           // columnas de "filas" que manda /api/opciones
const ETQ = { categoria: "Todas", departamento: "Todos", subtipo: "Todos" };
const SUGERENCIAS = ["¿Qué puedo preguntar?", "¿Qué animales existen en el Parque Madidi?", "¿Cuáles son las áreas protegidas de Bolivia?", "¿Qué especies están en peligro de extinción?", "¿Dónde vive el oso andino?", "¿Qué es una especie endémica?"];
const ICONOS = { "Áreas protegidas": "🌳", "Fauna": "🐆", "Flora": "🌿", "Ecosistemas": "🏞️", "Recursos hídricos": "💧", "Problemas ambientales": "🔥", "Conservación": "🤝" };
let FILAS = [];

/* ---------- utilidades ---------- */
function el(tag, cls, texto) { const e = document.createElement(tag); if (cls) e.className = cls; if (texto !== undefined) e.textContent = texto; return e; }
function escribir(nodo, texto) {            // texto plano + enlaces clicables (sin innerHTML)
  nodo.textContent = "";
  texto.split(/(https?:\/\/\S+)/g).forEach(parte => {
    if (/^https?:\/\//.test(parte)) { const a = el("a", "", parte); a.href = parte; a.target = "_blank"; a.rel = "noopener"; nodo.appendChild(a); }
    else nodo.appendChild(document.createTextNode(parte));
  });
}
function abajo() { chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" }); }
function slug(t) { return (t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, "-").toLowerCase(); }

/* ---------- mensajes ---------- */
function mensaje(rol, texto) {
  const m = el("div", "msg " + rol), col = el("div", "col"), b = el("div", "bub");
  if (rol === "bot") m.appendChild(el("div", "avatar", "🌿"));
  escribir(b, texto); col.appendChild(b); m.appendChild(col); chat.appendChild(m); abajo();
  return { m, col, b };
}

/* Respuestas normales (no scraping): lista limpia dentro del chat */
function lista(items) {
  const ul = el("ul", "lista");
  items.forEach(x => {
    const li = el("li", "cat-" + slug(x.categoria));
    li.appendChild(el("span", "ico", ICONOS[x.categoria] || "🌎"));
    const t = el("div", "li-txt");
    t.appendChild(el("strong", "", x.nombre));
    t.appendChild(el("small", "", [x.subtipo, x.departamento].filter(Boolean).join(" · ")));
    t.appendChild(el("span", "", x.frase));
    if (/^https?:\/\//.test(x.enlace || "")) { const a = el("a", "", "🔗 Ver fuente"); a.href = x.enlace; a.target = "_blank"; a.rel = "noopener"; t.appendChild(a); }
    li.appendChild(t); ul.appendChild(li);
  });
  return ul;
}

/* Tarjeta: SOLO para información obtenida con web scraping */
function tarjetaWeb(c) {
  const k = el("article", "card cat-" + slug(c.categoria));
  const ban = el("div", "card-ban");
  ban.appendChild(el("span", "ico", ICONOS[c.categoria] || "🌎"));
  ban.appendChild(el("span", "tag", c.categoria));
  ban.appendChild(el("span", "badge", "🌐 Web scraping"));
  k.appendChild(ban);
  const cu = el("div", "card-body");
  cu.appendChild(el("h4", "", c.nombre));
  cu.appendChild(el("div", "meta", [c.subtipo, c.departamento].filter(Boolean).join(" · ")));
  cu.appendChild(el("blockquote", "web", c.web));
  const pie = el("div", "card-foot");
  const info = el("div", "fuente");
  info.appendChild(el("strong", "", "Fuente: " + (c.fuente || "página web")));
  if (c.actualizado) info.appendChild(el("span", "", "Actualizado: " + c.actualizado));
  pie.appendChild(info);
  const btns = el("div", "btns");
  if (/^https?:\/\//.test(c.oficial || "")) { const o = el("a", "btn-fuente oficial", "🏛️ Fuente oficial ↗"); o.href = c.oficial; o.target = "_blank"; o.rel = "noopener"; btns.appendChild(o); }
  if (/^https?:\/\//.test(c.enlace || "")) { const a = el("a", "btn-fuente", "Ver página ↗"); a.href = c.enlace; a.target = "_blank"; a.rel = "noopener"; btns.appendChild(a); }
  pie.appendChild(btns);
  cu.appendChild(pie); k.appendChild(cu);
  return k;
}

/* ---------- ¿Te fue útil? ---------- */
function valorar(pregunta, respuesta) {
  const d = el("div", "valora"); d.appendChild(el("span", "", "¿Te fue útil?"));
  [["👍", "util"], ["👎", "no_util"]].forEach(([ico, voto]) => {
    const b = el("button", "", ico); b.type = "button";
    b.onclick = () => {
      fetch("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ voto, pregunta, respuesta }) }).catch(() => {});
      d.textContent = voto === "util" ? "¡Gracias! 🌿" : "Gracias, lo revisaremos para mejorar.";
    };
    d.appendChild(b);
  });
  return d;
}

/* ---------- filtros que sí filtran ---------- */
function valores() { return { categoria: SEL.categoria.value, departamento: SEL.departamento.value, subtipo: SEL.subtipo.value }; }
function coincide(f, v, ignorar) {
  return Object.keys(CLAVE).every(k => {
    if (k === ignorar || !v[k]) return true;
    return k === "departamento" ? (f.d === v.departamento || f.d === "Nacional") : f[CLAVE[k]] === v[k];
  });
}
function refrescarFiltros() {                // cada lista solo ofrece opciones que existen con los otros filtros
  const v = valores();
  Object.keys(SEL).forEach(k => {
    const s = SEL[k], actual = v[k];
    const ops = [...new Set(FILAS.filter(f => coincide(f, v, k)).map(f => f[CLAVE[k]]))].filter(o => k !== "departamento" || o !== "Nacional").sort((a, b) => a.localeCompare(b, "es"));
    s.textContent = ""; s.appendChild(new Option(ETQ[k], ""));
    ops.forEach(o => s.appendChild(new Option(o, o)));
    s.value = ops.includes(actual) ? actual : "";
  });
  const v2 = valores(), hay = Object.values(v2).some(Boolean);
  document.getElementById("limpiar").hidden = !hay;
  document.getElementById("contador").textContent = hay ? "Filtros activos ✔" : "";
  Object.values(SEL).forEach(s => s.classList.toggle("activo", !!s.value));
}
async function aplicarFiltros() {
  refrescarFiltros();
  const hay = Object.values(valores()).some(Boolean);
  ocultarSugerencias();
  if (!hay) { mensaje("bot", "Filtros quitados. Pregúntame lo que quieras sobre la naturaleza de Bolivia 🌿"); return; }
  await consultar("");
}
document.getElementById("limpiar").onclick = () => { Object.values(SEL).forEach(s => s.value = ""); aplicarFiltros(); };
Object.values(SEL).forEach(s => s.addEventListener("change", aplicarFiltros));

/* ---------- envío ---------- */
function ocultarSugerencias() { chips.hidden = true; }

async function consultar(texto) {
  const espera = mensaje("bot", "Escribiendo...");
  espera.b.classList.add("typing");
  const body = { mensaje: texto, enlaces: document.getElementById("f-enlaces").checked, ...valores() };
  try {
    const r = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("Error del servidor: " + r.status);
    const d = await r.json();
    espera.b.classList.remove("typing");
    escribir(espera.b, d.respuesta || "No recibí una respuesta del servidor.");
    if (Array.isArray(d.lista) && d.lista.length) espera.col.appendChild(lista(d.lista));
    if (Array.isArray(d.tarjetas) && d.tarjetas.length) { const g = el("div", "cards-grid"); d.tarjetas.forEach(c => g.appendChild(tarjetaWeb(c))); espera.col.appendChild(g); }
  } catch (e) {
    espera.b.classList.remove("typing");
    escribir(espera.b, "No pude conectar con el servidor. Intenta de nuevo en unos segundos.");
    console.error("Error en EcoBol:", e);
  }
  if (texto && !espera.b.classList.contains("typing")) espera.col.appendChild(valorar(texto, espera.b.textContent));
  abajo();
}

async function enviar(texto) {
  texto = texto.trim();
  if (!texto) return;
  ocultarSugerencias();                       // las sugerencias solo se ven antes de la primera pregunta
  mensaje("user", texto);
  input.value = "";
  await consultar(texto);
}

/* ---------- inicio ---------- */
async function iniciar() {
  mensaje("bot", "¡Hola! Soy EcoBol 🌿 Pregúntame por áreas protegidas, fauna, flora, ecosistemas, ríos y conservación de Bolivia. Escribe «ayuda» para ver ejemplos.");
  SUGERENCIAS.forEach(s => { const c = el("button", "chip", s); c.type = "button"; c.onclick = () => enviar(s === "¿Qué puedo preguntar?" ? "ayuda" : s); chips.appendChild(c); });
  try {
    const o = await (await fetch("/api/opciones")).json();
    FILAS = o.filas || [];
    refrescarFiltros();
  } catch (e) { /* filtros opcionales */ }
}
form.addEventListener("submit", e => { e.preventDefault(); enviar(input.value); });
iniciar();