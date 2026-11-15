"""Servidor Flask: sirve el frontend, la API del chatbot y ejecuta el scraping en R."""
import os, json, subprocess, threading
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import chatbot

ROOT = Path(__file__).resolve().parent.parent
FEEDBACK = Path(__file__).resolve().parent / "data" / "feedback.jsonl"
_lock = threading.Lock()
app = Flask(__name__, static_folder=str(ROOT / "frontend"), static_url_path="")
CORS(app)


@app.get("/")
def inicio():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/opciones")
def opciones():
    return jsonify(chatbot.opciones())


@app.post("/api/chat")
def chat():
    d = request.get_json(silent=True) or {}
    return jsonify(chatbot.responder(
        str(d.get("mensaje", ""))[:300],
        str(d.get("categoria", "")), str(d.get("departamento", "")), str(d.get("subtipo", "")),
        bool(d.get("enlaces", False))))


@app.get("/salud")
def salud():
    return jsonify({"ok": True})


@app.post("/api/feedback")
def feedback():
    """Guarda si la respuesta fue útil. No se guardan datos personales (ni IP)."""
    d = request.get_json(silent=True) or {}
    if d.get("voto") not in ("util", "no_util"):
        return jsonify({"ok": False}), 400
    reg = {"fecha": datetime.now().isoformat(timespec="seconds"), "voto": d["voto"],
           "pregunta": str(d.get("pregunta", ""))[:300], "respuesta": str(d.get("respuesta", ""))[:300]}
    with _lock, open(FEEDBACK, "a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    return jsonify({"ok": True})


@app.get("/api/feedback/resumen")
def feedback_resumen():
    """Cuántas valoraciones hay. Protegido con ADMIN_TOKEN."""
    token = os.environ.get("ADMIN_TOKEN")
    if not token or request.headers.get("X-Token") != token:
        return jsonify({"ok": False, "error": "No autorizado"}), 403
    regs = [json.loads(l) for l in FEEDBACK.read_text(encoding="utf-8").splitlines() if l.strip()] if FEEDBACK.exists() else []
    util = sum(r["voto"] == "util" for r in regs)
    return jsonify({"total": len(regs), "utiles": util, "no_utiles": len(regs) - util,
                    "no_utiles_preguntas": [r["pregunta"] for r in regs if r["voto"] == "no_util"][-20:]})


@app.post("/api/actualizar")
def actualizar():
    """Ejecuta scraping.R. Protegido con la variable de entorno ADMIN_TOKEN."""
    token = os.environ.get("ADMIN_TOKEN")
    if not token or request.headers.get("X-Token") != token:
        return jsonify({"ok": False, "error": "No autorizado"}), 403
    try:
        p = subprocess.run(["Rscript", str(ROOT / "scraping" / "scraping.R")], capture_output=True, text=True, timeout=600)
        return jsonify({"ok": p.returncode == 0, "log": (p.stdout + p.stderr)[-1500:]})
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "Rscript no está instalado en el servidor"}), 500


if __name__ == "__main__":
    # debug solo si lo pides: set FLASK_DEBUG=1
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")