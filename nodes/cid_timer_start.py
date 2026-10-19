import logging

from ..utils import any_type
from ..utils import timers

logger = logging.getLogger("cid_node_pack")


class CidTimerStart:
    """Mark point A of a measured interval.

    Records a high-resolution timestamp for the given timer name and passes
    its optional input through unchanged, so it can be spliced into a data
    path. Pair it with a downstream CidTimerStop that uses the same
    ``timer_name``; the elapsed wall-clock time between the two nodes'
    executions is what gets measured.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "timer_name": (
                    "STRING",
                    {
                        "default": "default",
                        "tooltip": "Name shared with the matching CidTimerStop "
                        "(use a unique name per timer in a workflow)",
                    },
                ),
            },
            "optional": {
                "input": (
                    any_type,
                    {"forceInput": True, "tooltip": "Value to pass through unchanged"},
                ),
            },
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "main"
    OUTPUT_NODE = True
    CATEGORY = "Cid Node Pack/Util"

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        # Always re-stamp on every queue run, even when inputs are unchanged
        return float("NaN")

    def main(self, timer_name, input=None):
        if not timer_name:
            raise ValueError("CidTimerStart: 'timer_name' cannot be empty")
        timers.start_timer(timer_name)
        # The ui payload lets the frontend switch paired CidTimerStop nodes
        # to their live "running" display.
        return {"ui": {"timer_started": [timer_name]}, "result": (input,)}
