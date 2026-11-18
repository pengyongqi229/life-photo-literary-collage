"""A restrained, deterministic photographic grade; no generation or geometry edits."""
from __future__ import annotations

import math
import random

from PIL import Image, ImageChops, ImageEnhance, ImageStat


def resolve_look(value=None):
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError("photo.look 必须是对象。")
    unknown = set(value) - {"preset", "strength", "grain", "seed"}
    if unknown:
        raise ValueError(f"未知调色字段：{', '.join(sorted(unknown))}")
    preset = value.get("preset", "japanese-film")
    if preset not in ("japanese-film", "none"):
        raise ValueError("photo.look.preset 只能是 japanese-film 或 none。")
    strength = value.get("strength", 0.45 if preset != "none" else 0.0)
    grain = value.get("grain", 0.35 if preset != "none" else 0.0)
    for name, number in (("strength", strength), ("grain", grain)):
        if type(number) not in (int, float) or not math.isfinite(number) or not 0 <= number <= 1:
            raise ValueError(f"photo.look.{name} 必须位于 [0, 1]。")
    seed = value.get("seed", 1729)
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("photo.look.seed 必须是 0–4294967295 的整数。")
    if preset == "none":
        strength, grain = 0.0, 0.0
    return {"preset": preset, "strength": float(strength), "grain": float(grain),
            "seed": seed, "algorithm_version": 1}


def apply_photo_look(original, settings=None):
    """Return a new RGBA image and an explicit, reproducible processing record."""
    look = resolve_look(settings)
    strength = look["strength"]
    if look["preset"] == "none" or strength == 0:
        result = original.copy()
    else:
        rgb = ImageEnhance.Color(original.convert("RGB")).enhance(1 - 0.10 * strength)
        bands = []
        for band, warmth in zip(rgb.split(), (4.0, 1.0, -3.0)):
            table = []
            for value in range(256):
                t = value / 255
                # Gentle contrast softening; keep bright whites from turning grey.
                soft = (value - 127.5) * (1 - 0.045 * strength) + 127.5
                soft = soft * (1 - 0.70 * t**4) + value * (0.70 * t**4)
                shadow = 4.0 * strength * (1 - t)**2
                warm = warmth * strength * (1 - t**3)
                table.append(max(0, min(255, round(soft + shadow + warm))))
            bands.append(band.point(table))
        rgb = Image.merge("RGB", bands)
        # Sparse monochrome +/-1-level grain. Seeded once on the full native image,
        # so split-page layouts can reassemble without seams or new noise patterns.
        count = round(128 * look["grain"] * strength)
        if count:
            noise = Image.frombytes("L", original.size,
                                    random.Random(look["seed"]).randbytes(original.width * original.height))
            grain = noise.point([127 if v < count else 129 if v >= 256 - count else 128
                                 for v in range(256)])
            rgb = ImageChops.add(rgb, Image.merge("RGB", (grain, grain, grain)), offset=-128)
        result = rgb.convert("RGBA")
        result.putalpha(original.getchannel("A"))
    diff = ImageChops.difference(original.convert("RGB"), result.convert("RGB"))
    look["max_channel_delta"] = max(high for _, high in diff.getextrema())
    look["mean_absolute_channel_delta"] = [round(v, 6) for v in ImageStat.Stat(diff).mean]
    look["pixel_values_may_change"] = bool(look["max_channel_delta"])
    look["geometry_changed"] = False
    return result, look
