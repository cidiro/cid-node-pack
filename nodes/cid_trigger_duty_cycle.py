class CidTriggerDutyCycle:
    """
    A node that activates a trigger for N executions, then deactivates it for N executions, and repeats.
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
                "on_count": ("INT", {"default": 10, "min": 1, "max": 1000000, "tooltip": "Number of consecutive executions the trigger stays active (True)."}),
                "off_count": ("INT", {"default": 10, "min": 1, "max": 1000000, "tooltip": "Number of consecutive executions the trigger stays inactive (False)."}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "INT",)
    RETURN_NAMES = ("trigger", "count",)
    OUTPUT_TOOLTIPS = (
        "True during the active phase, False during the inactive phase.",
        "Current position within the full on+off cycle (resets to 0 at end of cycle).",
    )
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Util"
    DESCRIPTION = "Activates a trigger for a configurable number of executions, then deactivates it for another configurable number, and repeats. Useful for duty-cycle patterns across workflow runs."

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        return float("NaN")

    def main(self, on_count, off_count):
        trigger = self.counter < on_count
        self.counter += 1
        if self.counter >= on_count + off_count:
            self.counter = 0
        return (trigger, self.counter,)
