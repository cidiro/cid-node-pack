import torch


class CidConcatenateImageBatches:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_a": ("IMAGE",),
                "images_b": ("IMAGE",),
            }
        }
        
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Image"
    
    def main(self, images_a, images_b):
        if images_a.shape[1:] != images_b.shape[1:]:
            raise ValueError(
                f"Cannot combine image batches with different dimensions. "
                f"images_a shape[1:]: {images_a.shape[1:]}, "
                f"images_b shape[1:]: {images_b.shape[1:]}"
            )

        combined_images = torch.cat((images_a, images_b), dim=0)

        return (combined_images,)
