import ast


class CidStringListAdd:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_value": ("STRING", {"default": ""}),
            },
            "optional": {
                "list_str": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("STRING", )
    RETURN_NAMES = ("list_str", )
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/String"

    def main(self, string_value, list_str="[]"):
        try:
            string_list = ast.literal_eval(list_str)
        except (ValueError, SyntaxError):
            raise ValueError(f"Invalid list format for list_str: {list_str}")

        if not isinstance(string_list, list):
            raise TypeError(f"list_str should be a list, but got {type(string_list).__name__}")

        if not all(isinstance(item, str) for item in string_list):
            raise TypeError("All items in list_str must be strings.")

        if string_value:
            string_list.append(string_value)

        return (str(string_list),)
