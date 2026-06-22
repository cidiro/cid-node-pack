class CidTriggerEveryN:
    """
    A node that outputs a trigger every N workflow executions.
    """
    def __init__(self):
        self.counter = 0

    @classmethod
    def INPUT_TYPES(cls):
        """
        Input Types
        """
        return {
            "required": {
                "n": ("INT", {"default": 10, "min": 1, "max": 1000000, "tooltip": "Number of executions between each trigger."}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "INT",)
    RETURN_NAMES = ("trigger", "count",)
    OUTPUT_TOOLTIPS = (
        "True on every Nth execution, False otherwise.",
        "Current execution count (resets to 0 when trigger fires).",
    )
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Util"
    DESCRIPTION = "Outputs a trigger every N workflow executions. Uses internal state to count executions and automatically resets after each trigger."

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        return float("NaN")

    def main(self, n):
        self.counter += 1
        trigger = self.counter >= n
        if trigger:
            self.counter = 0
        return (trigger, self.counter,)
