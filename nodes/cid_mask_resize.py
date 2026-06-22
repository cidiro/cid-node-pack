import torch
import torch.nn.functional as F


class CidMaskResize:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK",),
                "factor": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 16.0,
                    "step": 0.05,
                }),
            },
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Mask"

    def main(self, mask, factor):
        # Normalize to [B, H, W] float
        if mask.dim() == 2:
            mask = mask.unsqueeze(0)
        mask = mask.float()

        # Fast path: identity
        if abs(factor - 1.0) < 1e-6:
            return (mask.clamp(0.0, 1.0),)

        # Fully shrunk: return zeros
        if factor < 1e-6:
            return (torch.zeros_like(mask),)

        b, h, w = mask.shape
        device = mask.device
        dtype = mask.dtype

        # Promote to [B, 1, H, W] for grid_sample
        m4 = mask.unsqueeze(1)

        # Compute per-mask centroid (cy, cx) in pixel coords, weighted by mask values
        ys = torch.arange(h, device=device, dtype=dtype).view(1, h, 1)
        xs = torch.arange(w, device=device, dtype=dtype).view(1, 1, w)
        total = mask.sum(dim=(1, 2))  # [B]
        has_weight = total > 0
        safe_total = torch.where(has_weight, total, torch.ones_like(total))
        cy_px = (mask * ys).sum(dim=(1, 2)) / safe_total
        cx_px = (mask * xs).sum(dim=(1, 2)) / safe_total
        # Empty masks: fall back to geometric center
        center_y = torch.full_like(cy_px, (h - 1) / 2.0)
        center_x = torch.full_like(cx_px, (w - 1) / 2.0)
        cy_px = torch.where(has_weight, cy_px, center_y)
        cx_px = torch.where(has_weight, cx_px, center_x)

        # Convert centroids to normalized coords in [-1, 1] (align_corners=True convention,
        # which matches our explicit normalization below for affine_grid).
        cx_n = 2.0 * cx_px / max(w - 1, 1) - 1.0
        cy_n = 2.0 * cy_px / max(h - 1, 1) - 1.0

        # Inverse affine: sample input at (p - c) / f + c = p/f + c*(1 - 1/f)
        inv_f = 1.0 / factor
        theta = torch.zeros(b, 2, 3, device=device, dtype=dtype)
        theta[:, 0, 0] = inv_f
        theta[:, 1, 1] = inv_f
        theta[:, 0, 2] = cx_n * (1.0 - inv_f)
        theta[:, 1, 2] = cy_n * (1.0 - inv_f)

        grid = F.affine_grid(theta, size=(b, 1, h, w), align_corners=True)
        out = F.grid_sample(
            m4,
            grid,
            mode="bilinear",
            padding_mode="zeros",
            align_corners=True,
        )

        out = out.squeeze(1).clamp(0.0, 1.0).float()
        return (out,)
