import logging

from ..utils import any_type
from ..utils import duration
from ..utils import timers

logger = logging.getLogger("cid_node_pack")

class CidTimerStop:
    """Mark point B of a measured interval and report the elapsed time.

    Reads the start stamp recorded by a CidTimerStart with the same
    ``timer_name`` and returns the elapsed seconds as a FLOAT and a formatted
    STRING, while passing its optional input through unchanged. The elapsed
    time is also printed to the ComfyUI console and drawn as a retro digital
    clock on the node itself.

    The start stamp is kept after reading, so several stops can measure
    against one start (split timing).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "timer_name": (
                    "STRING",
                    {
                        "default": "default",
                        "tooltip": "Name of the CidTimerStart to measure from",
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

    RETURN_TYPES = (any_type, "FLOAT", "STRING")
    RETURN_NAMES = ("output", "seconds", "text")
    FUNCTION = "main"
    OUTPUT_NODE = True
    CATEGORY = "Cid Node Pack/Util"

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        # Always re-measure on every queue run, even when inputs are unchanged
        return float("NaN")

    def main(self, timer_name, input=None):
        if not timer_name:
            raise ValueError("CidTimerStop: 'timer_name' cannot be empty")
        elapsed = timers.stop_timer(timer_name)
        text = duration.format_duration(elapsed)
        # print() rather than logging: ComfyUI filters INFO records from
        # custom-node loggers, and the console line is meant to be copyable
        print(f"CidTimerStop [{timer_name}] {text} ({elapsed:.4f} s)", flush=True)
        return {
            "ui": {"text": [text], "elapsed": [elapsed]},
            "result": (input, elapsed, text),
        }
