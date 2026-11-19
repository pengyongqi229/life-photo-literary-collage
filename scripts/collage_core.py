"""Deterministic full-page collage engine. No image generation, OCR or network calls."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageOps, __version__ as PILLOW_VERSION
from photo_look import apply_photo_look

VERSION = "1.2.0"
MAX_PIXELS = 40_000_000
ARTIFACTS = ("final.png", "photo-native.png", "photo-graded.png", "photo-base.png",
             "paper-layer.png", "coverage-mask.png")
REVIEW_FIELDS = (
    "full_text_and_punctuation", "signature", "source_page_complete",
    "paper_texture_and_edges", "legibility", "subject_unobstructed",
    "mood_and_layout", "attribution_and_rights",
    "photo_look_natural",
)


class CollageError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise CollageError(message)


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha_pixels(im):
    header = f"{im.mode}:{im.width}:{im.height}:".encode("ascii")
    return hashlib.sha256(header + im.tobytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def asset_path(root, name):
    require(isinstance(name, str) and name, "素材路径必须是非空字符串。")
    root = Path(root).resolve()
    candidate = (root / name).resolve()
    require(candidate.is_relative_to(root), "素材路径不能越出 --assets 目录（包括符号链接）。")
    require(candidate.is_file(), f"找不到素材：{name}")
    return candidate


def integer(value, name, minimum=0):
    require(type(value) is int and value >= minimum, f"{name} 必须是 >= {minimum} 的整数。")
    return value


def number(value, name, low, high):
    require(type(value) in (int, float) and math.isfinite(value) and low <= value <= high,
            f"{name} 必须位于 [{low}, {high}]。")
    return float(value)


def check_box(value, size, name):
    require(isinstance(value, list) and len(value) == 4, f"{name} 应为 [左, 上, 右, 下]。")
    for val in value:
        integer(val, name)
    left, top, right, bottom = value
    require(0 <= left < right <= size[0] and 0 <= top < bottom <= size[1],
            f"{name} 越界或面积为零；右、下边界为不包含端点。")
    return tuple(value)


def safe_size(width, height):
    require(0 < width and 0 < height and width * height <= MAX_PIXELS,
            f"画布超过限制（{MAX_PIXELS:,} 像素）或为空；不能通过缩小生活照规避。")


def load_source(path, role):
    before = sha_file(path)
    with Image.open(path) as original:
        safe_size(*original.size)
        require(getattr(original, "n_frames", 1) == 1, f"{role} 不支持动画或多页输入。")
        require(original.mode in ("RGB", "RGBA", "L", "LA", "P"),
                f"{role} 不支持 {original.mode}；请提供 8 位 RGB/RGBA/灰度/调色板输入。")
        orientation = int(original.getexif().get(274, 1))
        profile = original.info.get("icc_profile")
        original_mode = original.mode
        original_size = list(original.size)
        # Only a lossless EXIF permutation and decoding to RGBA: no resize/color transform.
        normalized = ImageOps.exif_transpose(original).convert("RGBA")
    if role == "photo":
        require(normalized.getchannel("A").getextrema() == (255, 255),
                "生活照包含透明像素；本工具只接收不透明生活照，避免隐藏 RGB 被合成改变。")
    require(sha_file(path) == before, f"读取期间源文件变化：{path.name}")
    metadata = {
        "file_sha256": before, "normalized_pixel_sha256": sha_pixels(normalized),
        "stored_size": original_size, "display_size": list(normalized.size),
        "source_mode": original_mode, "exif_orientation": orientation,
        "icc_sha256": hashlib.sha256(profile).hexdigest() if profile else None,
    }
    return normalized, profile, metadata


def difference_pixels(a, b):
    if a.mode != b.mode or a.size != b.size:
        raise CollageError("像素比较的尺寸或模式不一致。")
    channels = ImageChops.difference(a, b).split()
    maximum = channels[0]
    for channel in channels[1:]:
        maximum = ImageChops.lighter(maximum, channel)
    histogram = maximum.histogram()
    return sum(histogram[1:])


def opaque_background(value):
    require(isinstance(value, list) and len(value) == 3, "background 应为三个 0–255 整数。")
    for val in value:
        integer(val, "background")
        require(val <= 255, "background 通道不能超过 255。")
    return tuple(value) + (255,)


def full_page_layer(page, target, opacity, ink_opacity):
    """Retain full RGB page, texture, punctuation and source alpha; never erase light pixels."""
    scale = min(target[0] / page.width, target[1] / page.height)
    width = max(1, min(target[0], round(page.width * scale)))
    height = max(1, min(target[1], round(page.height * scale)))
    scaled = page.resize((width, height), Image.Resampling.LANCZOS) if page.size != (width, height) else page.copy()
    # This continuous luminance curve gives dark ink more opacity without extracting/retyping it.
    luminance = scaled.convert("RGB").convert("L")
    lut = [round(255 * (opacity + (ink_opacity - opacity) * (1 - v / 255) ** 2)) for v in range(256)]
    alpha = ImageChops.multiply(scaled.getchannel("A"), luminance.point(lut))
    scaled.putalpha(alpha)
    return scaled, min(width / page.width, height / page.height)


def build(config, assets):
    require(config.get("schema_version") == 1, "仅支持 schema_version: 1。")
    photo_cfg, paper_cfg, layout = config["photo"], config["paper"], config["layout"]
    photo_path = asset_path(assets, photo_cfg["image"])
    paper_path = asset_path(assets, paper_cfg["image"])
    photo, icc, photo_meta = load_source(photo_path, "photo")
    paper, paper_icc, paper_meta = load_source(paper_path, "paper")
    require(not (icc and paper_icc and icc != paper_icc),
            "两张素材的 ICC 配置不同。请先准备色彩空间相容的手抄素材，生活照不得自动转换色域。")
    native_photo = photo
    photo, processing = apply_photo_look(native_photo, photo_cfg.get("look"))
    processing["native_pixel_sha256"] = sha_pixels(native_photo)
    processing["graded_pixel_sha256"] = sha_pixels(photo)
    transcript = paper_cfg.get("expected_transcript")
    require(isinstance(transcript, str) and transcript.strip(), "必须记录完整原文、标点和署名 expected_transcript。")
    require(paper_cfg.get("asset_kind") in ("real-handcopy", "synthetic-test", "typeset-handwriting"),
            "paper.asset_kind 必须区分真实手抄、手写风排印与测试素材。")
    if paper_cfg["asset_kind"] == "typeset-handwriting":
        production = paper_cfg.get("production", {})
        require(production.get("method") == "font-render" and production.get("is_real_handwriting") is False
                and production.get("author_penmanship") is False,
                "新文字排印须明确记录为手写风效果，不能冒充真实手抄或作者亲笔。")
    rights = paper_cfg.get("rights", {})
    require(rights.get("basis") in ("user-original", "permission", "public-domain", "licensed", "synthetic-test")
            and isinstance(rights.get("evidence"), str) and rights["evidence"].strip(),
            "必须记录 rights.basis 和 evidence；这只是留证，不能代替出处/版权核实。")
    if paper_cfg["asset_kind"] == "synthetic-test":
        require(rights["basis"] == "synthetic-test", "测试样本必须明确标为 synthetic-test。")
    else:
        require(rights["basis"] != "synthetic-test", "真实手抄不能使用测试版权标签。")
    regions = paper_cfg.get("regions", [])
    require(isinstance(regions, list) and regions, "必须标注全部正文和署名范围 regions。")
    region_boxes = []
    kinds = set()
    for index, region in enumerate(regions):
        require(region.get("kind") in ("text", "signature"), "region.kind 只能是 text 或 signature。")
        kinds.add(region["kind"])
        region_boxes.append(check_box(region["box"], paper.size, f"regions[{index}].box"))
    require(kinds == {"text", "signature"}, "必须分别标注正文（含标点）和署名；不可漏掉落款。")
    protected = [check_box(box, photo.size, "photo.protected_regions")
                 for box in photo_cfg.get("protected_regions", [])]
    gap = integer(layout.get("gap", 0), "layout.gap")
    margin = integer(layout.get("margin", 20), "layout.margin")
    kind = layout["type"]
    require(kind in ("vertical", "horizontal", "triptych", "overlay"), "不支持该布局。")
    width, height = photo.size
    # (source rectangle, destination top-left); every source pixel is placed exactly once.
    tiles = []
    if kind in ("vertical", "horizontal"):
        axis = "y" if kind == "vertical" else "x"
        extent = integer(layout["panel_size"], "layout.panel_size", 1)
        side = layout.get("paper_side", "after")
        require(side in ("before", "after"), "paper_side 应为 before 或 after。")
        if axis == "y":
            canvas_size = (width, height + gap + extent)
            photo_xy = (0, extent + gap) if side == "before" else (0, 0)
            panel = (0, 0, width, extent) if side == "before" else (0, height + gap, width, height + gap + extent)
        else:
            canvas_size = (width + gap + extent, height)
            photo_xy = (extent + gap, 0) if side == "before" else (0, 0)
            panel = (0, 0, extent, height) if side == "before" else (width + gap, 0, width + gap + extent, height)
        tiles.append(((0, 0, width, height), photo_xy))
    elif kind == "triptych":
        axis = layout.get("axis", "x")
        require(axis in ("x", "y"), "triptych.axis 应为 x 或 y。")
        limit = width if axis == "x" else height
        split = integer(layout["split_at"], "layout.split_at", 1)
        require(split < limit, "split_at 必须严格位于照片内部。")
        for box in protected:
            lo, hi = (box[0], box[2]) if axis == "x" else (box[1], box[3])
            require(not lo < split < hi, "分割线穿过受保护主体，请换位置或布局。")
        extent = integer(layout["panel_size"], "layout.panel_size", 1)
        added = extent + 2 * gap
        if axis == "x":
            canvas_size = (width + added, height)
            panel = (split + gap, 0, split + gap + extent, height)
            tiles = [((0, 0, split, height), (0, 0)),
                     ((split, 0, width, height), (split + added, 0))]
        else:
            canvas_size = (width, height + added)
            panel = (0, split + gap, width, split + gap + extent)
            tiles = [((0, 0, width, split), (0, 0)),
                     ((0, split, width, height), (0, split + added))]
    else:
        require(gap == 0, "overlay 不使用 gap。")
        canvas_size = photo.size
        panel = check_box(layout["box"], canvas_size, "layout.box")
        tiles.append(((0, 0, width, height), (0, 0)))
    safe_size(*canvas_size)
    interior = (panel[0] + margin, panel[1] + margin, panel[2] - margin, panel[3] - margin)
    require(interior[0] < interior[2] and interior[1] < interior[3], "纸张容器被 margin 挤空。")
    opacity = number(paper_cfg.get("opacity", 0.55 if kind == "overlay" else 1), "paper.opacity", 0.01, 1)
    ink_opacity = number(paper_cfg.get("ink_opacity", 0.96 if kind == "overlay" else 1), "paper.ink_opacity", opacity, 1)
    if kind != "overlay":
        require(opacity == ink_opacity == 1, "分栏布局应完整呈现原纸，不使用半透明。")
    page_layer, scale = full_page_layer(paper, (interior[2] - interior[0], interior[3] - interior[1]), opacity, ink_opacity)
    allow_upscale = paper_cfg.get("allow_upscale", False)
    require(type(allow_upscale) is bool, "allow_upscale 必须为布尔值。")
    require(scale <= 1 or allow_upscale, "纸张将被放大；优先用更高清手抄，确需放大时设 allow_upscale: true 并检查字迹。")
    smallest = number(paper_cfg["smallest_character_px"], "paper.smallest_character_px", 1, max(paper.size))
    minimum = number(paper_cfg.get("minimum_character_px", 12), "paper.minimum_character_px", 8, 200)
    require(smallest * scale >= minimum, "合成后最小字高不足；增大纸张区域或换布局，禁止删字/缩略句子。")
    px = interior[0] + (interior[2] - interior[0] - page_layer.width) // 2
    py = interior[1] + (interior[3] - interior[1] - page_layer.height) // 2
    base = Image.new("RGBA", canvas_size, opaque_background(config.get("background", [240, 235, 221])))
    for source_box, destination in tiles:
        base.paste(photo.crop(source_box), destination)  # no mask: exact pixel copy
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    layer.paste(page_layer, (px, py))  # no second alpha multiplication
    alpha = layer.getchannel("A")
    coverage = alpha.point([0] + [255] * 255)
    require(coverage.getbbox() is not None, "纸张完全不可见。")
    if kind == "overlay":
        for box in protected:
            require(coverage.crop(box).getbbox() is None, "纸张覆盖了受保护主体。请移动纸张或改用分栏。")
    final = Image.alpha_composite(base, layer)
    mapped_regions = []
    sx, sy = page_layer.width / paper.width, page_layer.height / paper.height
    for region, box in zip(regions, region_boxes):
        mapped = [px + math.floor(box[0] * sx), py + math.floor(box[1] * sy),
                  px + math.ceil(box[2] * sx), py + math.ceil(box[3] * sy)]
        check_box(mapped, canvas_size, "mapped text region")
        mapped_regions.append({"kind": region["kind"], "source_box": list(box), "output_box": mapped})
    images = {"final.png": final, "photo-native.png": native_photo, "photo-graded.png": photo, "photo-base.png": base,
              "paper-layer.png": layer, "coverage-mask.png": coverage}
    geometry = {"canvas_size": list(canvas_size), "paper_box": [px, py, px + page_layer.width, py + page_layer.height],
                "paper_scale": [sx, sy], "effective_smallest_character_px": smallest * scale,
                "regions": mapped_regions,
                "photo_tiles": [{"source_box": list(box), "destination": list(xy)} for box, xy in tiles]}
    metadata = {"photo": photo_meta, "paper": paper_meta}
    return images, geometry, metadata, icc, processing


def load_output_png(path, mode):
    with Image.open(path) as im:
        require(im.format == "PNG" and im.mode == mode, f"{path.name} 必须是 {mode} 无损 PNG。")
        return im.copy()


def check_pixels(images, geometry):
    final, base, photo = (images[key] for key in ("final.png", "photo-base.png", "photo-graded.png"))
    native = images["photo-native.png"]
    mask = images["coverage-mask.png"]
    # Verify every photo sample appears once in the base and reassembles exactly.
    restored = Image.new("RGBA", photo.size, (0, 0, 0, 0))
    coverage = Image.new("L", photo.size, 0)
    photo_changed = 0
    visible_checked = 0
    for tile in geometry["photo_tiles"]:
        box = tile["source_box"]
        x, y = tile["destination"]
        out_box = (x, y, x + box[2] - box[0], y + box[3] - box[1])
        tile_mask = mask.crop(out_box)
        area = (box[2] - box[0]) * (box[3] - box[1])
        require(coverage.crop(box).getbbox() is None, "照片源像素重复放置。")
        coverage.paste(255, box)
        restored.paste(base.crop(out_box), box[:2])
        visible_checked += area - tile_mask.histogram()[255]
        changed = ImageChops.difference(final.crop(out_box), photo.crop(box))
        channels = changed.split()
        maxima = channels[0]
        for channel in channels[1:]:
            maxima = ImageChops.lighter(maxima, channel)
        outside = ImageChops.multiply(maxima, ImageOps.invert(tile_mask))
        photo_changed += sum(outside.histogram()[1:])
    require(coverage.getextrema() == (255, 255), "照片有未放置的像素。")
    restored_diff = difference_pixels(restored, photo)
    require(restored_diff == 0, "画布底层无法逐像素还原为 photo-graded.png。")
    require(photo_changed == 0, "覆盖范围以外的照片像素与 photo-graded.png 不一致。")
    return {"photo_total_pixels": photo.width * photo.height,
            "comparison_baseline": "photo-graded.png",
            "native_to_graded_different_pixels": difference_pixels(native, photo),
            "base_reassembled_different_pixels": restored_diff,
            "visible_photo_pixels_checked": visible_checked,
            "visible_photo_different_pixels": photo_changed,
            "covered_photo_pixels": photo.width * photo.height - visible_checked,
            "text_check": "geometry_only; visual review required; no OCR performed"}


def review_template():
    return {"checked_by": "", "notes": "逐项对照原图填写。脚本不能证明字句、作者和版权正确。",
            "checks": {key: False for key in REVIEW_FIELDS}}


def verify_bundle(out, assets, review_path=None, require_review=False):
    out = Path(out)
    manifest = read_json(out / "manifest.json")
    require(manifest.get("engine_version") == VERSION, "引擎版本不一致，请用生成该包的版本验证。")
    expected, geometry, source_meta, expected_icc, processing = build(manifest["recipe"], assets)
    require(manifest["sources"] == source_meta, "源文件或解码结果与生成时不同。")
    require(manifest["geometry"] == geometry, "记录的布局与重算结果不一致。")
    require(manifest["photo_processing"] == processing, "调色记录与从原照重算的结果不一致。")
    actual = {}
    for name in ARTIFACTS:
        path = out / name
        require(sha_file(path) == manifest["artifact_sha256"][name], f"文件哈希不一致：{name}")
        actual[name] = load_output_png(path, expected[name].mode)
        required_icc = expected_icc if expected[name].mode == "RGBA" else None
        require(actual[name].info.get("icc_profile") == required_icc, f"ICC 配置不一致：{name}")
        require(not actual[name].getexif(), f"输出不应携带 EXIF 元数据：{name}")
        require(actual[name].size == expected[name].size, f"尺寸不一致：{name}")
        require(difference_pixels(actual[name], expected[name]) == 0, f"重算像素不一致：{name}")
    pixels = check_pixels(actual, geometry)
    review_path = Path(review_path) if review_path else out / "review.json"
    review = read_json(review_path) if review_path.exists() else review_template()
    checked = isinstance(review.get("checked_by"), str) and bool(review["checked_by"].strip())
    approved = checked and all(review.get("checks", {}).get(key) is True for key in REVIEW_FIELDS)
    report = {"automatic_pass": True, "visual_review_pass": approved,
              "delivery_ready": approved, "engine_version": VERSION,
              "runtime_pillow": PILLOW_VERSION, "render_pillow": manifest["pillow_version"],
              "pixel_checks": pixels,
              "photo_processing": processing,
              "limits": ["自动检查仅证明文件、几何和合成像素；文字语义/漏标范围/辨识度须目视复核。",
                         "调色会改变 RGB；photo-native.png 保留未调色原照，photo-graded.png 是合成校验基准。",
                         "叠纸区的扁平合成像素会变化；覆盖区外必须与调色底图零差异。"],
              "review_sha256": sha_file(review_path) if review_path.exists() else None}
    write_json(out / "verification.json", report)
    require(not require_review or approved, "自动像素检查通过，但目视/出处版权复核未全部确认；不可标作最终交付。")
    return report


def render(config, assets, out):
    out = Path(out).resolve()
    root = Path(assets).resolve()
    # Validate and render in memory before creating a new directory. Never overwrite an existing bundle.
    require(not out.exists(), "输出目录已存在；请使用新的目录，避免覆盖素材或前次成品。")
    images, geometry, metadata, icc, processing = build(config, root)
    check_pixels(images, geometry)
    out.mkdir(parents=True)
    for name, im in images.items():
        kwargs = {"icc_profile": icc} if icc and im.mode == "RGBA" else {}
        encoded = im.copy()
        encoded.info.clear()  # retain source ICC explicitly; do not copy EXIF/GPS to outputs
        encoded.save(out / name, format="PNG", **kwargs)
    manifest = {"engine_version": VERSION, "pillow_version": PILLOW_VERSION,
                "normalization": "Source EXIF permutation + decode RGBA; photo_processing is recorded separately",
                "recipe": config, "sources": metadata, "geometry": geometry,
                "photo_processing": processing,
                "artifact_sha256": {name: sha_file(out / name) for name in ARTIFACTS}}
    write_json(out / "manifest.json", manifest)
    write_json(out / "review.json", review_template())
    return verify_bundle(out, root)
