
from pathlib import Path
from PIL import Image

import torch
import torch.nn as nn
from torchvision import models, transforms

ROOT = Path(__file__).resolve().parents[2]
RUTA_MODELO = ROOT / "models" / "cnn" / "cnn_filtro_pose.pth"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Misma arquitectura utilizada en Colab
modelo = models.mobilenet_v2(weights=None)

entradas = modelo.classifier[1].in_features

modelo.classifier = nn.Sequential(
    nn.Dropout(0.40),
    nn.Linear(entradas, 128),
    nn.ReLU(),
    nn.Dropout(0.30),
    nn.Linear(128, 2)
)

checkpoint = torch.load(RUTA_MODELO, map_location=device, weights_only=True)

modelo.load_state_dict(checkpoint["model_state_dict"])
modelo = modelo.to(device)
modelo.eval()

# Mismo preprocesamiento de evaluación del notebook
transformacion = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


def detectar_pose(archivo):
    imagen = Image.open(archivo).convert("RGB")
    entrada = transformacion(imagen).unsqueeze(0).to(device)

    with torch.no_grad():
        salida = modelo(entrada)
        probabilidades = torch.softmax(salida, dim=1)

    confianza_pose = probabilidades[0][1].item()

    print(f"CNN - Probabilidad de pose: {confianza_pose:.2%}")

    return confianza_pose >= 0.70
