from ..utils import any_type
from ..utils import global_variables


class CidSetGlobalVariable:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": (any_type,),
                "key": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "main"
    OUTPUT_NODE = True
    CATEGORY = "Cid Node Pack/Util"
    
    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        return float("NaN")

    def main(self, value, key):
        if not key:
            raise ValueError("CidSetGlobalVariable: 'key' cannot be empty")
        global_variables[key] = value
        return {}
