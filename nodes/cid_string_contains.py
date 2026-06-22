class CidStringContains:
    """
    Checks if an input string contains any of the provided values.
    The `values` widget takes a comma-separated list of strings.
    e.g., "value1, value2, value3"
    If any of these values are found in the source string, the node returns True.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source": ("STRING", {"forceInput": True}),
                "values": ("STRING", {"default": "", "tooltip": "Comma-separated list of values to check for in the input string."}),
                "case_sensitive": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("BOOLEAN",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/String"

    def main(self, source, values, case_sensitive):
        if not source or not values:
            return (False,)

        value_list = [v.strip() for v in values.split(',')]

        if not case_sensitive:
            source = source.lower()
            value_list = [v.lower() for v in value_list]
                
        for value in value_list:
            if value and value in source:
                return (True,)

        return (False,)
