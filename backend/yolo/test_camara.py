import time
from pathlib import Path
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
from ultralytics import YOLO



ROOT_DIR = Path(__file__).resolve().parents[2]


CLASSIFIER_PATH = ROOT_DIR / "models" / "yolo" / "pose_classifier.pth"
YOLO_MODEL = "yolo11n-pose.pt"
CAMERA_INDEX = 0
UMBRAL_YOLO = 0.60
UMBRAL_CLASIFICACION = 0.70

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

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 50)
print("SISTEMA DE RECONOCIMIENTO DE DANZAS")
print("=" * 50)
print(f"Dispositivo: {device}")
print("\nCargando YOLO Pose...")
yolo_pose = YOLO(YOLO_MODEL)
print("YOLO Pose cargado correctamente")


print("\nCargando clasificador...")

if not CLASSIFIER_PATH.exists():
    raise FileNotFoundError(
        f"No se encontró el clasificador en:\n{CLASSIFIER_PATH}"
    )

checkpoint = torch.load(
    CLASSIFIER_PATH,
    map_location=device
)

modelo_cargado = PoseClassifier().to(device)

modelo_cargado.load_state_dict(
    checkpoint["model_state_dict"]
)

CLASES = checkpoint["classes"]

modelo_cargado.eval()

print("Clasificador cargado correctamente")
print("Clases:", CLASES)


def clasificar_pose(puntos):
    """
    Recibe los 17 keypoints normalizados de YOLO Pose
    y devuelve:

    - clase predicha
    - confianza
    - probabilidades
    """

    if len(puntos) != 17:
        return None

    # 17 puntos × (x, y) = 34 características
    caracteristicas = puntos.flatten()

    if len(caracteristicas) != 34:
        return None

    entrada = torch.tensor(
        caracteristicas,
        dtype=torch.float32
    ).unsqueeze(0).to(device)

    with torch.no_grad():

        logits = modelo_cargado(entrada)

        probabilidades = F.softmax(
            logits,
            dim=1
        )

        confianza, indice = torch.max(
            probabilidades,
            dim=1
        )

    indice = indice.item()
    confianza = confianza.item()

    clase = CLASES[indice]

    return clase, confianza, probabilidades


cap = cv2.VideoCapture(CAMERA_INDEX)
if not cap.isOpened():
    raise RuntimeError(
        "No se pudo abrir la cámara."
    )

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("\nCámara abierta correctamente")
print("Presiona Q para salir")
print("=" * 50)


tiempo_anterior = time.time()

try:

    while True:

        ret, frame = cap.read()

        if not ret:
            print("No se pudo leer el frame")
            break

        resultados = yolo_pose(
            frame,
            conf=UMBRAL_YOLO,
            verbose=False
        )

        resultado = resultados[0]
        frame_visual = resultado.plot()
        texto = "BUSCANDO PERSONA..."
        color = (0, 255, 255)

        if (
            resultado.keypoints is not None
            and resultado.keypoints.xyn is not None
            and len(resultado.keypoints.xyn) > 0
        ):

            indice_persona = 0
            if (
                resultado.boxes is not None
                and resultado.boxes.conf is not None
                and len(resultado.boxes.conf) > 1
            ):
                indice_persona = int(
                    torch.argmax(
                        resultado.boxes.conf
                    ).item()
                )

            # Keypoints normalizados
            puntos = (
                resultado
                .keypoints
                .xyn[indice_persona]
                .cpu()
                .numpy()
            )

            prediccion = clasificar_pose(puntos)

            if prediccion is not None:

                clase_predicha, confianza, probabilidades = prediccion

                porcentaje = confianza * 100

                if confianza >= UMBRAL_CLASIFICACION:

                    texto = (
                        f"{clase_predicha.upper()} "
                        f"{porcentaje:.1f}%"
                    )

                    # Verde = pose aceptada
                    color = (0, 255, 0)

                else:
                    texto = (
                        f"POSE NO RECONOCIDA "
                        f"({porcentaje:.1f}%)"
                    )
                    color = (0, 165, 255)

        else:
            texto = "NO SE DETECTA PERSONA"
            color = (0, 0, 255)


        tiempo_actual = time.time()
        diferencia = tiempo_actual - tiempo_anterior

        if diferencia > 0:
            fps = 1 / diferencia
        else:
            fps = 0

        tiempo_anterior = tiempo_actual

        cv2.putText(
            frame_visual,
            texto,
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            frame_visual,
            f"FPS: {fps:.1f}",
            (30, 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        cv2.imshow(
            "Detector de danzas - YOLO Pose",
            frame_visual
        )

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q"):
            break

finally:

    cap.release()
    cv2.destroyAllWindows()
    print("\nCámara cerrada correctamente")