from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import deque

from clasificador import analizar_frame


app = Flask(__name__)
CORS(app)

historial = deque(maxlen=5)


@app.route("/api/predict", methods=["POST"])


def predict():

    archivo = request.files.get("frame")

    if archivo is None:
        return jsonify({
            "error": "No se recibió frame"
        }), 400

    clase, confianza = analizar_frame(archivo)

    if clase is None:
        historial.clear()

        return jsonify({
            "confirmada": False,
            "danza": None
        })

    historial.append(clase)

    confirmada = (
        len(historial) == 5
        and len(set(historial)) == 1
    )

    danza = clase if confirmada else None

    return jsonify({
        "clase": clase,
        "confianza": confianza,
        "confirmada": confirmada,
        "danza": danza
    })

@app.route("/api/reset", methods=["POST"])
def reset():
    historial.clear()

    return jsonify({
        "ok": True
    })

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000
    )
