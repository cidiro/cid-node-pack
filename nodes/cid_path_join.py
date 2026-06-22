import os

class CidPathJoin:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path_a": ("STRING", {"default": ""}),
                "path_b": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("joined_path",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Path"

    def main(self, path_a, path_b):
        joined_path = os.path.join(path_a, path_b)
        return (joined_path,)
