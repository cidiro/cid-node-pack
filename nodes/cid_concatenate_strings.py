class CidConcatenateStrings:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_1": ("STRING", {"forceInput": True, "tooltip": "String input 1"})
            },
            "optional": {
                "separator": ("STRING", {"default": "", "multiline": False, "tooltip": "Separator between strings"})
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/String"

    def _process_special_chars(self, text):
        """Process escape sequences in the input text."""
        return text.encode().decode('unicode_escape')

    def main(self, **kwargs):
        separator = kwargs.get("separator", "")
        # Process special characters in separator
        separator = self._process_special_chars(separator)
        
        # Collect all string inputs
        strings = []
        for i in range(1, 21):  # Support up to 20 inputs
            key = f"string_{i}"
            if key in kwargs and kwargs[key] is not None:
                strings.append(kwargs[key])
        
        # Concatenate with separator
        result = separator.join(strings)
        
        return (result,)
