from pathlib import Path
import json

import faiss
import numpy as np
from PIL import Image

from backend.services.remoteclip import RemoteCLIPEncoder


PROJECT_ROOT = Path(__file__).resolve().parent.parent

TILES_DIR = (
    PROJECT_ROOT
    / "data"
    / "tiles"
    / "prayagraj"
    / "before"
)

INDEX_DIR = (
    PROJECT_ROOT
    / "data"
    / "indexes"
    / "prayagraj"
    / "before"
)

INDEX_PATH = INDEX_DIR / "index.faiss"
METADATA_PATH = INDEX_DIR / "metadata.json"


def main():
    print("=== ORION FAISS Index Builder ===")

    tile_paths = sorted(
        TILES_DIR.glob("*.png")
    )

    print(f"Tiles found: {len(tile_paths)}")

    if not tile_paths:
        raise FileNotFoundError(
            f"No tiles found in:\n{TILES_DIR}"
        )

    INDEX_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("\nLoading RemoteCLIP...")

    encoder = RemoteCLIPEncoder()

    print("\nLoading tile images...")

    images = []

    for tile_path in tile_paths:
        image = Image.open(tile_path).convert("RGB")
        images.append(image)

    print(
        f"Loaded {len(images)} tile images."
    )

    print("\nGenerating embeddings...")

    embeddings = encoder.encode_images(
        images,
        batch_size=16
    )

    embeddings = embeddings.numpy().astype(
        np.float32
    )

    print(
        f"Embedding matrix shape: "
        f"{embeddings.shape}"
    )

    # ---------------------------------------------------------
    # FAISS index
    # ---------------------------------------------------------
    #
    # Embeddings are L2-normalized, so inner product is
    # equivalent to cosine similarity.
    #
    # Higher score = more similar.
    #
    print("\nBuilding FAISS index...")

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(embeddings)

    print(
        f"Vectors in index: "
        f"{index.ntotal}"
    )

    # ---------------------------------------------------------
    # Save index
    # ---------------------------------------------------------

    faiss.write_index(
        index,
        str(INDEX_PATH)
    )

    print(
        f"FAISS index saved to:\n{INDEX_PATH}"
    )

    # ---------------------------------------------------------
    # Save metadata
    # ---------------------------------------------------------

    metadata = []

    for tile_path in tile_paths:
        metadata.append(
            {
                "tile_id": tile_path.stem,
                "filename": tile_path.name,
                "path": str(tile_path),
                "scene_id": "prayagraj",
                "observation": "before",
                "source_raster": "before.tif",
                "tile_size": 256,
            }
        )

    with open(
        METADATA_PATH,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2
        )

    print(
        f"Metadata saved to:\n{METADATA_PATH}"
    )

    # ---------------------------------------------------------
    # Verify index
    # ---------------------------------------------------------

    print("\n=== INDEX VERIFICATION ===")

    test_index = faiss.read_index(
        str(INDEX_PATH)
    )

    print(
        f"Reloaded vectors: "
        f"{test_index.ntotal}"
    )

    print(
        f"Vector dimension: "
        f"{test_index.d}"
    )

    if test_index.ntotal == len(tile_paths):
        print("Vector count check: PASS")
    else:
        print("Vector count check: FAIL")

    if test_index.d == 512:
        print("Embedding dimension check: PASS")
    else:
        print("Embedding dimension check: FAIL")

    print("\n=== INDEX BUILD COMPLETE ===")


if __name__ == "__main__":
    main()