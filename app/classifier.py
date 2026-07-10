"""Classifier and feature extractor using torchxrayvision DenseNet."""
import numpy as np
import torch
import torchxrayvision as xrv
from PIL import Image

# The model produces scores for these 18 pathology labels
LABELS = [
    "Atelectasis", "Consolidation", "Infiltration", "Pneumothorax",
    "Edema", "Emphysema", "Fibrosis", "Effusion", "Pneumonia",
    "Pleural_Thickening", "Cardiomegaly", "Nodule", "Mass", "Hernia",
    "Lung Lesion", "Fracture", "Lung Opacity", "Enlarged Cardiomediastinum",
]


def load_model() -> xrv.models.DenseNet:
    """Load densenet121-res224-all once and return in eval mode."""
    model = xrv.models.DenseNet(weights="densenet121-res224-all")
    model.eval()
    return model


def _preprocess(img: Image.Image) -> np.ndarray:
    """Convert PIL image to the float32 array xrv expects: (1,224,224) in [-1024,1024]."""
    img = img.convert("L")  # grayscale
    img = img.resize((224, 224))
    arr = np.array(img, dtype=np.float32)
    # xrv normalize: maps [0,255] → [-1024,1024]
    arr = xrv.datasets.normalize(arr, maxval=255, reshape=True)
    return arr  # shape (1, 224, 224)


def run_inference(model: xrv.models.DenseNet, img: Image.Image) -> dict[str, float]:
    """Return {label: probability} for all pathology labels."""
    arr = _preprocess(img)
    tensor = torch.from_numpy(arr).unsqueeze(0)  # (1, 1, 224, 224)
    with torch.no_grad():
        output = model(tensor)  # (1, num_classes) — already probabilities, no sigmoid needed
    probs = output.squeeze().numpy()
    labels = model.pathologies
    return {label: float(prob) for label, prob in zip(labels, probs)}


def get_query_embedding(model: xrv.models.DenseNet, img: Image.Image) -> np.ndarray:
    """Extract the feature vector from the DenseNet feature block."""
    arr = _preprocess(img)
    tensor = torch.from_numpy(arr).unsqueeze(0)  # (1, 1, 224, 224)
    with torch.no_grad():
        feats = model.features(tensor)          # (1, 1024, 7, 7)
        pooled = torch.nn.functional.adaptive_avg_pool2d(feats, (1, 1))
        embedding = pooled.squeeze().numpy()    # (1024,)
    return embedding
