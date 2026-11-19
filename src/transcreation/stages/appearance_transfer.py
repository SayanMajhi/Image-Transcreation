"""Deterministic research appearance cue; no geometry synthesis or edit approval."""
import numpy as np
from PIL import Image, ImageCms, ImageFilter


METHOD = "DETERMINISTIC_APPEARANCE_TRANSFER_BASELINE"
SETTINGS = {
    "method": METHOD, "scope": "RESEARCH_ONLY", "color_space": "CIELAB D50 via Pillow LittleCMS",
    "delta_a": 14.0, "delta_b": 26.0, "strength": 0.75,
    "inward_gaussian_radius_pixels": 12.0,
    "highlight_start_L": 70.0, "highlight_end_L": 95.0,
    "minimum_highlight_effect": 0.35,
    "palette_reason": "Positive a/b warm reddish-yellow cue; no reference dish or authenticity claim.",
}


def transfer_appearance(image, mask, protected, *, scope):
    """Keep LAB L and spatial positions; blend chroma-shifted RGB only inside mask."""
    if scope != "RESEARCH_ONLY":
        raise ValueError("appearance transfer is exclusively RESEARCH_ONLY")
    if image.mode != "RGB":
        raise ValueError("decoded RGB source required")
    for layer in (mask, protected):
        if layer.mode != "L" or layer.size != image.size or not set(layer.tobytes()) <= {0, 255}:
            raise ValueError("original-resolution binary masks required")
    editable = np.asarray(mask) == 255
    if not editable.any() or np.any(editable & (np.asarray(protected) == 255)):
        raise ValueError("empty editable region or protected intersection")
    rgb_profile = ImageCms.createProfile("sRGB")
    lab_profile = ImageCms.createProfile("LAB")
    lab = ImageCms.profileToProfile(image, rgb_profile, lab_profile, outputMode="LAB")
    channels = np.asarray(lab).astype(np.float32).copy()
    lightness = channels[:, :, 0] * (100.0 / 255.0)
    highlight = np.clip((lightness - 70.0) / 25.0, 0.0, 1.0)
    weight = SETTINGS["strength"] * (1.0 - 0.65 * highlight)
    channels[:, :, 1] += SETTINGS["delta_a"] * weight
    channels[:, :, 2] += SETTINGS["delta_b"] * weight
    adapted_lab = Image.frombytes("LAB", image.size, np.rint(np.clip(channels, 0, 255)).astype(np.uint8).tobytes())
    adapted = ImageCms.profileToProfile(adapted_lab, lab_profile, rgb_profile, outputMode="RGB")
    alpha = np.asarray(mask.filter(ImageFilter.GaussianBlur(12.0))).astype(np.float32) / 255.0
    alpha *= editable
    original = np.asarray(image)
    blended = np.rint(alpha[:, :, None] * np.asarray(adapted) + (1 - alpha[:, :, None]) * original)
    result = np.clip(blended, 0, 255).astype(np.uint8)
    result[~editable] = original[~editable]
    return Image.fromarray(result), Image.fromarray(np.rint(alpha * 255).astype(np.uint8))
