import os

class CidGetFileName:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("file_name",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Path"

    def main(self, file_path):
        base_name = os.path.basename(file_path)
        file_name, _ = os.path.splitext(base_name)
        return (file_name,)
