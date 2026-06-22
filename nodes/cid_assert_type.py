import torch

from ..utils import any_type


ASSERT_TYPES = (
    "STRING",
    "INT",
    "FLOAT",
    "BOOLEAN",
    "IMAGE",
    "MASK",
    "LATENT",
    "MODEL",
    "CLIP",
    "VAE",
    "CONDITIONING",
)


class CidAssertType:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": (any_type, {"forceInput": True, "tooltip": "Input value to validate and pass through"}),
                "assert_type": (
                    list(ASSERT_TYPES),
                    {
                        "default": "STRING",
                        "tooltip": "Expected type for the input value. The output slot type follows this selection.",
                    },
                ),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("value",)
    OUTPUT_TOOLTIPS = ("Input value, passed through only when it matches the selected assert type.",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Util"
    DESCRIPTION = "Validates that an incoming value matches a selected concrete type, then passes it through unchanged."

    def _is_string(self, value):
        return isinstance(value, str)

    def _is_int(self, value):
        return isinstance(value, int) and not isinstance(value, bool)

    def _is_float(self, value):
        return isinstance(value, float) and not isinstance(value, bool)

    def _is_boolean(self, value):
        return isinstance(value, bool)

    def _is_image(self, value):
        return isinstance(value, torch.Tensor) and value.ndim == 4

    def _is_mask(self, value):
        return isinstance(value, torch.Tensor) and value.ndim == 3

    def _is_latent(self, value):
        return (
            isinstance(value, dict)
            and "samples" in value
            and isinstance(value["samples"], torch.Tensor)
        )

    def _is_model(self, value):
        class_name = value.__class__.__name__.lower()
        has_model_methods = hasattr(value, "model") or hasattr(value, "get_model_object")
        return "model" in class_name or has_model_methods

    def _is_clip(self, value):
        class_name = value.__class__.__name__.lower()
        has_clip_methods = hasattr(value, "tokenize") and hasattr(value, "encode_from_tokens")
        return "clip" in class_name or has_clip_methods

    def _is_vae(self, value):
        class_name = value.__class__.__name__.lower()
        has_vae_methods = hasattr(value, "decode") and hasattr(value, "encode")
        return "vae" in class_name or has_vae_methods

    def _is_conditioning(self, value):
        if not isinstance(value, list):
            return False
        if len(value) == 0:
            return True

        first = value[0]
        if not isinstance(first, (list, tuple)) or len(first) < 2:
            return False

        embedding, meta = first[0], first[1]
        return isinstance(embedding, torch.Tensor) and isinstance(meta, dict)

    def _describe_value(self, value):
        if isinstance(value, torch.Tensor):
            return f"Tensor(shape={tuple(value.shape)}, dtype={value.dtype})"

        if isinstance(value, dict):
            keys = list(value.keys())
            return f"dict(keys={keys[:5]})"

        if isinstance(value, list):
            return f"list(len={len(value)})"

        return type(value).__name__

    def _matches_asserted_type(self, value, assert_type):
        validators = {
            "STRING": self._is_string,
            "INT": self._is_int,
            "FLOAT": self._is_float,
            "BOOLEAN": self._is_boolean,
            "IMAGE": self._is_image,
            "MASK": self._is_mask,
            "LATENT": self._is_latent,
            "MODEL": self._is_model,
            "CLIP": self._is_clip,
            "VAE": self._is_vae,
            "CONDITIONING": self._is_conditioning,
        }

        checker = validators.get(assert_type)
        if checker is None:
            return False

        return checker(value)

    def main(self, value, assert_type):
        if not self._matches_asserted_type(value, assert_type):
            actual = self._describe_value(value)
            raise ValueError(
                f"[CidAssertType] Type assertion failed: expected '{assert_type}', got '{actual}'"
            )

        return (value,)
