from pathlib import Path

import torch
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


def main():
    print("=== ORION Tile Embedding Test ===")

    tile_paths = sorted(
        TILES_DIR.glob("*.png")
    )

    print(f"Tiles found: {len(tile_paths)}")

    if not tile_paths:
        raise FileNotFoundError(
            f"No tiles found in:\n{TILES_DIR}"
        )

    print("\nLoading RemoteCLIP...")

    encoder = RemoteCLIPEncoder()

    print("\nEncoding tiles...")

    images = []

    for tile_path in tile_paths:
        image = Image.open(tile_path).convert("RGB")
        images.append(image)

    embeddings = encoder.encode_images(
        images,
        batch_size=16
    )

    print("\n=== RESULTS ===")

    print(
        f"Number of embeddings: "
        f"{embeddings.shape[0]}"
    )

    print(
        f"Embedding dimension: "
        f"{embeddings.shape[1]}"
    )

    print(
        f"Embedding tensor shape: "
        f"{tuple(embeddings.shape)}"
    )

    norms = embeddings.norm(
        dim=1
    )

    print(
        f"Minimum embedding norm: "
        f"{norms.min().item():.4f}"
    )

    print(
        f"Maximum embedding norm: "
        f"{norms.max().item():.4f}"
    )

    print(
        f"Average embedding norm: "
        f"{norms.mean().item():.4f}"
    )

    print("\nFirst tile:")
    print(tile_paths[0].name)

    print(
        "First embedding first 10 values:"
    )

    print(
        embeddings[0][:10]
    )

    if torch.cuda.is_available():
        allocated = (
            torch.cuda.memory_allocated()
            / (1024 ** 3)
        )

        reserved = (
            torch.cuda.memory_reserved()
            / (1024 ** 3)
        )

        print(
            f"\nGPU memory allocated: "
            f"{allocated:.2f} GB"
        )

        print(
            f"GPU memory reserved: "
            f"{reserved:.2f} GB"
        )

    print("\n=== TILE EMBEDDING TEST COMPLETE ===")


if __name__ == "__main__":
    main()