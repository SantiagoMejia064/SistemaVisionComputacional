"""Contrato de integración y smoke tests con los pesos locales."""
from io import BytesIO
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import cv2
import numpy as np
import torch
from PIL import Image
from backend.yolo import api, clasificador
from backend.yolo.filtro_pose import evaluar_pose


class IntegracionTest(unittest.TestCase):
    def setUp(self):
        self.cliente = api.app.test_client()
        with api.SESIONES_LOCK:
            api.SESIONES.clear()
        self.sesion = self.cliente.post("/api/reset").json["sesion"]

    def enviar(self, sesion=None, imagen=b"imagen"):
        return self.cliente.post("/api/predict", data={
            "sesion": sesion or self.sesion,
            "frame": (BytesIO(imagen), "frame.jpg"),
        })

    def test_modelos_reales_sin_persona(self):
        ok, imagen = cv2.imencode(".jpg", np.zeros((480, 640, 3), np.uint8))
        self.assertTrue(ok)
        respuesta = self.enviar(imagen=imagen.tobytes())
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json["estado"], "sin_persona")
        self.assertFalse(respuesta.json["confirmada"])
        probabilidad = evaluar_pose(Image.new("RGB", (200, 400)))
        self.assertTrue(0 <= probabilidad <= 1)

    def test_imagen_invalida_y_limite(self):
        self.assertEqual(self.enviar(imagen=b"").status_code, 400)
        self.assertEqual(self.enviar(imagen=b"no es imagen").status_code, 400)
        self.assertEqual(self.enviar(imagen=b"x" * (8 * 1024 * 1024)).status_code, 413)
        self.assertEqual(self.cliente.post("/api/predict", data={"sesion":self.sesion}).status_code, 400)
        self.assertEqual(self.enviar(sesion="desconocida").status_code, 400)

    def test_recorte_cnn_y_coordenadas_mlp(self):
        puntos = torch.full((1, 17, 2), 0.4)
        resultado = SimpleNamespace(
            boxes=torch.tensor([[100.0, 50.0, 300.0, 350.0]]),
            keypoints=SimpleNamespace(xyn=puntos, conf=torch.ones((1, 17))),
        )
        resultado.boxes = SimpleNamespace(
            xyxy=resultado.boxes,
        )
        class Cajas:
            xyxy = resultado.boxes.xyxy
            def __len__(self):
                return 1
        resultado.boxes = Cajas()
        logits = torch.full((1, 4), -10.0)
        logits[0, clasificador.CLASES.index("cumbia")] = 10.0
        with patch.object(clasificador, "yolo", return_value=[resultado]), \
             patch.object(clasificador, "evaluar_pose", return_value=0.99) as cnn, \
             patch.object(clasificador, "modelo", return_value=logits) as mlp:
            salida = clasificador.analizar_imagen(np.zeros((400, 500, 3), np.uint8))
            self.assertEqual(salida["clase"], "cumbia")
            self.assertEqual(cnn.call_args.args[0].size, (240, 360))
            torch.testing.assert_close(mlp.call_args.args[0].cpu(), puntos.reshape(1, 34))
            cnn.return_value = 0.1
            self.assertEqual(clasificador.analizar_imagen(np.zeros((400, 500, 3), np.uint8))["estado"], "no_pose")

    def test_confirmacion_aislamiento_y_rechazo(self):
        otra = self.cliente.post("/api/reset").json["sesion"]
        def prediccion(clase):
            return dict(estado="analizando" if clase else "no_pose", clase=clase,
                        confianza=0.95 if clase else 0, personas=1, keypoints=[],
                        puntos_visibles=17, confianza_pose=0.98)
        with patch.object(api, "analizar_frame", side_effect=lambda _: prediccion("cumbia")):
            for n in range(1, 6):
                salida = self.enviar().json
                self.assertEqual(salida["consecutivas"], n)
                self.assertEqual(salida["confirmada"], n == 5)
            self.assertEqual(salida["danza"], "cumbia")
            self.assertEqual(self.enviar(sesion=otra).json["consecutivas"], 1)
        with patch.object(api, "analizar_frame", side_effect=lambda _: prediccion(None)):
            self.assertEqual(self.enviar().json["consecutivas"], 0)
        with patch.object(api, "analizar_frame", side_effect=lambda _: prediccion("joropo")):
            salida = self.enviar().json
            self.assertEqual(salida["consecutivas"], 1)
            self.assertIsNone(salida["danza"])

    def test_cambio_clase_expiracion_y_error(self):
        api.SESIONES[self.sesion].update(clase="cumbia", consecutivas=4)
        with patch.object(api, "analizar_frame", return_value={
            "estado":"analizando", "clase":"bambuco", "confianza":0.96
        }):
            self.assertEqual(self.enviar().json["consecutivas"], 1)
        with patch.object(api, "analizar_frame", side_effect=RuntimeError("fallo controlado")), self.assertLogs(api.app.logger, level="ERROR"):
            self.assertEqual(self.enviar().status_code, 500)
            self.assertEqual(api.SESIONES[self.sesion]["consecutivas"], 0)
        api.SESIONES[self.sesion]["tiempo"] -= api.TTL + 1
        self.assertEqual(self.enviar().status_code, 409)

    def test_frontend_y_health(self):
        with self.cliente.get("/") as respuesta:
            self.assertEqual(respuesta.status_code, 200)
        with self.cliente.get("/js/deteccion.js") as respuesta:
            self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(self.cliente.get("/api/health").json["ok"])


if __name__ == "__main__":
    unittest.main()
