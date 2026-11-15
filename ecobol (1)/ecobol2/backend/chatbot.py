"""Lógica del chatbot EcoBol (biodiversidad de Bolivia): datos base + información scrapeada por R."""
import csv, json, re, unicodedata
from urllib.parse import urlparse
from pathlib import Path

DATA = Path(__file__).parent / "data"
STOP = {"de", "la", "el", "en", "para", "que", "y", "un", "una", "quiero", "busco", "hay", "con", "me", "mi", "por", "los",
        "las", "del", "bolivia", "boliviana", "boliviano", "nacional", "nacionales", "se", "puedo", "dame", "sobre", "algun", "alguna", "donde", "como", "cual", "cuales", "dime", "saber", "es", "a"}
CATS = [("Fauna", ["animal", "fauna", "mamifero", "aves", "reptil", "anfibio", "pez ", "peces"]),
        ("Flora", ["planta", "flor", "flora", "arbol", "flores", "vegetacion"]),
        ("Áreas protegidas", ["area protegida", "areas protegidas", "parque", "reserva", "sernap"]),
        ("Ecosistemas", ["ecosistema", "bosque", "selva", "amazon", "yungas", "chaco", "altiplano", "humedal"]),
        ("Recursos hídricos", ["rio", "rios", "lago", "laguna", "salar", "cuenca"]),
        ("Problemas ambientales", ["deforestacion", "incendio", "contaminacion", "cambio climatico"]),
        ("Conservación", ["conservacion", "proyecto", "programa", "ong"])]
SUBS = [("Parque nacional", ["parque nacional", "parques nacionales"]), ("Reserva", ["reserva", "reservas"]), ("ANMI", ["anmi", "manejo integrado"]),
        ("Mamífero", ["mamifero"]), ("Ave", ["aves", "ave "]), ("Anfibio", ["anfibio"]), ("Árbol", ["arbol"]), ("Río", ["rios", "rio "]), ("Lago", ["lago"]), ("Institución", ["institucion", "ong"])]
DEPTOS = [("La Paz", ["la paz", "el alto", "coroico"]), ("Santa Cruz", ["santa cruz", "samaipata"]), ("Cochabamba", ["cochabamba"]), ("Oruro", ["oruro"]),
          ("Potosí", ["potosi", "uyuni"]), ("Chuquisaca", ["chuquisaca", "sucre"]), ("Tarija", ["tarija"]), ("Beni", ["beni", "trinidad", "rurrenabaque"]), ("Pando", ["pando", "cobija"])]
FAQ = [
    (r"que es (la )?biodiversidad|megadiverso|pais diverso", "Biodiversidad es la variedad de especies, ecosistemas y genes. Bolivia es considerado uno de los países con mayor diversidad biológica del mundo, por sus ecosistemas desde los Andes hasta la Amazonía y el Chaco."),
    (r"que es (una )?(especie )?endemic", "Una especie endémica vive de forma natural solo en una región determinada. Por ejemplo, la paraba barba azul es endémica de las sabanas del Beni."),
    (r"ramsar", "Un sitio Ramsar es un humedal reconocido internacionalmente por el Convenio de Ramsar para su conservación y uso sostenible. Bolivia tiene varios, como el Pantanal boliviano."),
    (r"uicn|categorias de (amenaza|conservacion)|que significa (vulnerable|peligro critico)", "La UICN usa estas categorías, de menor a mayor riesgo: Preocupación menor, Casi amenazado, Vulnerable, En peligro y En peligro crítico (y luego Extinto). Son internacionales; Bolivia tiene además sus categorías en el Libro Rojo de Vertebrados."),
    (r"como (puedo )?(ayudar|cuidar|proteger)|que puedo hacer.*(naturaleza|ambiente)", "Puedes ayudar así: no compres fauna ni plantas silvestres, no hagas fuego en zonas de riesgo, no dejes basura, respeta las normas de las áreas protegidas y apoya a organizaciones de conservación."),
    (r"que es (un |el )?anmi|manejo integrado", "ANMI significa Área Natural de Manejo Integrado: combina la conservación de la naturaleza con el aprovechamiento sostenible por las comunidades locales."),
    (r"que es (un )?parque nacional", "Un parque nacional es un área protegida que resguarda ecosistemas y paisajes de valor científico, cultural y natural, con manejo estricto. Ejemplos: Madidi, Sajama y Amboró."),
    (r"chaqueo|que es (una )?quema", "El chaqueo es la quema de vegetación para habilitar terrenos agrícolas. Si se sale de control puede provocar incendios forestales."),
    (r"flor nacional|flores nacionales", "Bolivia tiene dos flores nacionales: la kantuta (Cantua buxifolia) y el patujú (Heliconia rostrata)."),
    (r"\b(gracias|chau|adios)\b", "¡De nada! Si quieres, pregúntame por otra especie, área protegida o ecosistema de Bolivia. 🌿"),
    (r"diferencia.*(parque|reserva)|parque.*\b(vs|o|y)\b.*reserva", "Un parque nacional protege ecosistemas y paisajes de valor científico, con manejo más estricto. Una reserva nacional protege también especies y recursos y puede permitir algunos usos sostenibles. Un ANMI (Área Natural de Manejo Integrado) combina conservación con el aprovechamiento sostenible por comunidades. Confirma las categorías en el SERNAP."),
    (r"cuantas areas protegidas|cuantos parques", "El SERNAP administra el Sistema Nacional de Áreas Protegidas (cerca de 22 áreas nacionales) y existen además áreas departamentales y municipales. Confirma el número actual en sernap.gob.bo."),
    (r"mejor epoca|cuando ir|cuando viajar|temporada|\bclima\b", "En la Amazonía y los llanos, la época seca (mayo a octubre) facilita el acceso; de noviembre a marzo llueve más y algunos caminos se complican. Confirma con la administración del área protegida antes de viajar."),
    (r"cuantos departamentos|departamentos de bolivia", "Bolivia tiene 9 departamentos: La Paz, Santa Cruz, Cochabamba, Oruro, Potosí, Chuquisaca, Tarija, Beni y Pando."),
]
HF = DATA / "hechos.json"
_cache = {"mtime": None, "filas": []}


def norm(t):
    t = unicodedata.normalize("NFKD", t.lower())
    return re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in t if not unicodedata.combining(c))).strip()


def datos():
    p = DATA / "scraped.json"
    mt = (p.stat().st_mtime if p.exists() else 0) + (HF.stat().st_mtime if HF.exists() else 0)
    if _cache["mtime"] == mt and _cache["filas"]:
        return _cache["filas"]
    with open(DATA / "base.csv", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    web = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    hech = json.loads(HF.read_text(encoding="utf-8")) if HF.exists() else {}
    for r in filas:
        r["hechos"] = hech.get(r["nombre"], {})
        w = web.get(r["id"], {})
        par = w.get("parrafos") or []
        par = [par] if isinstance(par, str) else par
        r["web_texto"] = " ".join(par[:4])[:1600]
        r["web_actualizado"] = w.get("actualizado", "") or ""
        r["web_titulo"] = w.get("titulo", "") or ""
        r["oficial"] = (r.get("fuente_oficial") or "").strip()
        r["nombre_n"] = norm(r["nombre"])
        r["busca"] = norm(" ".join([r["nombre"], r["categoria"], r["subtipo"], r["departamento"], r["etiquetas"], r["descripcion"], r["web_texto"][:300]]))
    _cache.update(mtime=mt, filas=filas)
    return filas


def opciones():
    f = datos()
    out = {k: sorted({r[c] for r in f}) for k, c in (("categorias", "categoria"), ("departamentos", "departamento"), ("subtipos", "subtipo"))}
    out["filas"] = [{"c": c, "d": d, "s": s} for c, d, s in sorted({(r["categoria"], r["departamento"], r["subtipo"]) for r in f})]
    return out


def _detectar(t, lista):
    for k, kws in lista:
        if any(w in t for w in kws):
            return k
    return ""


def _cumple(r, c, d, s):
    return (not c or r["categoria"] == c) and (not d or r["departamento"] in (d, "Nacional")) and (not s or r["subtipo"] == s)


def buscar(texto, categoria="", departamento="", subtipo="", limite=5):
    t = norm(texto)
    sub_explicito = bool(subtipo)
    categoria = categoria or _detectar(t, CATS)
    departamento = departamento or _detectar(t, DEPTOS)
    subtipo = subtipo or _detectar(t, SUBS)
    base = datos()
    res = []
    for sub in ((subtipo,) if sub_explicito else (subtipo, "")):   # si el subtipo se detectó solo, se relaja
        res = [r for r in base if _cumple(r, categoria, departamento, sub)]
        if res:
            break
    palabras = [p for p in t.split() if p not in STOP and len(p) > 3]
    punt = []
    for r in res:
        s = sum((3 if q[:max(4, len(q) - 2)] in r["nombre_n"] else 0) + (1 if q[:max(4, len(q) - 2)] in r["busca"] else 0) for q in palabras)
        punt.append((s, r))
    if any(s > 0 for s, _ in punt):
        punt = [x for x in punt if x[0] > 0]
    elif palabras and not (categoria or departamento or subtipo):
        return []                                    # texto sin relación con los registros: no inventar resultados
    punt.sort(key=lambda x: -x[0])
    return [r for _, r in punt[:limite]]


def _frase(t):
    return re.split(r"(?<=\.)\s", t)[0]


AYUDA = """Esto puedo responderte (puedes preguntar corto o con detalle):

🌳 Áreas protegidas: «Parque Madidi», «cuáles son las áreas protegidas de Bolivia», «parques nacionales en Santa Cruz», «dónde se encuentra el Parque Sajama», «cuándo se creó Sajama», «qué superficie tiene Kaa-Iya», «cómo visitar Torotoro»
🐆 Fauna: «oso andino», «qué animales existen en el Parque Madidi», «dónde vive la paraba barba azul», «qué come el jaguar», «por qué está amenazado el oso andino», «dato curioso del cóndor»
🌿 Flora: «qué es la queñua», «flor nacional», «castaña amazónica», «plantas del altiplano»
🏞️ Ecosistemas y agua: «Yungas», «dónde puedo encontrar bosques amazónicos», «lago Titicaca», «ríos de Bolivia»
⚠️ Amenazas: «qué especies están en peligro de extinción», «incendios forestales», «glaciar Chacaltaya»
🤝 Conservación: «SERNAP», «instituciones de conservación», «cómo puedo ayudar»
ℹ️ Conceptos: «qué es la biodiversidad», «qué es una especie endémica», «qué es un sitio Ramsar», «categorías de la UICN», «diferencia entre parque y reserva»
🎛️ Filtros: elige categoría, departamento o subtipo a la izquierda y verás solo lo que coincide.
🔗 Si quieres el enlace, escribe «dame el enlace de ...» o activa «Mostrar enlaces». Si preguntas «dónde se encuentra...», siempre te lo doy."""

TEMAS = [("creacion", r"cuando se (creo|declaro|fundo)|creacion|creado"),
         ("superficie", r"superficie|hectareas|extension|que tan grande|tamano"),
         ("alimentacion", r"\b(come|comen|alimenta|alimentan|alimentacion|dieta)\b"),
         ("amenazas", r"amenazas|que (lo|la) amenaza|por que (esta|estan) (en peligro|amenazad)|causas"),
         ("estado", r"peligro|amenaza|extincion|vulnerable|categoria|estado de conservacion"),
         ("visitar", r"visitar|visita|turismo|como llegar|se puede ir|ir a"),
         ("curiosidad", r"curiosidad|dato curioso|sabias|interesante"),
         ("donde", r"donde|ubicacion|ubicado|queda|\bse encuentra\b"),
         ("fauna", r"animales|fauna|especies|viven|habitan|aves"),
         ("flora", r"plantas|flora|vegetacion|arboles"),
         ("fecha", r"cuando|fecha|que dia|dia fue|se declaro"),
         ("detalle", r"que paso|como fue|detalle|informacion|cuentame|explica|caracteristicas|importancia")]


GEN = {"parque", "nacional", "reserva", "fauna", "flora", "andina", "lago", "amazonica", "silvestre", "vida", "biosfera", "gran"}


def _entidad(t):
    palabras = [p for p in t.split() if p not in STOP and len(p) > 2]
    sc = sorted(((sum(3 for q in palabras if any(w == q or (len(q) >= 5 and w.startswith(q[:max(4, len(q) - 2)])) for w in r["nombre_n"].split())), r) for r in datos()), key=lambda x: -x[0])
    if not sc or sc[0][0] < 3:
        return None, []
    empate = [r for s, r in sc if s == sc[0][0]]
    if len(empate) == 1:
        return empate[0], []
    return None, (empate[:3] if len(empate) <= 3 and sc[0][0] >= 6 else [])


def _web(r, t, n=3):
    """Frases del texto scrapeado de la página, las más relacionadas con la pregunta."""
    sents = [x for x in re.split(r"(?<=[.!?])\s+", r["web_texto"]) if len(x) > 40]
    nt = [w[:5] for w in r["nombre_n"].split() if len(w) > 4 and w not in GEN]
    if nt:
        sents = [x for x in sents if any(k in norm(x) for k in nt)]
    if not sents:
        return ""
    toks = [w for w in t.split() if w not in STOP and len(w) > 3]
    mejor = sorted(range(len(sents)), key=lambda i: (-sum(w[:4] in norm(sents[i]) for w in toks), i))[:n]
    return " ".join(sents[i] for i in sorted(mejor))[:700]


def _tarjeta_web(r, texto):
    """Tarjeta SOLO para información que viene del web scraping (R)."""
    return {"nombre": r["nombre"], "categoria": r["categoria"], "subtipo": r["subtipo"], "departamento": r["departamento"],
            "web": texto, "titulo": r.get("web_titulo", ""), "actualizado": r.get("web_actualizado", ""),
            "fuente": urlparse(r["enlace"]).netloc.replace("www.", ""), "enlace": r["enlace"], "oficial": r["oficial"]}


def _item(x, enlaces):
    d = {"nombre": x["nombre"], "categoria": x["categoria"], "subtipo": x["subtipo"], "departamento": x["departamento"], "frase": _frase(x["descripcion"])}
    if enlaces:
        d["enlace"] = x["oficial"] or x["enlace"]
    return d


def _entidad_resp(r, t, enlaces=False):
    h, n = r["hechos"], r["nombre"]
    tema = next((k for k, pat in TEMAS if re.search(pat, t)), "")

    def simple(txt, link=enlaces):
        return {"respuesta": txt + (f"\n🔗 {r['oficial'] or r['enlace']}" if link else "")}

    if tema == "fecha":
        return simple(h.get("fecha") or h.get("creacion") or f"No tengo una fecha registrada de «{n}».")
    if tema == "donde":
        loc = h.get("donde") or (f"{n} está en {r['departamento']}, Bolivia." if r["departamento"] != "Nacional" else f"«{n}» tiene distribución amplia en Bolivia; no tengo una ubicación más exacta.")
        return simple("📍 " + loc)
    if tema in ("creacion", "superficie", "estado", "fauna", "flora", "alimentacion", "amenazas", "visitar", "curiosidad"):
        if h.get(tema):
            return simple(h[tema])
        w = _web(r, t)
        if w:
            return {"respuesta": f"No tengo ese dato exacto de «{n}» en mis registros, pero esto dice su página web:", "tarjetas": [_tarjeta_web(r, w)]}
        return simple(f"No tengo ese dato registrado de «{n}». Puedes consultarlo en la fuente:", True)
    if tema == "detalle" and h.get("detalle"):
        return simple(h["detalle"])
    w = _web(r, t)
    if w:
        return {"respuesta": f"Esto encontré sobre «{n}» en su página web:", "tarjetas": [_tarjeta_web(r, w)]}
    partes = [f"🌿 {n} ({r['subtipo']} · {r['departamento']})", r["descripcion"]]
    for k, etq in (("creacion", "📅"), ("superficie", "📐"), ("donde", "📍")):
        if h.get(k):
            partes.append(f"{etq} {h[k]}")
    return simple("\n".join(partes))


def responder(texto, categoria="", departamento="", subtipo="", enlaces=False):
    t = norm(texto)
    categoria, departamento, subtipo = (categoria or "").strip(), (departamento or "").strip(), (subtipo or "").strip()
    filt = " · ".join(x for x in (categoria, departamento, subtipo) if x)
    enlaces = bool(enlaces) or bool(re.search(r"enlace|link|pagina|sitio", t))
    if not t:                                         # sin texto: lista según los filtros activos
        if not filt:
            return {"respuesta": "Escribe tu pregunta, por ejemplo: «Parque Madidi» u «oso andino»."}
        res = [r for r in datos() if _cumple(r, categoria, departamento, subtipo)]
        if not res:
            return {"respuesta": f"No hay registros con los filtros «{filt}». Prueba otra combinación."}
        return {"respuesta": f"Filtros activos: {filt}.\nEncontré {len(res)} registro(s):", "lista": [_item(x, enlaces) for x in res[:20]]}
    if re.match(r"^(hola|buenas|buen dia|hey)\b", t) and len(t) < 15:
        return {"respuesta": "¡Hola! 🌿 Soy EcoBol. Pregúntame por áreas protegidas, fauna, flora, ecosistemas, ríos y conservación de Bolivia. Escribe «ayuda» para ver ejemplos."}
    if re.search(r"\bayuda\b|que puedes|que preguntas|que me puedes|como funciona", t):
        return {"respuesta": AYUDA}
    for pat, resp in FAQ:
        if re.search(pat, t):
            return {"respuesta": resp}
    r, dudas = _entidad(t)
    if r:
        if not _cumple(r, categoria, departamento, subtipo):
            return {"respuesta": f"«{r['nombre']}» no coincide con los filtros activos ({filt}). Cambia o limpia los filtros para ver su información."}
        return _entidad_resp(r, t, enlaces)
    dudas = [d for d in dudas if _cumple(d, categoria, departamento, subtipo)]
    if dudas:
        return {"respuesta": "¿Te refieres a...?\n" + "\n".join(f"• {d['nombre']}" for d in dudas) + "\nEscríbeme el nombre completo."}
    toks = [w for w in t.split() if w not in STOP]
    res = buscar(texto, categoria, departamento, subtipo, 3 if len(toks) <= 2 else 8)
    if not res:
        extra = f" con los filtros «{filt}»" if filt else ""
        return {"respuesta": f"No encontré información sobre eso{extra}. Prueba con otro nombre de especie, área protegida o departamento, o escribe «ayuda»."}
    dep = departamento or _detectar(t, DEPTOS)
    nota = ("\n\nℹ️ Los registros «Nacional» tienen distribución general en Bolivia; no confirman presencia en una localidad específica de " + dep + ".") if dep and any(x["departamento"] == "Nacional" for x in res) else ""
    cab = f"Esto encontré ({len(res)})" + (f" con los filtros {filt}" if filt else "") + ":"
    return {"respuesta": cab + nota, "lista": [_item(x, enlaces) for x in res]}