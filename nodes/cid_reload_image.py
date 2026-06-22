import os
import tempfile
import numpy as np
from PIL import Image
import torch


class CidReloadImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", ),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Util"

    def main(self, image):
        if image is None:
            raise ValueError("Input image cannot be None")

        batch_size, height, width, channels = image.shape
        reloaded_images = []

        # Process each image in the batch
        for i in range(batch_size):
            img_tensor = image[i:i+1, :, :, :] # Keep the batch dimension for consistency

            # Convert tensor to PIL Image
            img_np = np.clip(255. * img_tensor.cpu().numpy(), 0, 255).astype(np.uint8)
            # Squeeze the batch dimension if it's 1, before converting to PIL
            if img_np.shape[0] == 1:
                pil_image = Image.fromarray(img_np[0])
            else:
                # This case shouldn't happen if we process one by one, but handle defensively
                pil_image = Image.fromarray(img_np) 

            # Save to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_filename = temp_file.name
                try:
                    pil_image.save(temp_filename, format='PNG', compress_level=1)
                except Exception as e:
                    # Clean up temp file on error
                    os.unlink(temp_filename)
                    raise IOError(f"Failed to save temporary image: {e}")

            # Load from the temporary file
            try:
                loaded_pil_image = Image.open(temp_filename)
                # Convert back to numpy array and add batch dimension
                loaded_np = np.array(loaded_pil_image).astype(np.float32) / 255.0
                loaded_np = loaded_np[np.newaxis, :, :, :] # Add batch dimension back
            except Exception as e:
                raise IOError(f"Failed to load temporary image: {e}")
            finally:
                # Ensure temporary file is deleted
                os.unlink(temp_filename)

            # Convert back to tensor
            reloaded_tensor = torch.from_numpy(loaded_np)
            reloaded_images.append(reloaded_tensor)

        # Concatenate the reloaded images along the batch dimension
        final_tensor = torch.cat(reloaded_images, dim=0)

        # Ensure the output tensor has the same shape as the input
        if final_tensor.shape != image.shape:
             # This might happen if the image format changes during save/load (e.g., alpha channel)
             # Let's try to adjust the channels if possible
             if final_tensor.shape[0:3] == image.shape[0:3]: # Check if only channels differ
                 if image.shape[3] == 3 and final_tensor.shape[3] == 4: # Input RGB, Output RGBA
                     final_tensor = final_tensor[:, :, :, :3] # Take only RGB
                 elif image.shape[3] == 4 and final_tensor.shape[3] == 3: # Input RGBA, Output RGB
                     # Need to add an alpha channel, default to fully opaque
                     alpha_channel = torch.ones_like(final_tensor[:, :, :, :1])
                     final_tensor = torch.cat((final_tensor, alpha_channel), dim=3)
                 else: # Other mismatch, raise error
                    raise ValueError(f"Shape mismatch after reload: Input {image.shape}, Output {final_tensor.shape}")
             else: # Dimensions other than channels mismatch
                 raise ValueError(f"Shape mismatch after reload: Input {image.shape}, Output {final_tensor.shape}")


        return (final_tensor,)
