import os

class CidGetDirectoryName:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("directory_name",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Path"

    def main(self, file_path):
        directory_name = os.path.dirname(file_path)
        return (directory_name,)
