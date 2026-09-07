from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from PIL import Image


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "remoteclip"
    / "RemoteCLIP-ViT-B-32.pt"
)

DEFAULT_INDEX_ROOT = (
    PROJECT_ROOT
    / "data"
    / "indexes"
)


# ============================================================
# ORION CONSTANTS
# ============================================================

EMBEDDING_DIMENSION = 512

TILE_SIZE = 256

SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".webp",
}


# ============================================================
# REMOTECLIP
# ============================================================

def load_remoteclip(
    checkpoint_path: Path,
):
    """
    Load the local RemoteCLIP ViT-B/32 checkpoint.

    No external API is used.
    """

    try:
        import torch
        import open_clip

    except ImportError as error:

        raise RuntimeError(
            "RemoteCLIP dependencies are missing: "
            f"{error}"
        )

    if not checkpoint_path.exists():

        raise FileNotFoundError(
            "RemoteCLIP checkpoint not found:\n"
            f"{checkpoint_path}"
        )

    print()
    print("=" * 70)
    print("LOADING REMOTECLIP")
    print("=" * 70)

    print(
        f"Checkpoint: {checkpoint_path}"
    )

    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(
        f"Device: {device}"
    )

    # --------------------------------------------------------
    # Create architecture without downloading pretrained weights
    # --------------------------------------------------------

    model, _, preprocess = (
        open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained=None,
        )
    )

    # --------------------------------------------------------
    # Load local checkpoint
    # --------------------------------------------------------

    checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
    )

    if isinstance(
        checkpoint,
        dict,
    ):

        if "state_dict" in checkpoint:

            state_dict = checkpoint["state_dict"]

        elif "model" in checkpoint:

            state_dict = checkpoint["model"]

        else:

            state_dict = checkpoint

    else:

        state_dict = checkpoint

    # --------------------------------------------------------
    # Clean common prefixes
    # --------------------------------------------------------

    cleaned_state_dict = {}

    for key, value in state_dict.items():

        new_key = key

        if new_key.startswith(
            "module."
        ):

            new_key = new_key[
                len("module.") :
            ]

        cleaned_state_dict[
            new_key
        ] = value

    # --------------------------------------------------------
    # Load weights
    # --------------------------------------------------------

    missing, unexpected = (
        model.load_state_dict(
            cleaned_state_dict,
            strict=False,
        )
    )

    if missing:

        print(
            f"Warning: {len(missing)} missing "
            "checkpoint keys."
        )

    if unexpected:

        print(
            f"Warning: {len(unexpected)} unexpected "
            "checkpoint keys."
        )

    model = model.to(
        device
    )

    model.eval()

    print(
        "RemoteCLIP loaded successfully."
    )

    return (
        model,
        preprocess,
        device,
        torch,
    )


# ============================================================
# IMAGE EMBEDDING
# ============================================================

def encode_image(
    image_path: Path,
    model,
    preprocess,
    device,
    torch,
) -> np.ndarray:

    """
    Generate one normalized 512-dimensional
    RemoteCLIP image embedding.
    """

    image = Image.open(
        image_path
    ).convert(
        "RGB"
    )

    image_tensor = (
        preprocess(
            image
        )
        .unsqueeze(0)
        .to(device)
    )

    with torch.no_grad():

        features = model.encode_image(
            image_tensor
        )

    # --------------------------------------------------------
    # L2 normalization
    # --------------------------------------------------------

    features = (
        features
        / (
            features.norm(
                dim=-1,
                keepdim=True,
            )
            + 1e-12
        )
    )

    embedding = (
        features[0]
        .detach()
        .cpu()
        .numpy()
        .astype(
            np.float32
        )
    )

    if embedding.shape != (
        EMBEDDING_DIMENSION,
    ):

        raise RuntimeError(
            "Unexpected embedding dimension: "
            f"{embedding.shape}. "
            f"Expected ({EMBEDDING_DIMENSION},)."
        )

    return embedding


# ============================================================
# TILE ID
# ============================================================

def build_tile_id(
    image_path: Path,
) -> str:

    """
    Extract the existing ORION tile identifier.

    Example:
        tile_00029_x1792_y512.png

    becomes:
        tile_00029_x1792_y512
    """

    stem = image_path.stem

    if stem.startswith(
        "tile_"
    ):

        return stem

    # --------------------------------------------------------
    # Fallback for images without ORION naming
    # --------------------------------------------------------

    x, y = parse_coordinates(
        image_path.name
    )

    if (
        x is not None
        and y is not None
    ):

        return (
            f"tile_x{x}_y{y}"
        )

    return stem


# ============================================================
# COORDINATE PARSING
# ============================================================

def parse_coordinates(
    filename: str,
) -> tuple[int | None, int | None]:

    patterns = [
        r"_x(-?\d+)_y(-?\d+)",
        r"x(-?\d+)_y(-?\d+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            filename,
            flags=re.IGNORECASE,
        )

        if match:

            return (
                int(match.group(1)),
                int(match.group(2)),
            )

    return (
        None,
        None,
    )


# ============================================================
# IMAGE DISCOVERY
# ============================================================

def discover_images(
    image_directory: Path,
) -> list[Path]:

    if not image_directory.exists():

        raise FileNotFoundError(
            "Input directory does not exist:\n"
            f"{image_directory}"
        )

    images = []

    for path in sorted(
        image_directory.rglob("*")
    ):

        if not path.is_file():
            continue

        if (
            path.suffix.lower()
            in SUPPORTED_IMAGE_EXTENSIONS
        ):

            images.append(
                path
            )

    return images


# ============================================================
# EXISTING METADATA
# ============================================================

def load_metadata(
    metadata_path: Path,
) -> list[dict[str, Any]]:

    if not metadata_path.exists():

        return []

    try:

        with open(
            metadata_path,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "Existing metadata.json is invalid:\n"
            f"{error}"
        )

    # --------------------------------------------------------
    # Normal ORION format
    # --------------------------------------------------------

    if isinstance(
        data,
        list,
    ):

        return data

    # --------------------------------------------------------
    # Defensive support for wrapped metadata
    # --------------------------------------------------------

    if isinstance(
        data,
        dict,
    ):

        if isinstance(
            data.get("metadata"),
            list,
        ):

            return data["metadata"]

        if isinstance(
            data.get("items"),
            list,
        ):

            return data["items"]

    raise RuntimeError(
        "Unsupported metadata.json format."
    )


# ============================================================
# EXISTING ITEM IDENTITIES
# ============================================================

def metadata_identities(
    metadata: list[dict[str, Any]],
) -> set[str]:

    identities = set()

    for item in metadata:

        # ----------------------------------------------------
        # Existing ORION tile_id
        # ----------------------------------------------------

        tile_id = item.get(
            "tile_id"
        )

        if tile_id:

            identities.add(
                str(tile_id)
            )

        # ----------------------------------------------------
        # Existing filename
        # ----------------------------------------------------

        filename = item.get(
            "filename"
        )

        if filename:

            identities.add(
                str(filename)
            )

        # ----------------------------------------------------
        # Existing path
        # ----------------------------------------------------

        path = item.get(
            "path"
        )

        if path:

            path_string = str(
                path
            )

            identities.add(
                path_string
            )

            identities.add(
                Path(
                    path_string
                ).name
            )

    return identities


# ============================================================
# FAISS INDEX
# ============================================================

def load_or_create_index(
    index_path: Path,
) -> faiss.Index:

    if not index_path.exists():

        print()
        print(
            "No existing FAISS index found."
        )

        print(
            "Creating a new IndexFlatIP index."
        )

        return faiss.IndexFlatIP(
            EMBEDDING_DIMENSION
        )

    print()
    print(
        f"Loading existing FAISS index:\n"
        f"{index_path}"
    )

    index = faiss.read_index(
        str(index_path)
    )

    if index.d != (
        EMBEDDING_DIMENSION
    ):

        raise RuntimeError(
            "FAISS dimension mismatch.\n"
            f"Existing index dimension: {index.d}\n"
            f"Expected dimension: {EMBEDDING_DIMENSION}"
        )

    return index


# ============================================================
# ALIGNMENT CHECK
# ============================================================

def verify_alignment(
    index: faiss.Index,
    metadata: list[dict[str, Any]],
) -> None:

    vector_count = (
        index.ntotal
    )

    metadata_count = (
        len(metadata)
    )

    print()
    print(
        f"FAISS vectors:  {vector_count}"
    )

    print(
        f"Metadata rows:  {metadata_count}"
    )

    if vector_count != metadata_count:

        raise RuntimeError(
            "FAISS index and metadata are not aligned.\n"
            f"FAISS vectors = {vector_count}\n"
            f"Metadata rows = {metadata_count}\n\n"
            "The ingestion process has been stopped "
            "to protect the existing index."
        )


# ============================================================
# BUILD METADATA
# ============================================================

def build_metadata_entry(
    image_path: Path,
    scene_id: str,
    observation: str,
) -> dict[str, Any]:

    tile_id = build_tile_id(
        image_path
    )

    try:

        relative_path = (
            image_path
            .relative_to(
                PROJECT_ROOT
            )
            .as_posix()
        )

    except ValueError:

        relative_path = str(
            image_path
        )

    return {
        "tile_id": tile_id,

        "filename": image_path.name,

        "path": relative_path,

        "scene_id": scene_id,

        "observation": observation,

        "source_raster": (
            f"{observation}.tif"
        ),

        "tile_size": TILE_SIZE,
    }


# ============================================================
# SAVE METADATA
# ============================================================

def save_metadata(
    metadata_path: Path,
    metadata: list[dict[str, Any]],
) -> None:

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# SAVE MANIFEST
# ============================================================

def save_manifest(
    manifest_path: Path,
    manifest: dict[str, Any],
) -> None:

    with open(
        manifest_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            manifest,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# INCREMENTAL INGESTION
# ============================================================

def incremental_ingest(
    image_directory: Path,
    scene_id: str,
    observation: str,
    index_directory: Path,
    model_path: Path,
) -> dict[str, Any]:

    start_time = (
        time.perf_counter()
    )

    index_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    index_path = (
        index_directory
        / "index.faiss"
    )

    metadata_path = (
        index_directory
        / "metadata.json"
    )

    manifest_path = (
        index_directory
        / "ingestion_manifest.json"
    )

    print()
    print("=" * 70)
    print("ORION INCREMENTAL INGESTION")
    print("=" * 70)

    print(
        f"Scene:       {scene_id}"
    )

    print(
        f"Observation: {observation}"
    )

    print(
        f"Input:       {image_directory}"
    )

    print(
        f"Index dir:   {index_directory}"
    )

    # --------------------------------------------------------
    # Discover input images
    # --------------------------------------------------------

    images = discover_images(
        image_directory
    )

    if not images:

        raise RuntimeError(
            "No supported images were found."
        )

    print()
    print(
        f"Images discovered: {len(images)}"
    )

    # --------------------------------------------------------
    # Load existing index
    # --------------------------------------------------------

    index = load_or_create_index(
        index_path
    )

    # --------------------------------------------------------
    # Load existing metadata
    # --------------------------------------------------------

    metadata = load_metadata(
        metadata_path
    )

    # --------------------------------------------------------
    # Critical safety check
    # --------------------------------------------------------

    verify_alignment(
        index,
        metadata,
    )

    vectors_before = (
        index.ntotal
    )

    # --------------------------------------------------------
    # Find existing records
    # --------------------------------------------------------

    existing_identities = (
        metadata_identities(
            metadata
        )
    )

    new_images = []

    skipped_images = []

    for image_path in images:

        tile_id = build_tile_id(
            image_path
        )

        identity_candidates = {
            tile_id,
            image_path.name,
            str(image_path),
        }

        try:

            identity_candidates.add(
                image_path
                .relative_to(
                    PROJECT_ROOT
                )
                .as_posix()
            )

        except ValueError:

            pass

        if (
            identity_candidates
            & existing_identities
        ):

            skipped_images.append(
                image_path
            )

        else:

            new_images.append(
                image_path
            )

    print()
    print(
        f"Existing images skipped: "
        f"{len(skipped_images)}"
    )

    print(
        f"New images: "
        f"{len(new_images)}"
    )

    # --------------------------------------------------------
    # Nothing new
    # --------------------------------------------------------

    if not new_images:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        result = {
            "status": (
                "already_up_to_date"
            ),

            "scene_id": scene_id,

            "observation": observation,

            "images_discovered": len(
                images
            ),

            "images_skipped": len(
                skipped_images
            ),

            "images_added": 0,

            "vectors_before": (
                vectors_before
            ),

            "vectors_added": 0,

            "vectors_after": (
                index.ntotal
            ),

            "incremental": True,

            "elapsed_seconds": round(
                elapsed,
                4,
            ),

            "index_path": str(
                index_path
            ),

            "metadata_path": str(
                metadata_path
            ),
        }

        print()
        print("=" * 70)
        print("NOTHING NEW TO INGEST")
        print("=" * 70)

        print(
            f"Vectors remain: {index.ntotal}"
        )

        return result

    # --------------------------------------------------------
    # Load RemoteCLIP only when new images exist
    # --------------------------------------------------------

    (
        model,
        preprocess,
        device,
        torch,
    ) = load_remoteclip(
        model_path
    )

    # --------------------------------------------------------
    # Encode new images
    # --------------------------------------------------------

    embeddings = []

    new_metadata = []

    for counter, image_path in enumerate(
        new_images,
        start=1,
    ):

        print()
        print(
            f"[{counter}/{len(new_images)}] "
            f"{image_path.name}"
        )

        embedding = encode_image(
            image_path=image_path,
            model=model,
            preprocess=preprocess,
            device=device,
            torch=torch,
        )

        embeddings.append(
            embedding
        )

        metadata_entry = (
            build_metadata_entry(
                image_path=image_path,
                scene_id=scene_id,
                observation=observation,
            )
        )

        new_metadata.append(
            metadata_entry
        )

    # --------------------------------------------------------
    # Build matrix
    # --------------------------------------------------------

    embedding_matrix = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    if embedding_matrix.ndim != 2:

        raise RuntimeError(
            "Unexpected embedding matrix shape:\n"
            f"{embedding_matrix.shape}"
        )

    if embedding_matrix.shape[1] != (
        EMBEDDING_DIMENSION
    ):

        raise RuntimeError(
            "Unexpected embedding dimension:\n"
            f"{embedding_matrix.shape[1]}"
        )

    # --------------------------------------------------------
    # Normalize again defensively
    # --------------------------------------------------------

    norms = np.linalg.norm(
        embedding_matrix,
        axis=1,
        keepdims=True,
    )

    embedding_matrix = (
        embedding_matrix
        / np.maximum(
            norms,
            1e-12,
        )
    )

    # --------------------------------------------------------
    # ADD ONLY NEW VECTORS
    # --------------------------------------------------------

    print()
    print(
        "Adding new vectors to FAISS..."
    )

    index.add(
        embedding_matrix
    )

    # --------------------------------------------------------
    # Append metadata in EXACT same order
    # --------------------------------------------------------

    metadata.extend(
        new_metadata
    )

    # --------------------------------------------------------
    # Verify alignment before saving
    # --------------------------------------------------------

    verify_alignment(
        index,
        metadata,
    )

    # --------------------------------------------------------
    # Save FAISS
    # --------------------------------------------------------

    print()
    print(
        "Saving FAISS index..."
    )

    faiss.write_index(
        index,
        str(index_path)
    )

    # --------------------------------------------------------
    # Save metadata
    # --------------------------------------------------------

    print(
        "Saving metadata..."
    )

    save_metadata(
        metadata_path,
        metadata,
    )

    # --------------------------------------------------------
    # Timing
    # --------------------------------------------------------

    elapsed = (
        time.perf_counter()
        - start_time
    )

    # --------------------------------------------------------
    # Manifest
    # --------------------------------------------------------

    manifest = {
        "pipeline": (
            "ORION incremental ingestion"
        ),

        "scene_id": scene_id,

        "observation": observation,

        "embedding_model": (
            "RemoteCLIP ViT-B/32"
        ),

        "embedding_dimension": (
            EMBEDDING_DIMENSION
        ),

        "index_type": (
            type(index).__name__
        ),

        "input_directory": str(
            image_directory
        ),

        "index_path": str(
            index_path
        ),

        "metadata_path": str(
            metadata_path
        ),

        "images_discovered": len(
            images
        ),

        "images_skipped": len(
            skipped_images
        ),

        "images_added": len(
            new_images
        ),

        "vectors_before": (
            vectors_before
        ),

        "vectors_added": len(
            new_images
        ),

        "vectors_after": (
            index.ntotal
        ),

        "incremental": True,

        "elapsed_seconds": round(
            elapsed,
            4,
        ),

        "timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%S"
        ),
    }

    save_manifest(
        manifest_path,
        manifest,
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    result = {
        "status": "success",

        "scene_id": scene_id,

        "observation": observation,

        "images_discovered": len(
            images
        ),

        "images_skipped": len(
            skipped_images
        ),

        "images_added": len(
            new_images
        ),

        "vectors_before": (
            vectors_before
        ),

        "vectors_added": len(
            new_images
        ),

        "vectors_after": (
            index.ntotal
        ),

        "incremental": True,

        "elapsed_seconds": round(
            elapsed,
            4,
        ),

        "index_path": str(
            index_path
        ),

        "metadata_path": str(
            metadata_path
        ),

        "manifest_path": str(
            manifest_path
        ),
    }

    print()
    print("=" * 70)
    print("INCREMENTAL INGESTION COMPLETE")
    print("=" * 70)

    print(
        f"Vectors before : {vectors_before}"
    )

    print(
        f"Vectors added  : {len(new_images)}"
    )

    print(
        f"Vectors after  : {index.ntotal}"
    )

    print(
        f"Time           : {elapsed:.2f} seconds"
    )

    return result


# ============================================================
# CLI
# ============================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "ORION incremental RemoteCLIP "
            "embedding and FAISS ingestion"
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help=(
            "Directory containing image tiles."
        ),
    )

    parser.add_argument(
        "--scene-id",
        required=True,
        help=(
            "ORION scene ID, e.g. prayagraj."
        ),
    )

    parser.add_argument(
        "--observation",
        required=True,
        help=(
            "Observation label, e.g. before or after."
        ),
    )

    parser.add_argument(
        "--index-dir",
        required=True,
        help=(
            "Target FAISS index directory."
        ),
    )

    parser.add_argument(
        "--model",
        default=str(
            DEFAULT_MODEL_PATH
        ),
        help=(
            "Path to local RemoteCLIP checkpoint."
        ),
    )

    args = parser.parse_args()

    try:

        result = incremental_ingest(
            image_directory=Path(
                args.input
            ),

            scene_id=args.scene_id,

            observation=args.observation,

            index_directory=Path(
                args.index_dir
            ),

            model_path=Path(
                args.model
            ),
        )

    except Exception as error:

        print()
        print("=" * 70)
        print("INGESTION FAILED")
        print("=" * 70)

        print(
            str(error)
        )

        return 1

    print()
    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )