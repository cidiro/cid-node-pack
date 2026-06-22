from ..utils import any_type


class CidStoreAny:
    def __init__(self):
        self.stored_data = None
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "input": (any_type, {"forceInput": True, "tooltip": "Input of any type"})
            }
        }

    RETURN_TYPES = (any_type,)
    FUNCTION = "store_data"
    CATEGORY = "Cid Node Pack/Util"

    def store_data(self, input=None):
        if input is not None:
            self.stored_data = input

        if self.stored_data is None:
            raise ValueError("[CidStoreAny] No data stored yet")
        
        return (self.stored_data,)
