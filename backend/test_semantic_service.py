from pathlib import Path

from PIL import Image

from backend.services.semantic_search import (
    SemanticSearchService
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

TILES_DIR = (
    PROJECT_ROOT
    / "data"
    / "tiles"
    / "prayagraj"
    / "before"
)


def main():
    print("=== ORION Semantic Search Service Test ===")

    print("\nCreating service...")

    service = SemanticSearchService()

    print("\n--- TEXT SEARCH ---")

    text_results = service.search_text(
        "temporary structures near a river",
        top_k=5
    )

    print(
        f"Query: {text_results['query']}"
    )

    for result in text_results["results"]:
        print(
            f"{result['rank']}. "
            f"score={result['score']:.4f}  "
            f"tile={result['tile_id']}"
        )

    print("\n--- IMAGE SEARCH ---")

    tile_paths = sorted(
        TILES_DIR.glob("*.png")
    )

    if not tile_paths:
        raise FileNotFoundError(
            f"No tiles found:\n{TILES_DIR}"
        )

    query_tile = tile_paths[
        len(tile_paths) // 2
    ]

    image = Image.open(
        query_tile
    ).convert("RGB")

    print(
        f"Query image: "
        f"{query_tile.name}"
    )

    image_results = service.search_image(
        image,
        top_k=5
    )

    for result in image_results["results"]:
        print(
            f"{result['rank']}. "
            f"score={result['score']:.4f}  "
            f"tile={result['tile_id']}"
        )

    print(
        "\n=== SEMANTIC SERVICE TEST COMPLETE ==="
    )


if __name__ == "__main__":
    main()