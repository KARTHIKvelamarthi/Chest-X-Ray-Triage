"""Grad-CAM heatmap generation using pytorch-grad-cam."""
import uuid
import os
import numpy as np
import torch
import torchxrayvision as xrv
from PIL import Image
import cv2
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

HEATMAP_DIR = os.path.join("static", "heatmaps")


def _preprocess_tensor(img: Image.Image) -> torch.Tensor:
    """Return (1,1,224,224) float32 tensor."""
    img = img.convert("L").resize((224, 224))
    arr = np.array(img, dtype=np.float32)
    arr = xrv.datasets.normalize(arr, maxval=255, reshape=True)
    return torch.from_numpy(arr).unsqueeze(0)  # (1,1,224,224)


def generate_heatmap(
    model: xrv.models.DenseNet,
    original_pil: Image.Image,
    target_label_idx: int,
) -> str:
    """
    Run GradCAM on model.features targeting the given class index.
    Overlay a jet colormap at 0.5 alpha onto the original image.
    Save to static/heatmaps/{uuid}.png and return the relative URL path.
    """
    os.makedirs(HEATMAP_DIR, exist_ok=True)

    input_tensor = _preprocess_tensor(original_pil)

    # Target the last dense block in model.features
    target_layers = [model.features.denseblock4]

    cam = GradCAM(model=model, target_layers=target_layers)
    targets = [ClassifierOutputTarget(target_label_idx)]

    grayscale_cam = cam(input_tensor=input_tensor, targets=targets)
    grayscale_cam = grayscale_cam[0]  # (224, 224)

    # Resize original to 224x224 for overlay
    orig_resized = original_pil.convert("RGB").resize((224, 224))
    orig_arr = np.array(orig_resized, dtype=np.uint8)

    # Apply jet colormap
    heatmap_uint8 = np.uint8(255 * grayscale_cam)
    heatmap_colored = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
    heatmap_rgb = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

    # Blend
    overlay = (orig_arr * 0.5 + heatmap_rgb * 0.5).astype(np.uint8)
    result_pil = Image.fromarray(overlay)

    filename = f"{uuid.uuid4().hex}.png"
    save_path = os.path.join(HEATMAP_DIR, filename)
    result_pil.save(save_path)

    return f"/static/heatmaps/{filename}"
