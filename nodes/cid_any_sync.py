from ..utils.any_type import any_type

class CidAnySync:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_1": (any_type, {"forceInput": True, "tooltip": "Input of any type"})
            }
        }

    RETURN_TYPES = tuple(any_type for _ in range(10))
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Util"

    def main(self, **kwargs):
        outputs = []
        for i in range(1, 11):
            key = f"input_{i}"
            outputs.append(kwargs.get(key, None))
        return tuple(outputs)
