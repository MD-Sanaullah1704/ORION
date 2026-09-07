from pathlib import Path
import json
import re

import faiss
import numpy as np
from PIL import Image

from backend.services.remoteclip import RemoteCLIPEncoder


# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ORION combined production search index.
#
# This contains:
# - 121 Prayagraj BEFORE vectors
# - 121 Prayagraj AFTER vectors
# - 1 Jewar BEFORE vector
# - 1 Jewar AFTER vector
#
# Total = 244 vectors
DEFAULT_INDEX_DIR = (
    PROJECT_ROOT
    / "data"
    / "indexes"
    / "orion_combined"
)


# ==========================================================
# QUERY INTENT DEFINITIONS
# ==========================================================

QUERY_INTENTS = {
    "road_development": {
        "keywords": {
            "road": 1.0,
            "roads": 1.0,
            "roadway": 1.0,
            "highway": 1.0,
            "highways": 1.0,
            "street": 0.8,
            "streets": 0.8,
            "transport": 0.7,
            "transportation": 0.7,
            "roadwork": 1.0,
            "roadworks": 1.0,
            "road development": 1.0,
        },
        "metadata_terms": {
            "road development": 1.0,
            "road development": 1.0,
            "roads": 0.9,
            "road": 0.9,
            "infrastructure": 0.7,
            "development": 0.6,
            "airport construction": 0.4,
        },
    },

    "construction": {
        "keywords": {
            "construction": 1.0,
            "construct": 0.9,
            "constructed": 0.9,
            "building": 0.8,
            "buildings": 0.8,
            "development": 0.7,
            "construction site": 1.0,
            "construction activity": 1.0,
            "infrastructure": 0.8,
            "infrastructure development": 0.9,
            "development site": 0.8,
        },
        "metadata_terms": {
            "construction": 1.0,
            "construction activity": 1.0,
            "airport construction": 1.0,
            "infrastructure development": 1.0,
            "development site": 0.9,
            "infrastructure": 0.8,
            "disturbed land": 0.6,
        },
    },

    "airport": {
        "keywords": {
            "airport": 1.0,
            "airports": 1.0,
            "runway": 1.0,
            "runways": 1.0,
            "terminal": 0.9,
            "aviation": 0.9,
            "aerodrome": 1.0,
        },
        "metadata_terms": {
            "airport construction": 1.0,
            "airport": 1.0,
            "runway": 1.0,
            "infrastructure development": 0.8,
            "construction": 0.7,
        },
    },

    "infrastructure": {
        "keywords": {
            "infrastructure": 1.0,
            "development": 0.8,
            "urban": 0.6,
            "expansion": 0.7,
            "infrastructure development": 1.0,
        },
        "metadata_terms": {
            "infrastructure development": 1.0,
            "infrastructure": 1.0,
            "urban expansion": 0.9,
            "development site": 0.8,
            "construction": 0.7,
            "road development": 0.7,
        },
    },

    "vegetation": {
        "keywords": {
            "vegetation": 1.0,
            "green": 0.8,
            "greenery": 0.9,
            "forest": 0.9,
            "forests": 0.9,
            "trees": 0.9,
            "tree": 0.9,
            "vegetated": 1.0,
            "vegetation cover": 1.0,
            "green areas": 1.0,
            "farmland": 0.7,
            "agriculture": 0.7,
            "agricultural": 0.7,
        },
        "metadata_terms": {
            "vegetation": 1.0,
            "green": 0.9,
            "vegetation cover": 1.0,
            "agriculture": 0.7,
            "farmland": 0.7,
        },
    },

    "water": {
        "keywords": {
            "river": 1.0,
            "rivers": 1.0,
            "water": 1.0,
            "waterbody": 1.0,
            "waterbody": 1.0,
            "water body": 1.0,
            "lake": 0.9,
            "lakes": 0.9,
            "pond": 0.8,
            "ponds": 0.8,
            "flood": 1.0,
            "flooding": 1.0,
            "flooded": 1.0,
        },
        "metadata_terms": {
            "river": 1.0,
            "water": 1.0,
            "water body": 1.0,
            "flood": 1.0,
            "flooding": 1.0,
        },
    },

    "temporary_structures": {
        "keywords": {
            "temporary": 0.8,
            "structure": 0.8,
            "structures": 0.8,
            "temporary structure": 1.0,
            "temporary structures": 1.0,
            "tents": 1.0,
            "tent": 1.0,
            "camp": 0.8,
            "camps": 0.8,
        },
        "metadata_terms": {
            "temporary structures": 1.0,
            "temporary structure": 1.0,
            "structures": 0.8,
            "camp": 0.7,
            "tents": 0.8,
        },
    },

    "urban_development": {
        "keywords": {
            "urban": 1.0,
            "urban development": 1.0,
            "urban expansion": 1.0,
            "city": 0.8,
            "development": 0.8,
            "built-up": 1.0,
            "builtup": 1.0,
            "built up": 1.0,
        },
        "metadata_terms": {
            "urban expansion": 1.0,
            "urban development": 1.0,
            "development": 0.8,
            "infrastructure development": 0.8,
            "construction": 0.7,
        },
    },
}


# ==========================================================
# SEMANTIC SEARCH SERVICE
# ==========================================================

class SemanticSearchService:
    """
    ORION semantic retrieval service.

    Supports:

    1. Text -> satellite imagery retrieval
    2. Image -> satellite imagery retrieval

    Text retrieval uses a hybrid ranking strategy:

        RemoteCLIP semantic similarity
                    +
        metadata / query-intent relevance

    This allows domain-specific imagery such as
    Jewar airport construction imagery to rank higher
    for queries like:

        "road development"
        "airport construction"
        "infrastructure development"

    while preserving the original FAISS similarity score.

    The service loads a FAISS index together with its
    aligned metadata records.

    Default index:
        data/indexes/orion_combined

    The combined index contains imagery from:
        - Prayagraj
        - Jewar / Noida International Airport area
    """

    def __init__(
        self,
        index_dir=None
    ):
        print("Initializing semantic search service...")

        if index_dir is None:
            index_dir = DEFAULT_INDEX_DIR

        self.index_dir = Path(index_dir)

        if not self.index_dir.is_absolute():
            self.index_dir = (
                PROJECT_ROOT
                / self.index_dir
            )

        self.index_path = (
            self.index_dir
            / "index.faiss"
        )

        self.metadata_path = (
            self.index_dir
            / "metadata.json"
        )

        print(
            f"Index directory:\n"
            f"{self.index_dir}"
        )

        if not self.index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found:\n"
                f"{self.index_path}"
            )

        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found:\n"
                f"{self.metadata_path}"
            )

        # --------------------------------------------------
        # LOAD FAISS INDEX
        # --------------------------------------------------

        print("Loading FAISS index...")

        self.index = faiss.read_index(
            str(self.index_path)
        )

        print(
            f"FAISS vectors loaded: "
            f"{self.index.ntotal}"
        )

        # --------------------------------------------------
        # LOAD METADATA
        # --------------------------------------------------

        with open(
            self.metadata_path,
            "r",
            encoding="utf-8"
        ) as file:
            self.metadata = json.load(file)

        if len(self.metadata) != self.index.ntotal:
            raise ValueError(
                "FAISS index and metadata count "
                "do not match."
            )

        print(
            f"Metadata records loaded: "
            f"{len(self.metadata)}"
        )

        # --------------------------------------------------
        # DATASET SUMMARY
        # --------------------------------------------------

        self.dataset_counts = {}

        for tile in self.metadata:
            dataset = tile.get(
                "dataset",
                tile.get(
                    "scene_id",
                    "unknown"
                )
            )

            self.dataset_counts[dataset] = (
                self.dataset_counts.get(
                    dataset,
                    0
                ) + 1
            )

        print("Indexed datasets:")

        for dataset, count in (
            self.dataset_counts.items()
        ):
            print(
                f"  {dataset}: {count}"
            )

        # --------------------------------------------------
        # LOAD REMOTECLIP
        # --------------------------------------------------

        print("Loading RemoteCLIP...")

        self.encoder = RemoteCLIPEncoder()

        print(
            "Semantic search service ready."
        )

    # ======================================================
    # QUERY INTENT DETECTION
    # ======================================================

    def _normalize_text(
        self,
        value
    ):
        """
        Normalize text for metadata matching.
        """

        if value is None:
            return ""

        if isinstance(value, (list, tuple, set)):
            value = " ".join(
                str(item)
                for item in value
            )

        value = str(value).lower()

        value = re.sub(
            r"[_/,-]+",
            " ",
            value
        )

        value = re.sub(
            r"\s+",
            " ",
            value
        )

        return value.strip()

    def _tokenize(
        self,
        text
    ):
        """
        Convert text into simple lowercase tokens.
        """

        text = self._normalize_text(text)

        return set(
            re.findall(
                r"[a-z0-9]+",
                text
            )
        )

    def _detect_query_intents(
        self,
        query
    ):
        """
        Detect domain-specific intents from a
        natural-language query.

        Returns a dictionary such as:

            {
                "road_development": 1.0,
                "construction": 0.4
            }
        """

        normalized_query = self._normalize_text(
            query
        )

        query_tokens = self._tokenize(
            normalized_query
        )

        detected = {}

        for intent_name, intent_data in (
            QUERY_INTENTS.items()
        ):
            keywords = intent_data.get(
                "keywords",
                {}
            )

            score = 0.0
            matched = 0.0

            for keyword, weight in keywords.items():

                normalized_keyword = (
                    self._normalize_text(
                        keyword
                    )
                )

                if " " in normalized_keyword:
                    if normalized_keyword in normalized_query:
                        score += float(weight)
                        matched += float(weight)

                else:
                    if normalized_keyword in query_tokens:
                        score += float(weight)
                        matched += float(weight)

            if score > 0:
                detected[intent_name] = min(
                    1.0,
                    score
                )

        return detected

    # ======================================================
    # METADATA TEXT EXTRACTION
    # ======================================================

    def _metadata_text(
        self,
        tile
    ):
        """
        Combine searchable metadata fields into
        one normalized text representation.
        """

        fields = [
            tile.get("dataset"),
            tile.get("location"),
            tile.get("scene_id"),
            tile.get("observation"),
            tile.get("sensor"),
            tile.get("platform"),
            tile.get("product"),
            tile.get("image_role"),
            tile.get("filename"),
            tile.get("source_raster"),
            tile.get("change_type"),
            tile.get("description"),
            tile.get("title"),
        ]

        query_tags = tile.get(
            "query_tags",
            []
        )

        if isinstance(
            query_tags,
            list
        ):
            fields.extend(query_tags)
        else:
            fields.append(query_tags)

        return self._normalize_text(
            " ".join(
                str(field)
                for field in fields
                if field is not None
            )
        )

    # ======================================================
    # METADATA RELEVANCE
    # ======================================================

    def _metadata_relevance(
        self,
        query,
        tile,
        detected_intents=None
    ):
        """
        Calculate metadata relevance between a query
        and a metadata record.

        Score range:
            0.0 -> no metadata evidence
            1.0 -> strong metadata evidence

        Metadata is intentionally used as a reranking
        signal rather than replacing RemoteCLIP.
        """

        if detected_intents is None:
            detected_intents = (
                self._detect_query_intents(
                    query
                )
            )

        if not detected_intents:
            return 0.0

        metadata_text = self._metadata_text(
            tile
        )

        if not metadata_text:
            return 0.0

        metadata_tokens = self._tokenize(
            metadata_text
        )

        normalized_metadata = (
            self._normalize_text(
                metadata_text
            )
        )

        intent_scores = []

        for intent_name, intent_strength in (
            detected_intents.items()
        ):
            intent_data = QUERY_INTENTS.get(
                intent_name,
                {}
            )

            metadata_terms = intent_data.get(
                "metadata_terms",
                {}
            )

            if not metadata_terms:
                continue

            intent_score = 0.0
            intent_weight = 0.0

            for term, weight in metadata_terms.items():

                normalized_term = (
                    self._normalize_text(
                        term
                    )
                )

                matched = False

                if " " in normalized_term:
                    if normalized_term in normalized_metadata:
                        matched = True
                else:
                    if normalized_term in metadata_tokens:
                        matched = True

                if matched:
                    intent_score += float(weight)
                    intent_weight += float(weight)

            if intent_weight > 0:
                normalized_intent_score = min(
                    1.0,
                    intent_score / intent_weight
                )

                intent_scores.append(
                    normalized_intent_score
                    * float(intent_strength)
                )

        if not intent_scores:
            return 0.0

        return min(
            1.0,
            max(intent_scores)
        )

    # ======================================================
    # HYBRID RERANKING
    # ======================================================

    def _calculate_rerank_score(
        self,
        semantic_score,
        metadata_score,
        query_has_intent
    ):
        """
        Combine RemoteCLIP similarity and metadata
        relevance.

        Normal semantic query:
            80% semantic
            20% metadata

        Strong domain-specific query:
            45% semantic
            55% metadata

        This prevents metadata from completely
        overpowering visual-semantic retrieval.
        """

        semantic_score = float(
            semantic_score
        )

        metadata_score = float(
            metadata_score
        )

        if query_has_intent:
            semantic_weight = 0.45
            metadata_weight = 0.55
        else:
            semantic_weight = 0.80
            metadata_weight = 0.20

        rerank_score = (
            semantic_weight
            * semantic_score
            +
            metadata_weight
            * metadata_score
        )

        return float(
            max(
                0.0,
                min(
                    1.0,
                    rerank_score
                )
            )
        )

    # ======================================================
    # TEXT SEARCH
    # ======================================================

    def search_text(
        self,
        query,
        top_k=5
    ):
        """
        Search satellite imagery using a
        natural-language query.

        Retrieval pipeline:

            Query
              ↓
            RemoteCLIP
              ↓
            FAISS candidate retrieval
              ↓
            Query intent detection
              ↓
            Metadata relevance
              ↓
            Hybrid reranking
              ↓
            Final results
        """

        if not isinstance(
            query,
            str
        ):
            raise TypeError(
                "query must be a string."
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "query cannot be empty."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if self.index.ntotal == 0:
            return {
                "query_type": "text",
                "query": query,
                "count": 0,
                "results": [],
            }

        # --------------------------------------------------
        # RETRIEVE A LARGER CANDIDATE POOL
        # --------------------------------------------------

        candidate_k = min(
            max(
                top_k * 10,
                50
            ),
            self.index.ntotal
        )

        # --------------------------------------------------
        # ENCODE TEXT
        # --------------------------------------------------

        query_embedding = (
            self.encoder.encode_text(
                query
            )
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

        # --------------------------------------------------
        # FAISS SEARCH
        # --------------------------------------------------

        scores, indices = (
            self.index.search(
                query_vector,
                candidate_k
            )
        )

        # --------------------------------------------------
        # DETECT QUERY INTENT
        # --------------------------------------------------

        detected_intents = (
            self._detect_query_intents(
                query
            )
        )

        query_has_intent = bool(
            detected_intents
        )

        if query_has_intent:
            print(
                "Detected query intents:",
                detected_intents
            )

        # --------------------------------------------------
        # BUILD CANDIDATE RESULTS
        # --------------------------------------------------

        candidates = []

        for semantic_score, index_id in zip(
            scores[0],
            indices[0]
        ):

            if index_id < 0:
                continue

            if index_id >= len(
                self.metadata
            ):
                continue

            tile = self.metadata[
                index_id
            ]

            metadata_score = (
                self._metadata_relevance(
                    query,
                    tile,
                    detected_intents
                )
            )

            rerank_score = (
                self._calculate_rerank_score(
                    semantic_score,
                    metadata_score,
                    query_has_intent
                )
            )

            candidates.append(
                {
                    "semantic_score": float(
                        semantic_score
                    ),
                    "metadata_score": float(
                        metadata_score
                    ),
                    "rerank_score": float(
                        rerank_score
                    ),
                    "index_id": int(
                        index_id
                    ),
                    "tile": tile,
                }
            )

        # --------------------------------------------------
        # HYBRID SORT
        # --------------------------------------------------

        candidates.sort(
            key=lambda item: (
                item["rerank_score"],
                item["semantic_score"]
            ),
            reverse=True
        )

        # Keep only requested number of results.
        candidates = candidates[
            :top_k
        ]

        # --------------------------------------------------
        # FORMAT RESULTS
        # --------------------------------------------------

        results = []

        for rank, candidate in enumerate(
            candidates,
            start=1
        ):

            tile = candidate["tile"]

            result = {
                "rank": rank,

                # Original RemoteCLIP / FAISS similarity.
                #
                # IMPORTANT:
                # This remains the original semantic
                # similarity and is NOT probability.
                "score": round(
                    candidate[
                        "semantic_score"
                    ],
                    4
                ),

                # Explicit semantic score.
                "semantic_score": round(
                    candidate[
                        "semantic_score"
                    ],
                    4
                ),

                # Metadata relevance.
                "metadata_score": round(
                    candidate[
                        "metadata_score"
                    ],
                    4
                ),

                # Final hybrid ranking score.
                "rerank_score": round(
                    candidate[
                        "rerank_score"
                    ],
                    4
                ),

                "tile_id": tile.get(
                    "tile_id"
                ),

                "filename": tile.get(
                    "filename"
                ),

                "path": tile.get(
                    "path"
                ),

                "scene_id": tile.get(
                    "scene_id"
                ),

                "observation": tile.get(
                    "observation"
                ),

                "source_raster": tile.get(
                    "source_raster"
                ),

                "tile_size": tile.get(
                    "tile_size"
                ),
            }

            # --------------------------------------------------
            # DATASET METADATA
            # --------------------------------------------------

            optional_fields = [
                "dataset",
                "location",
                "date",
                "before_date",
                "after_date",
                "sensor",
                "platform",
                "product",
                "mgrs_tile",
                "source_crs",
                "pixel_size_m",
                "image_role",
                "query_tags",
                "x",
                "y",
            ]

            for field in optional_fields:

                if field in tile:
                    result[field] = tile[
                        field
                    ]

            # --------------------------------------------------
            # SEARCH EXPLANATION
            # --------------------------------------------------

            if query_has_intent:
                result["ranking_mode"] = (
                    "hybrid_semantic_metadata"
                )
            else:
                result["ranking_mode"] = (
                    "semantic"
                )

            results.append(
                result
            )

        return {
            "query_type": "text",
            "query": query,
            "count": len(results),

            "ranking": {
                "mode": (
                    "hybrid_semantic_metadata"
                    if query_has_intent
                    else "semantic"
                ),
                "semantic_weight": (
                    0.45
                    if query_has_intent
                    else 0.80
                ),
                "metadata_weight": (
                    0.55
                    if query_has_intent
                    else 0.20
                ),
                "detected_intents": (
                    list(
                        detected_intents.keys()
                    )
                ),
            },

            "results": results,
        }

    # ======================================================
    # IMAGE SEARCH
    # ======================================================

    def search_image(
        self,
        image,
        top_k=5
    ):
        """
        Search satellite imagery using a
        reference image.

        Image search remains pure semantic retrieval.
        """

        if not isinstance(
            image,
            Image.Image
        ):
            raise TypeError(
                "image must be a PIL.Image.Image."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if self.index.ntotal == 0:
            return {
                "query_type": "image",
                "count": 0,
                "results": [],
            }

        top_k = min(
            top_k,
            self.index.ntotal
        )

        image = image.convert(
            "RGB"
        )

        # --------------------------------------------------
        # ENCODE IMAGE
        # --------------------------------------------------

        image_embedding = (
            self.encoder.encode_image(
                image
            )
        )

        query_vector = (
            image_embedding
            .numpy()
            .astype(np.float32)
        )

        query_vector = query_vector.reshape(
            1,
            -1
        )

        # --------------------------------------------------
        # FAISS SEARCH
        # --------------------------------------------------

        scores, indices = (
            self.index.search(
                query_vector,
                top_k
            )
        )

        return self._format_results(
            scores[0],
            indices[0],
            query_type="image"
        )

    # ======================================================
    # RESULT FORMATTING
    # ======================================================

    def _format_results(
        self,
        scores,
        indices,
        query_type,
        query=None
    ):
        """
        Convert FAISS results into API-friendly
        dictionaries.

        All available dataset metadata is preserved.
        """

        results = []

        for rank, (
            score,
            index_id
        ) in enumerate(
            zip(
                scores,
                indices
            ),
            start=1
        ):

            if index_id < 0:
                continue

            if index_id >= len(
                self.metadata
            ):
                continue

            tile = self.metadata[
                index_id
            ]

            # --------------------------------------------------
            # CORE SEARCH METADATA
            # --------------------------------------------------

            result = {
                "rank": rank,

                # FAISS similarity score.
                #
                # This is retrieval similarity,
                # NOT probability or accuracy.
                "score": round(
                    float(score),
                    4
                ),

                "semantic_score": round(
                    float(score),
                    4
                ),

                "tile_id": tile.get(
                    "tile_id"
                ),

                "filename": tile.get(
                    "filename"
                ),

                "path": tile.get(
                    "path"
                ),

                "scene_id": tile.get(
                    "scene_id"
                ),

                "observation": tile.get(
                    "observation"
                ),

                "source_raster": tile.get(
                    "source_raster"
                ),

                "tile_size": tile.get(
                    "tile_size"
                ),
            }

            # --------------------------------------------------
            # DATASET METADATA
            # --------------------------------------------------

            optional_fields = [
                "dataset",
                "location",
                "date",
                "before_date",
                "after_date",
                "sensor",
                "platform",
                "product",
                "mgrs_tile",
                "source_crs",
                "pixel_size_m",
                "image_role",
                "query_tags",
                "x",
                "y",
            ]

            for field in optional_fields:

                if field in tile:
                    result[field] = tile[
                        field
                    ]

            results.append(
                result
            )

        response = {
            "query_type": query_type,
            "count": len(results),
            "results": results,
        }

        if query is not None:
            response["query"] = query

        return response


# ==========================================================
# SERVICE LOADER
# ==========================================================

def load_semantic_search(
    index_dir=None
):
    """
    Convenience function for loading ORION's
    semantic search service.

    If index_dir is omitted, the combined
    ORION production index is used.

    A custom index directory can still be supplied
    for testing or future datasets.
    """

    return SemanticSearchService(
        index_dir=index_dir
    )