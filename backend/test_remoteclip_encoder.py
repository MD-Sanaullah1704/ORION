from pathlib import Path

from PIL import Image

from backend.services.remoteclip import RemoteCLIPEncoder


PROJECT_ROOT = Path(__file__).resolve().parent.parent

IMAGE_PATH = (
    PROJECT_ROOT
    / "data"
    / "scenes"
    / "prayagraj"
    / "before.tif"
)


def main():
    print("=== ORION RemoteCLIP Encoder Test ===")

    encoder = RemoteCLIPEncoder()

    print("\nLoading satellite image...")

    image = Image.open(IMAGE_PATH).convert("RGB")

    print(
        f"Image size: {image.width} x {image.height}"
    )

    print("\nEncoding image...")

    image_embedding = encoder.encode_image(image)

    print(
        f"Image embedding shape: "
        f"{tuple(image_embedding.shape)}"
    )

    print(
        f"Image embedding norm: "
        f"{image_embedding.norm().item():.4f}"
    )

    query = "temporary structures near a river"

    print(
        f'\nEncoding text: "{query}"'
    )

    text_embedding = encoder.encode_text(query)

    print(
        f"Text embedding shape: "
        f"{tuple(text_embedding.shape)}"
    )

    print(
        f"Text embedding norm: "
        f"{text_embedding.norm().item():.4f}"
    )

    similarity = (
        image_embedding @ text_embedding
    ).item()

    print(
        f"\nText-image similarity: "
        f"{similarity:.4f}"
    )

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()