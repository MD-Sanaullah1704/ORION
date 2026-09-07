from pathlib import Path
import json

import faiss

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


QUERIES = [
    "temporary structures near a river",
    "roads and transportation infrastructure",
    "vegetation and green areas",
    "water body",
    "urban development",
]


def main():
    print("=== ORION Semantic Search Test ===")

    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"FAISS index not found:\n{INDEX_PATH}"
        )

    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            f"Metadata not found:\n{METADATA_PATH}"
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

    print("\nLoading RemoteCLIP...")

    encoder = RemoteCLIPEncoder()

    for query in QUERIES:

        print("\n" + "=" * 60)
        print(f'QUERY: "{query}"')
        print("=" * 60)

        query_embedding = encoder.encode_text(
            query
        )

        query_vector = (
            query_embedding
            .numpy()
            .astype("float32")
        )

        query_vector = query_vector.reshape(
            1,
            -1
        )

        scores, indices = index.search(
            query_vector,
            5
        )

        print("\nTop 5 results:\n")

        for rank, (score, index_id) in enumerate(
            zip(scores[0], indices[0]),
            start=1
        ):
            tile = metadata[index_id]

            print(
                f"{rank}. "
                f"score={score:.4f}  "
                f"tile={tile['tile_id']}  "
                f"file={tile['filename']}"
            )

    print("\n=== SEMANTIC SEARCH TEST COMPLETE ===")


if __name__ == "__main__":
    main()