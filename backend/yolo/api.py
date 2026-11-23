"""API local y frontend servidos desde el mismo origen."""
from pathlib import Path
from threading import Lock
from time import monotonic
from uuid import UUID, uuid4

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

if __package__:
    from .clasificador import analizar_frame
else:
    from clasificador import analizar_frame

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
app = Flask(__name__, static_folder=str(FRONTEND), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
CORS(app, resources={r"/api/*": {"origins": [
    r"http://localhost(:\d+)?", r"http://127\.0\.0\.1(:\d+)?"
]}})
CONFIRMACIONES = 3
SESIONES = {}
SESIONES_LOCK = Lock()
TTL = 120


@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.get("/api/health")
def health():
    return jsonify(ok=True, confirmaciones=CONFIRMACIONES)


@app.post("/api/reset")
def reset():
    ahora = monotonic()
    with SESIONES_LOCK:
        for sid in list(SESIONES):
            if ahora - SESIONES[sid]["tiempo"] > TTL:
                del SESIONES[sid]
        if len(SESIONES) >= 100:
            return jsonify(error="Demasiadas sesiones activas"), 503
        sid = str(uuid4())
        SESIONES[sid] = dict(tiempo=ahora, clase=None, consecutivas=0, lock=Lock())
    return jsonify(ok=True, sesion=sid)


@app.post("/api/predict")
def predict():
    sid = request.form.get("sesion", "")
    try:
        UUID(sid)
    except ValueError:
        return jsonify(error="Inicia una sesión con /api/reset"), 400
    with SESIONES_LOCK:
        sesion = SESIONES.get(sid)
        if sesion is None or monotonic() - sesion["tiempo"] > TTL:
            return jsonify(error="Sesión vencida; reinicia la cámara"), 409
    archivo = request.files.get("frame")
    if archivo is None:
        with sesion["lock"]:
            sesion.update(clase=None, consecutivas=0)
        return jsonify(error="No se recibió frame"), 400
    with sesion["lock"]:
        if monotonic() - sesion["tiempo"] > 10:
            sesion.update(clase=None, consecutivas=0)
        try:
            resultado = analizar_frame(archivo)
        except ValueError as error:
            sesion.update(clase=None, consecutivas=0)
            return jsonify(error=str(error)), 400
        except Exception:
            sesion.update(clase=None, consecutivas=0)
            app.logger.exception("Falló la inferencia")
            return jsonify(error="No se pudo analizar la imagen; revisa el servidor"), 500
        clase = resultado["clase"]
        if clase is None:
            sesion.update(clase=None, consecutivas=0)
        else:
            cantidad = sesion["consecutivas"] + 1 if clase == sesion["clase"] else 1
            sesion.update(clase=clase, consecutivas=min(cantidad, CONFIRMACIONES))
        sesion["tiempo"] = monotonic()
        confirmada = sesion["consecutivas"] >= CONFIRMACIONES
        resultado.update(confirmada=confirmada, danza=clase if confirmada else None,
                         consecutivas=sesion["consecutivas"], requeridas=CONFIRMACIONES)
        if confirmada:
            resultado["estado"] = "confirmada"
        return jsonify(resultado)


@app.errorhandler(HTTPException)
def error_http(error):
    return jsonify(error=error.description), error.code


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
