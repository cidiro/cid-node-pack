import torch
import torch.nn.functional as F
import comfy.utils


class CidCropAndStitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_src": ("IMAGE",),
                "image_dst": ("IMAGE",),
                "mask": ("MASK",),
            },
            "optional": {
                "blend_ratio": ("FLOAT", {
                    "default": 0.05,
                    "min": 0.0,
                    "max": 0.5,
                    "step": 0.01,
                }),
                "color_match_strength": ("FLOAT", {
                    "default": 0.35,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                }),
                "processing_device": (["auto", "gpu", "cpu"], {
                    "default": "auto",
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Image"

    def _blend_radii_from_bboxes(self, mask, blend_ratio):
        if blend_ratio <= 0.0:
            return [0 for _ in range(mask.shape[0])]

        _, h, w = mask.shape
        foreground = mask > 0.0
        has_pixels = foreground.flatten(1).any(dim=1)

        y_coords = torch.arange(h, device=mask.device).view(1, h)
        x_coords = torch.arange(w, device=mask.device).view(1, w)
        any_y = foreground.any(dim=2)
        any_x = foreground.any(dim=1)

        y_min = torch.where(any_y, y_coords, torch.full_like(y_coords, h)).min(dim=1).values
        y_max = torch.where(any_y, y_coords, torch.full_like(y_coords, -1)).max(dim=1).values
        x_min = torch.where(any_x, x_coords, torch.full_like(x_coords, w)).min(dim=1).values
        x_max = torch.where(any_x, x_coords, torch.full_like(x_coords, -1)).max(dim=1).values

        bbox_h = (y_max - y_min + 1).clamp_min(0)
        bbox_w = (x_max - x_min + 1).clamp_min(0)
        base = torch.minimum(bbox_h, bbox_w)
        radii = torch.round(base.float() * float(blend_ratio)).long()
        radii = torch.where(has_pixels & (radii < 1), torch.ones_like(radii), radii)
        radii = torch.where(has_pixels, radii, torch.zeros_like(radii))
        return radii.detach().cpu().tolist()

    def _erode_binary_mask(self, mask):
        padded = F.pad(mask, (1, 1, 1, 1), mode="replicate")
        return 1.0 - F.max_pool2d(1.0 - padded, kernel_size=3, stride=1)

    def _smoothstep(self, value):
        return value * value * (3.0 - 2.0 * value)

    def _processing_device(self, requested_device, fallback_device):
        if requested_device == "cpu":
            return torch.device("cpu")
        if requested_device == "gpu" and torch.cuda.is_available():
            if fallback_device.type == "cuda":
                return fallback_device
            return torch.device("cuda")
        return fallback_device

    def _inward_feather_masks(self, mask, radii):
        if not radii or max(radii) <= 0:
            return mask.clamp(0.0, 1.0)

        binary = (mask > 0.001).float().unsqueeze(1)
        max_radius = max(radii)
        radii_tensor = torch.tensor(radii, device=mask.device, dtype=binary.dtype).view(-1, 1, 1, 1)
        distance = torch.zeros_like(binary)
        current = binary

        for step in range(max_radius):
            active = (radii_tensor > step).to(binary.dtype)
            distance = distance + current * active
            current = self._erode_binary_mask(current)

        alpha = (distance / radii_tensor.clamp_min(1.0)).clamp(0.0, 1.0).squeeze(1)
        alpha = self._smoothstep(alpha)

        # Respect any existing soft/painted opacity while enforcing no source bleed
        # outside the selected region.
        feathered = torch.minimum(alpha, mask.clamp(0.0, 1.0))
        enabled = radii_tensor.squeeze(1) > 0
        return torch.where(enabled, feathered, mask.clamp(0.0, 1.0))

    def _sum_filter_bchw(self, value, radius):
        if radius <= 0:
            return value

        channels = value.shape[1]
        kernel_size = 2 * radius + 1
        kh = torch.ones(channels, 1, 1, kernel_size, device=value.device, dtype=value.dtype)
        kv = torch.ones(channels, 1, kernel_size, 1, device=value.device, dtype=value.dtype)
        value = F.conv2d(value, kh, padding=(0, radius), groups=channels)
        value = F.conv2d(value, kv, padding=(radius, 0), groups=channels)
        return value

    def _edge_color_match(self, image_src, image_dst, soft_mask, radii, strength):
        if strength <= 0.0:
            return image_src

        src = image_src.permute(0, 3, 1, 2).float()
        dst = image_dst.permute(0, 3, 1, 2).float()
        alpha = soft_mask.unsqueeze(1).float()
        band = (4.0 * alpha * (1.0 - alpha)).clamp(0.0, 1.0)

        corrected = src.clone()
        eps = 1e-6
        strength = float(max(0.0, min(1.0, strength)))

        radius_groups = {}
        for i, radius in enumerate(radii):
            color_radius = max(1, min(int(radius) * 2, 96))
            radius_groups.setdefault(color_radius, []).append(i)

        for color_radius, indices in radius_groups.items():
            index = torch.tensor(indices, device=src.device, dtype=torch.long)
            src_i = src.index_select(0, index)
            dst_i = dst.index_select(0, index)
            band_i = band.index_select(0, index)
            diff_i = (dst_i - src_i) * band_i
            numerator = self._sum_filter_bchw(diff_i, color_radius)
            denominator = self._sum_filter_bchw(band_i, color_radius).clamp_min(eps)
            correction = numerator / denominator
            influence = band_i * strength
            corrected[index] = src_i + correction * influence

        return corrected.permute(0, 2, 3, 1).to(image_src.dtype)

    def main(self, image_src, image_dst, mask, blend_ratio=0.05, color_match_strength=0.35, processing_device="auto"):
        if image_src.dim() == 3:
            image_src = image_src.unsqueeze(0)
        if image_dst.dim() == 3:
            image_dst = image_dst.unsqueeze(0)
        if mask.dim() == 2:
            mask = mask.unsqueeze(0)

        if mask.max().item() == 0:
            return (image_dst,)

        dst_b, dst_h, dst_w, dst_c = image_dst.shape
        device = image_dst.device
        dtype = image_dst.dtype

        # Resize image_src to dst spatial dims
        src_b, src_h, src_w, src_c = image_src.shape
        if src_h != dst_h or src_w != dst_w:
            src_bchw = image_src.permute(0, 3, 1, 2)
            src_bchw = comfy.utils.common_upscale(src_bchw, dst_w, dst_h, "bicubic", "disabled")
            image_src = src_bchw.permute(0, 2, 3, 1)
            src_c = image_src.shape[3]

        # Align channels
        if src_c != dst_c:
            if src_c == 1 and dst_c >= 3:
                image_src = image_src.expand(-1, -1, -1, dst_c)
            elif src_c >= 3 and dst_c == 1:
                image_src = image_src[..., :1]
            elif src_c == 4 and dst_c == 3:
                image_src = image_src[..., :3]
            elif src_c == 3 and dst_c == 4:
                alpha = torch.ones(image_src.shape[0], dst_h, dst_w, 1, device=device, dtype=dtype)
                image_src = torch.cat([image_src, alpha], dim=-1)
            elif src_c > dst_c:
                image_src = image_src[..., :dst_c]
            else:
                pad = torch.zeros(image_src.shape[0], dst_h, dst_w, dst_c - src_c, device=device, dtype=dtype)
                image_src = torch.cat([image_src, pad], dim=-1)

        # Resize mask to dst spatial dims
        msk_h, msk_w = mask.shape[1], mask.shape[2]
        if msk_h != dst_h or msk_w != dst_w:
            mask_bchw = mask.unsqueeze(1).expand(-1, 3, -1, -1).float()
            mask_bchw = comfy.utils.common_upscale(mask_bchw, dst_w, dst_h, "bicubic", "disabled")
            mask = mask_bchw[:, 0, :, :]
        mask = mask.clamp(0.0, 1.0).to(dtype).to(device)

        # Batch alignment
        src_b = image_src.shape[0]
        msk_b = mask.shape[0]
        non_one = [b for b in (src_b, dst_b, msk_b) if b != 1]
        if len(set(non_one)) > 1:
            n = min(src_b, dst_b, msk_b)
            image_src = image_src[:n]
            image_dst = image_dst[:n]
            mask = mask[:n]
        else:
            n = max(src_b, dst_b, msk_b)
            if src_b == 1 and n > 1:
                image_src = image_src.expand(n, -1, -1, -1)
            if dst_b == 1 and n > 1:
                image_dst = image_dst.expand(n, -1, -1, -1)
            if msk_b == 1 and n > 1:
                mask = mask.expand(n, -1, -1)

        # Build an inward-only feather, so the source does not bleed beyond the
        # mask while the pasted edge still fades smoothly into the destination.
        output_device = image_dst.device
        blend_device = self._processing_device(processing_device, output_device)
        if blend_device != output_device:
            image_src = image_src.to(blend_device)
            image_dst = image_dst.to(blend_device)
            mask = mask.to(blend_device)

        radii = []
        if blend_ratio > 0.0:
            radii = self._blend_radii_from_bboxes(mask, blend_ratio)
            soft_mask = self._inward_feather_masks(mask, radii).to(dtype)
        else:
            soft_mask = mask
            radii = [0 for _ in range(mask.shape[0])]

        image_src = self._edge_color_match(
            image_src,
            image_dst,
            soft_mask,
            radii,
            color_match_strength,
        )
        soft_mask = soft_mask.unsqueeze(-1)
        result = (image_src * soft_mask + image_dst * (1.0 - soft_mask)).clamp(0.0, 1.0)

        return (result.to(device=output_device, dtype=dtype),)
