
from ..utils import any_type
from ..utils import timers


class CidTimerStart:
    """Mark point A of a measured interval.

    Records a high-resolution timestamp for the given timer id and passes
    its optional input through unchanged, so it can be spliced into a data
    path. Pair it with a downstream CidTimerStop that uses the same ``id``;
    the elapsed wall-clock time between the two nodes' executions is what
    gets measured.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "id": (
                    "STRING",
                    {
                        "default": "default",
                        "tooltip": "Id shared with the matching CidTimerStop "
                        "(use a unique id per timer in a workflow)",
                    },
                ),
            },
            "optional": {
                "passthrough": (
                    any_type,
                    {"forceInput": True, "tooltip": "Value to pass through unchanged"},
                ),
            },
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("passthrough",)
    FUNCTION = "main"
    OUTPUT_NODE = True
    CATEGORY = "Cid Node Pack/Util"

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        # Always re-stamp on every queue run, even when inputs are unchanged
        return float("NaN")

    def main(self, id, passthrough=None):
        if not id:
            raise ValueError("CidTimerStart: 'id' cannot be empty")
        timers.start_timer(id)
        # The ui payload lets the frontend switch paired CidTimerStop nodes
        # to their live "running" display.
        return {"ui": {"timer_started": [id]}, "result": (passthrough,)}
