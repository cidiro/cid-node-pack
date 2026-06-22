import os

class CidGetFileExtension:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("file_extension",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Path"

    def main(self, file_path):
        _, file_extension = os.path.splitext(file_path)
        return (file_extension,)
