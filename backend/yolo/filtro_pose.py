"""Filtro binario sobre recortes de persona, como en CNN.PERSONA.ipynb."""
from pathlib import Path
import torch
from torch import nn
from torchvision import models, transforms

ROOT = Path(__file__).resolve().parents[2]
RUTA_MODELO = ROOT / "models/cnn/cnn_filtro_pose.pth"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if not RUTA_MODELO.is_file():
    raise FileNotFoundError(f"Falta el filtro CNN: {RUTA_MODELO}")
checkpoint = torch.load(RUTA_MODELO, map_location=device, weights_only=True)
modelo = models.mobilenet_v2(weights=None)
modelo.classifier = nn.Sequential(
    nn.Dropout(0.40), nn.Linear(modelo.classifier[1].in_features, 128),
    nn.ReLU(), nn.Dropout(0.30), nn.Linear(128, 2),
)
modelo.load_state_dict(checkpoint["model_state_dict"])
modelo.to(device).eval()
INDICE_POSE = next(int(i) for i, nombre in checkpoint["class_names"].items() if nombre == "pose")
transformacion = transforms.Compose([
    transforms.Resize((checkpoint["img_size"], checkpoint["img_size"])),
    transforms.ToTensor(),
    transforms.Normalize(checkpoint["normalization_mean"], checkpoint["normalization_std"]),
])


def evaluar_pose(imagen):
    """Devuelve P(pose) de un recorte PIL RGB."""
    entrada = transformacion(imagen.convert("RGB")).unsqueeze(0).to(device)
    with torch.inference_mode():
        return torch.softmax(modelo(entrada), dim=1)[0, INDICE_POSE].item()
