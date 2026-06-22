import torch
import comfy.utils


class CidApplyMask:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Mask"

    def main(self, image, mask):
        # Normalize image to [B,H,W,C]
        if image.dim() == 3:
            image = image.unsqueeze(0)

        # Normalize mask to [B,H,W]
        if mask.dim() == 2:
            mask = mask.unsqueeze(0)

        img_b, img_h, img_w, img_c = image.shape

        # Resize mask to match image spatial dims if needed
        if mask.shape[1] != img_h or mask.shape[2] != img_w:
            mask_as_image = mask.unsqueeze(1).expand(-1, 3, -1, -1)
            mask = comfy.utils.common_upscale(
                mask_as_image,
                img_w,
                img_h,
                upscale_method='bicubic',
                crop='center',
            )[:, 0, :, :]

        mask = mask.clamp(0.0, 1.0).to(image.dtype).to(image.device)

        # Align batch sizes
        mask_b = mask.shape[0]
        if img_b != mask_b:
            if img_b == 1 and mask_b > 1:
                image = image.expand(mask_b, -1, -1, -1)
                img_b = mask_b
            elif mask_b == 1 and img_b > 1:
                mask = mask.expand(img_b, -1, -1)
                mask_b = img_b
            else:
                n = min(img_b, mask_b)
                image = image[:n]
                mask = mask[:n]

        # Drop existing alpha if present, keep first 3 channels
        if img_c >= 3:
            rgb = image[..., :3]
        else:
            # grayscale or similar: replicate channels to RGB
            rgb = image[..., :1].expand(-1, -1, -1, 3)

        alpha = mask.unsqueeze(-1)
        rgba = torch.cat([rgb, alpha], dim=-1).contiguous()

        return (rgba,)
