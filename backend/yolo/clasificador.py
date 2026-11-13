import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from ultralytics import YOLO


# ============================================================
# CONFIGURACIÓN
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

CLASSIFIER_PATH = ROOT_DIR / "models" / "yolo" / "pose_classifier.pth"

UMBRAL = 0.85

# ============================================================
# MODELO MLP
# ============================================================

class PoseClassifier(nn.Module):

    def __init__(self):

        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(34, 64),
            nn.ReLU(),

            nn.Linear(64, 32),
            nn.ReLU(),

            nn.Dropout(0.20),

            nn.Linear(32, 4)
        )

    def forward(self, x):

        return self.network(x)


# ============================================================
# CARGAR MODELOS
# ============================================================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

yolo = YOLO("yolo11n-pose.pt")

checkpoint = torch.load(
    CLASSIFIER_PATH,
    map_location=device
)

modelo = PoseClassifier().to(device)

modelo.load_state_dict(
    checkpoint["model_state_dict"]
)

CLASES = checkpoint["classes"]

modelo.eval()


# ============================================================
# ANALIZAR FRAME
# ============================================================

def analizar_frame(archivo):

    # Convertir imagen recibida a OpenCV
    bytes_imagen = np.frombuffer(
        archivo.read(),
        np.uint8
    )

    frame = cv2.imdecode(
        bytes_imagen,
        cv2.IMREAD_COLOR
    )

    if frame is None:
        return None, 0


    # --------------------------------------------------------
    # YOLO POSE
    # --------------------------------------------------------

    resultado = yolo(
        frame,
        conf=0.25,
        verbose=False
    )[0]


    # Si no hay persona
    if (
        resultado.keypoints is None
        or resultado.keypoints.xyn is None
        or len(resultado.keypoints.xyn) == 0
    ):
        return None, 0


    # Primera persona detectada
    puntos = (
        resultado.keypoints
        .xyn[0]
        .cpu()
        .numpy()
    )


    # Deben existir 17 puntos
    if len(puntos) != 17:
        return None, 0


    # --------------------------------------------------------
    # CLASIFICADOR
    # --------------------------------------------------------

    caracteristicas = puntos.flatten()

    entrada = torch.tensor(
        caracteristicas,
        dtype=torch.float32
    ).unsqueeze(0).to(device)


    with torch.no_grad():

        salida = modelo(entrada)

        probabilidades = F.softmax(
            salida,
            dim=1
        )

    for i, clase_nombre in enumerate(CLASES):
        print(
            clase_nombre,
            round(probabilidades[0][i].item() * 100, 2),
            "%"
        )

        print("--------------------")

        valores, indices = torch.topk(
            probabilidades,
            2,
            dim=1
        )


        confianza = valores[0][0].item()
        segunda_confianza = valores[0][1].item()

        indice = indices[0][0].item()

        clase = CLASES[indice]

    if confianza < UMBRAL:
        return None, confianza


    return clase, confianza