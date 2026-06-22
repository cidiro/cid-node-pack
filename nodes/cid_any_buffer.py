from collections import deque
import torch

from ..utils import any_type


class CidAnyBuffer:
    def __init__(self):
        self.buffer_size = 5  # Default buffer size
        self.buffer = deque(maxlen=self.buffer_size)
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "value": (any_type, {"forceInput": True, "tooltip": "Input value to be buffered"}),
                "buffer_size": ("INT", {"default": 5, "min": 1, "max": 20, "step": 1, "tooltip": "Number of values to buffer"})
            }
        }

    RETURN_TYPES = tuple([any_type] * 20)
    RETURN_NAMES = tuple([f"value_{i+1}" for i in range(20)])
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Util"

    def is_image_type(self, value):
        return isinstance(value, torch.Tensor) and (len(value.shape) == 3 or len(value.shape) == 4)

    def is_string_type(self, value):
        return isinstance(value, str)

    def main(self, value, buffer_size):
        is_image = self.is_image_type(value)
        is_string = self.is_string_type(value)
        
        if buffer_size != self.buffer_size:
            self.buffer_size = buffer_size
            new_buffer = deque(maxlen=buffer_size)
            for item in self.buffer:
                new_buffer.append(item)
            self.buffer = new_buffer
        
        self.buffer.appendleft(value)
        
        outputs = []
        for i in range(20):
            if i < len(self.buffer) and i < buffer_size:
                outputs.append(self.buffer[i])
            else:
                if is_image:
                    empty_image = torch.zeros_like(value)
                    outputs.append(empty_image)
                elif is_string:
                    outputs.append("")
                else:
                    outputs.append(None)
        
        return tuple(outputs)
