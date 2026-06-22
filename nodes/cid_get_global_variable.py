from ..utils import any_type
from ..utils import global_variables

OUTPUT_TYPE_MAP = {
    "*": any_type,
    "STRING": "STRING",
    "INT": "INT",
    "FLOAT": "FLOAT",
    "BOOLEAN": "BOOLEAN",
    "IMAGE": "IMAGE",
    "MASK": "MASK",
    "LATENT": "LATENT",
    "MODEL": "MODEL",
    "CLIP": "CLIP",
    "VAE": "VAE",
    "CONDITIONING": "CONDITIONING",
}


class CidGetGlobalVariable:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key": ("STRING", {"default": ""}),
                "output_type": (list(OUTPUT_TYPE_MAP.keys()), {"default": "*"}),
            },
            "optional": {
                "default_value": (any_type,),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("value",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Util"
    OUTPUT_NODE = False
    
    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        return float("NaN")

    @classmethod
    def VALIDATE_INPUTS(cls, key, output_type, default_value=None):
        return True

    def main(self, key, output_type="*", default_value=None):
        if not key:
            raise ValueError("CidGetGlobalVariable: 'key' cannot be empty")
        value = global_variables.get(key, default_value)
        return (value,)
