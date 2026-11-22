
from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import deque
from io import BytesIO

from clasificador import analizar_frame
from filtro_pose import detectar_pose

app = Flask(__name__)
CORS(app)

historial = deque(maxlen=5)


@app.route("/api/predict", methods=["POST"])
def predict():

    archivo = request.files.get("frame")

    if archivo is None:
        return jsonify({"error": "No se recibió frame"}), 400

    # Leer el frame una sola vez
    imagen = archivo.read()

    # ETAPA 1: CNN - ¿Existe una pose de danza?
    hay_pose = detectar_pose(BytesIO(imagen))

    if not hay_pose:
        historial.clear()

        return jsonify({
            "estado": "no_pose",
            "clase": None,
            "confianza": 0,
            "confirmada": False,
            "danza": None
        })

    # ETAPA 2: YOLO Pose + MLP - ¿Qué danza es?
    clase, confianza = analizar_frame(BytesIO(imagen))

    if clase is None:
        historial.clear()

        return jsonify({
            "estado": "sin_clasificacion",
            "clase": None,
            "confianza": round(confianza, 2),
            "confirmada": False,
            "danza": None
        })

    # ETAPA 3: Cinco clasificaciones consecutivas
    historial.append(clase)

    confirmada = (
        len(historial) == 5
        and len(set(historial)) == 1
    )

    return jsonify({
        "estado": "confirmada" if confirmada else "analizando",
        "clase": clase,
        "confianza": round(confianza, 2),
        "confirmada": confirmada,
        "danza": clase if confirmada else None
    })


@app.route("/api/reset", methods=["POST"])
def reset():
    historial.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000
    )
