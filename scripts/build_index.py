"""
Offline indexer — run once before first use.

Joins indiana_projections.csv + indiana_reports.csv on uid,
filters to Frontal projections, runs each image through the
DenseNet feature layer, and saves data/embeddings.npz.

Usage:
    conda run -n cxr python scripts/build_index.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from PIL import Image, UnidentifiedImageError

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.classifier import get_query_embedding, load_model

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_DIR = os.path.join(_HERE, "data", "images", "images_normalized")
PROJECTIONS_CSV = os.path.join(_HERE, "data", "indiana_projections.csv")
REPORTS_CSV = os.path.join(_HERE, "data", "indiana_reports.csv")
OUTPUT_PATH = os.path.join(_HERE, "data", "embeddings.npz")


def main():
    print(f"Output path (absolute): {OUTPUT_PATH}")
    print("Loading model...")
    model = load_model()

    print("Loading CSVs...")
    proj = pd.read_csv(PROJECTIONS_CSV)
    reports = pd.read_csv(REPORTS_CSV)

    # Filter to Frontal only, take first Frontal per uid
    frontal = proj[proj["projection"] == "Frontal"].drop_duplicates(subset="uid")
    merged = frontal.merge(reports[["uid", "findings", "impression"]], on="uid", how="left")

    print(f"Found {len(merged)} Frontal cases. Building embeddings...")

    embeddings = []
    metadata = []
    skipped = 0

    for i, row in enumerate(merged.itertuples(), 1):
        img_path = os.path.join(IMAGES_DIR, row.filename)
        try:
            pil_img = Image.open(img_path)
            pil_img.load()  # force decode
        except (FileNotFoundError, UnidentifiedImageError, Exception) as exc:
            skipped += 1
            continue

        try:
            emb = get_query_embedding(model, pil_img)
        except Exception as exc:
            skipped += 1
            continue

        embeddings.append(emb)
        metadata.append({
            "uid": str(row.uid),
            "findings": str(row.findings) if pd.notna(row.findings) else None,
            "impression": str(row.impression) if pd.notna(row.impression) else None,
            "image_path": img_path,
        })

        if i % 100 == 0:
            print(f"  Processed {i}/{len(merged)} images ({skipped} skipped)...")

    if not embeddings:
        print("No embeddings generated. Check that image files exist.")
        return

    emb_array = np.array(embeddings, dtype=np.float32)
    meta_array = np.array([json.dumps(m) for m in metadata], dtype=object)

    np.savez_compressed(OUTPUT_PATH, embeddings=emb_array, metadata=meta_array)
    print(
        f"\nDone. Saved {len(embeddings)} embeddings to {OUTPUT_PATH} "
        f"({skipped} images skipped)."
    )


if __name__ == "__main__":
    main()
