import hashlib
from ..utils import any_type


class CidBooleanMultiplexer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "on_true": (any_type,),
                "on_false": (any_type,),
                "select": ("BOOLEAN", {"default": True, "label_on": "true", "label_off": "false"}),
            }
        }

    RETURN_TYPES = (any_type,)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Control Flow"
    
    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Create a hash of all inputs to determine if node needs to be re-executed
        hash_input = str(kwargs.get('select', True))
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def main(self, on_true, on_false, select):
        if select:
            return (on_true,)
        else:
            return (on_false,)
