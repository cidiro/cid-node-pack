
from ..utils import any_type
from ..utils import duration
from ..utils import timers


class CidTimerStop:
    """Mark point B of a measured interval and report the elapsed time.

    Reads the start stamp recorded by a CidTimerStart with the same ``id``
    and passes its optional input through unchanged. The elapsed time is
    drawn as a retro digital clock on the node itself and printed to the
    ComfyUI console (copyable, with raw seconds).

    The start stamp is kept after reading, so several stops can measure
    against one start (split timing).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "id": (
                    "STRING",
                    {
                        "default": "default",
                        "tooltip": "Id of the CidTimerStart to measure from",
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
        # Always re-measure on every queue run, even when inputs are unchanged
        return float("NaN")

    def main(self, id, passthrough=None):
        if not id:
            raise ValueError("CidTimerStop: 'id' cannot be empty")
        elapsed = timers.stop_timer(id)
        text = duration.format_duration(elapsed)
        # print() rather than logging: ComfyUI filters INFO records from
        # custom-node loggers, and the console line is meant to be copyable
        print(f"CidTimerStop [{id}] {text} ({elapsed:.4f} s)", flush=True)
        return {
            "ui": {"text": [text], "elapsed": [elapsed]},
            "result": (passthrough,),
        }
