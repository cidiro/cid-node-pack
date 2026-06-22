from ..utils import any_type


class CidAnyQueue:
    def __init__(self):
        self.queue = []
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_list": (any_type, {"forceInput": True, "tooltip": "List of values to add to the queue"}),
                "consume": ("BOOLEAN", {"default": True, "tooltip": "Whether to consume the item from the queue"}),
            }
        }

    RETURN_TYPES = (any_type, "INT")
    RETURN_NAMES = ("value", "remaining")
    OUTPUT_TOOLTIPS = ("The first item popped from the queue", "The number of items remaining in the queue after popping")
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Util"
    DESCRIPTION = "Stores items in a queue and pops one item per workflow run. Re-executes every run to continuously consume the queue."
    
    @classmethod
    def IS_CHANGED(s, **kwargs):
        return float("NaN")

    def main(self, input_list, consume):
        if input_list is not None:
            if isinstance(input_list, list):
                self.queue.extend(input_list)
            else:
                self.queue.append(input_list)
            
        if len(self.queue) == 0:
            raise ValueError("CidAnyQueue is empty!")
            
        if consume:
            item = self.queue.pop(0)
        else:
            item = self.queue[0]
        
        return (item, len(self.queue))
