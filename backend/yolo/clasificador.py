"""Pipeline compartido por HTTP y la herramienta de cámara."""
from pathlib import Path
from threading import Lock
import cv2
import numpy as np
from PIL import Image
import torch
from torch import nn
from ultralytics import YOLO

if __package__:
    from .filtro_pose import evaluar_pose
else:
    from filtro_pose import evaluar_pose

ROOT_DIR = Path(__file__).resolve().parents[2]
CLASSIFIER_PATH = ROOT_DIR / "models/yolo/pose_classifier.pth"
YOLO_PATH = ROOT_DIR / "yolo11n-pose.pt"
UMBRAL = 0.85
UMBRAL_CNN = 0.70
UMBRAL_PUNTO = 0.50
INFERENCIA_LOCK = Lock()


class PoseClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(34, 64), nn.ReLU(), nn.Linear(64, 32), nn.ReLU(),
            nn.Dropout(0.20), nn.Linear(32, 4),
        )

    def forward(self, x):
        return self.network(x)


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
for ruta in (CLASSIFIER_PATH, YOLO_PATH):
    if not ruta.is_file():
        raise FileNotFoundError(f"Falta un modelo requerido: {ruta}")
yolo = YOLO(str(YOLO_PATH))
checkpoint = torch.load(CLASSIFIER_PATH, map_location=device, weights_only=True)
CLASES = checkpoint["classes"]
if len(CLASES) != 4 or set(CLASES) != {"bambuco", "cumbia", "currulao", "joropo"}:
    raise ValueError(f"Clases incompatibles: {CLASES}")
modelo = PoseClassifier().to(device)
modelo.load_state_dict(checkpoint["model_state_dict"])
modelo.eval()


def analizar_imagen(frame):
    """YOLO una vez; CNN sobre recorte; MLP sobre coordenadas del frame original.

    Se exige una persona para evitar mezclar visitantes durante la confirmación.
    """
    salida = dict(estado="sin_persona", clase=None, confianza=0.0,
                  confianza_pose=None, personas=0, puntos_visibles=0, keypoints=[])
    with INFERENCIA_LOCK, torch.inference_mode():
        resultado = yolo(frame, conf=0.25, verbose=False)[0]
        cantidad = len(resultado.boxes) if resultado.boxes is not None else 0
        salida["personas"] = cantidad
        if cantidad == 0:
            return salida
        if cantidad != 1:
            salida["estado"] = "multiples_personas"
            return salida
        if resultado.keypoints is None or resultado.keypoints.conf is None:
            salida["estado"] = "puntos_insuficientes"
            return salida
        puntos = resultado.keypoints.xyn[0].cpu().numpy()
        confianza_puntos = resultado.keypoints.conf[0].cpu().numpy()
        if puntos.shape != (17, 2) or not np.isfinite(puntos).all():
            salida["estado"] = "puntos_insuficientes"
            return salida
        salida["keypoints"] = [
            [float(x), float(y), float(c)] for (x, y), c in zip(puntos, confianza_puntos)
        ]
        salida["puntos_visibles"] = int((confianza_puntos >= UMBRAL_PUNTO).sum())
        x1, y1, x2, y2 = resultado.boxes.xyxy[0].cpu().numpy()
        margen_x, margen_y = (x2 - x1) * 0.10, (y2 - y1) * 0.10
        alto, ancho = frame.shape[:2]
        x1, x2 = max(0, int(x1 - margen_x)), min(ancho, int(x2 + margen_x))
        y1, y2 = max(0, int(y1 - margen_y)), min(alto, int(y2 + margen_y))
        if x2 <= x1 or y2 <= y1:
            salida["estado"] = "puntos_insuficientes"
            return salida
        recorte = Image.fromarray(cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2RGB))
        salida["confianza_pose"] = evaluar_pose(recorte)
        if salida["confianza_pose"] < UMBRAL_CNN:
            salida["estado"] = "no_pose"
            return salida
        if not (confianza_puntos[5:17] >= UMBRAL_PUNTO).all():
            salida["estado"] = "puntos_insuficientes"
            return salida
        entrada = torch.as_tensor(puntos.flatten(), dtype=torch.float32, device=device).unsqueeze(0)
        probabilidades = torch.softmax(modelo(entrada), dim=1)
        confianza, indice = probabilidades[0].max(dim=0)
        salida["confianza"] = confianza.item()
        salida["estado"] = "sin_clasificacion"
        if salida["confianza"] >= UMBRAL:
            salida.update(estado="analizando", clase=CLASES[indice.item()])
        return salida


def analizar_frame(archivo):
    datos = np.frombuffer(archivo.read(), dtype=np.uint8)
    frame = cv2.imdecode(datos, cv2.IMREAD_COLOR) if datos.size else None
    if frame is None:
        raise ValueError("El archivo no contiene una imagen válida")
    if frame.shape[0] * frame.shape[1] > 16000000:
        raise ValueError("La imagen supera los 16 megapíxeles")
    return analizar_imagen(frame)
