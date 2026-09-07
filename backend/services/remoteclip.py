from pathlib import Path

import torch
import open_clip
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "remoteclip"
    / "RemoteCLIP-ViT-B-32.pt"
)


class RemoteCLIPEncoder:
    """
    Local RemoteCLIP encoder for ORION.

    Supports:
    - satellite image/tile -> 512-dimensional embedding
    - text query -> 512-dimensional embedding

    Both embeddings are normalized and live in the
    same vector space.
    """

    def __init__(self, device=None):
        self.device = device or (
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"RemoteCLIP checkpoint not found:\n{MODEL_PATH}"
            )

        print(f"Loading RemoteCLIP on {self.device}...")

        # Create the ViT-B/32 architecture without
        # downloading ordinary CLIP weights.
        self.model, _, self.preprocess = (
            open_clip.create_model_and_transforms(
                "ViT-B-32",
                pretrained=None
            )
        )

        self.tokenizer = open_clip.get_tokenizer(
            "ViT-B-32"
        )

        print("Loading RemoteCLIP checkpoint...")

        checkpoint = torch.load(
            MODEL_PATH,
            map_location="cpu",
            weights_only=True
        )

        self.model.load_state_dict(
            checkpoint,
            strict=True
        )

        self.model = self.model.to(self.device)
        self.model.eval()

        print("RemoteCLIP loaded successfully.")

    @torch.inference_mode()
    def encode_image(self, image):
        """
        Encode one PIL image into a normalized 512-D vector.
        """

        if not isinstance(image, Image.Image):
            raise TypeError(
                "encode_image expects a PIL.Image.Image"
            )

        image = image.convert("RGB")

        tensor = self.preprocess(image).unsqueeze(0)
        tensor = tensor.to(self.device)

        features = self.model.encode_image(tensor)

        features = features / features.norm(
            dim=-1,
            keepdim=True
        )

        return features.squeeze(0).cpu()

    @torch.inference_mode()
    def encode_images(self, images, batch_size=16):
        """
        Encode multiple PIL images.

        Returns:
            Tensor with shape [number_of_images, 512]
        """

        if not images:
            return torch.empty((0, 512))

        results = []

        for start in range(0, len(images), batch_size):
            batch_images = images[
                start:start + batch_size
            ]

            tensors = torch.stack(
                [
                    self.preprocess(
                        image.convert("RGB")
                    )
                    for image in batch_images
                ]
            )

            tensors = tensors.to(self.device)

            features = self.model.encode_image(
                tensors
            )

            features = features / features.norm(
                dim=-1,
                keepdim=True
            )

            results.append(features.cpu())

        return torch.cat(results, dim=0)

    @torch.inference_mode()
    def encode_text(self, text):
        """
        Encode one text query into a normalized 512-D vector.
        """

        if not isinstance(text, str):
            raise TypeError(
                "encode_text expects a string"
            )

        tokens = self.tokenizer([text]).to(
            self.device
        )

        features = self.model.encode_text(tokens)

        features = features / features.norm(
            dim=-1,
            keepdim=True
        )

        return features.squeeze(0).cpu()


def load_remoteclip():
    """
    Convenience function for ORION services.
    """

    return RemoteCLIPEncoder()