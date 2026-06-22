class CidCounter:
    """
    A counter node that increments, decrements, or resets a value.
    """
    def __init__(self):
        self.counter = None

    @classmethod
    def INPUT_TYPES(cls):
        """
        Input Types
        """
        return {
            "required": {
                "initial_value": ("INT", {"default": 0, "min": -1000000, "max": 1000000}),
                "increment": ("BOOLEAN", {"default": False}),
                "decrement": ("BOOLEAN", {"default": False}),
                "reset": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("INT",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Util"

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        return float("NaN")

    def main(self, initial_value, increment, decrement, reset):
        if self.counter is None:
            self.counter = initial_value

        if reset:
            self.counter = initial_value
        else:
            if increment:
                self.counter += 1
            if decrement:
                self.counter -= 1

        return (self.counter,)
