from ..utils import any_type


class CidAnyList:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "item_1": (any_type, {"forceInput": True, "tooltip": "First item in the list"})
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("list",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Collections"
    
    def main(self, **kwargs):
        # Collect all items from the inputs
        items = []
        for i in range(1, 21):  # Support up to 20 inputs
            key = f"item_{i}"
            if key in kwargs and kwargs[key] is not None:
                items.append(kwargs[key])
        
        return (items,)
