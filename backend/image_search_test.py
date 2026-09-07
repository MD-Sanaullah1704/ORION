from pathlib import Path
import json

import faiss
import numpy as np
from PIL import Image

from backend.services.remoteclip import RemoteCLIPEncoder


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INDEX_PATH = (
    PROJECT_ROOT
    / "data"
    / "indexes"
    / "prayagraj"
    / "before"
    / "index.faiss"
)

METADATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "indexes"
    / "prayagraj"
    / "before"
    / "metadata.json"
)

TILES_DIR = (
    PROJECT_ROOT
    / "data"
    / "tiles"
    / "prayagraj"
    / "before"
)


def main():
    print("=== ORION Image-to-Image Search Test ===")

    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"FAISS index not found:\n{INDEX_PATH}"
        )

    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            f"Metadata not found:\n{METADATA_PATH}"
        )

    if not TILES_DIR.exists():
        raise FileNotFoundError(
            f"Tiles directory not found:\n{TILES_DIR}"
        )

    print("\nLoading FAISS index...")

    index = faiss.read_index(
        str(INDEX_PATH)
    )

    print(
        f"Vectors loaded: {index.ntotal}"
    )

    with open(
        METADATA_PATH,
        "r",
        encoding="utf-8"
    ) as file:
        metadata = json.load(file)

    print(
        f"Metadata records: {len(metadata)}"
    )

    # Automatically select a real tile from the dataset.
    tile_paths = sorted(
        TILES_DIR.glob("*.png")
    )

    if not tile_paths:
        raise FileNotFoundError(
            f"No PNG tiles found in:\n{TILES_DIR}"
        )

    query_tile = tile_paths[
        len(tile_paths) // 2
    ]

    print("\nLoading query image...")

    query_image = Image.open(
        query_tile
    ).convert("RGB")

    print(
        f"Query tile: {query_tile.name}"
    )

    print(
        f"Image size: "
        f"{query_image.width} x "
        f"{query_image.height}"
    )

    print("\nLoading RemoteCLIP...")

    encoder = RemoteCLIPEncoder()

    print("\nGenerating query image embedding...")

    query_embedding = encoder.encode_image(
        query_image
    )

    print(
        f"Embedding shape: "
        f"{tuple(query_embedding.shape)}"
    )

    print(
        f"Embedding norm: "
        f"{query_embedding.norm().item():.4f}"
    )

    query_vector = (
        query_embedding
        .numpy()
        .astype(np.float32)
    )

    query_vector = query_vector.reshape(
        1,
        -1
    )

    print("\nSearching FAISS index...")

    scores, indices = index.search(
        query_vector,
        5
    )

    print(
        "\nTop 5 visually/semantically "
        "similar tiles:\n"
    )

    for rank, (score, index_id) in enumerate(
        zip(scores[0], indices[0]),
        start=1
    ):
        tile = metadata[index_id]

        marker = ""

        if tile["filename"] == query_tile.name:
            marker = "  <-- QUERY TILE"

        print(
            f"{rank}. "
            f"score={score:.4f}  "
            f"tile={tile['tile_id']}  "
            f"file={tile['filename']}"
            f"{marker}"
        )

    print(
        "\n=== IMAGE-TO-IMAGE SEARCH TEST COMPLETE ==="
    )


if __name__ == "__main__":
    main()