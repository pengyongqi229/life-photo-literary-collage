#!/usr/bin/env python3
"""Draw copyright-clear synthetic fixtures, not personal photos or real handwriting."""
import argparse
import copy
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from collage_core import require, write_json


def fixture_photo():
    width, height = 1280, 900
    im = Image.new("RGB", (width, height))
    # A deterministic drawn scene, explicitly labelled as a test image.
    im.putdata([(120 + x * 50 // width, 155 + y * 40 // height,
                 185 - y * 60 // height) for y in range(height) for x in range(width)])
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 570, width, height), fill=(109, 135, 102))
    draw.polygon([(0, 580), (380, 440), (700, 620)], fill=(85, 118, 100))
    draw.rectangle((1000, 260, 1034, 700), fill=(75, 77, 64))
    draw.ellipse((835, 140, 1180, 430), fill=(66, 105, 82))
    draw.ellipse((1040, 200, 1260, 455), fill=(76, 120, 84))
    draw.rectangle((780, 645, 1095, 685), fill=(137, 102, 71))
    draw.rectangle((810, 680, 825, 760), fill=(89, 82, 64))
    draw.rectangle((1050, 680, 1065, 760), fill=(89, 82, 64))
    font = ImageFont.load_default(size=28)
    draw.text((32, 800), "SYNTHETIC TEST SCENE", font=font, fill=(245, 243, 229))
    draw.text((32, 840), "NOT A PERSONAL PHOTO", font=font, fill=(245, 243, 229))
    return im


def fixture_paper(size, portrait=False, holes=False):
    width, height = size
    rng = random.Random(810)
    im = Image.new("RGBA", size)
    pixels = []
    for y in range(height):
        for x in range(width):
            noise = rng.randint(-5, 5)
            aged = round(7 * (abs(x - width / 2) / width + abs(y - height / 2) / height))
            pixels.append((239 + noise - aged, 230 + noise - aged, 208 + noise - aged, 255))
    im.putdata(pixels)
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=30)
    small = ImageFont.load_default(size=25)
    if portrait:
        lines = ["A quiet afternoon.", "Light rests here;", "the day goes on."]
        ys = [200, 258, 316]
        for text, y in zip(lines, ys):
            draw.text((34, y), text, font=font, fill=(44, 43, 36))
        draw.text((104, 450), "- Test author", font=font, fill=(44, 43, 36))
        draw.text((28, 660), "TEST PAGE ONLY", font=small, fill=(64, 61, 49))
        draw.text((28, 700), "NOT HANDWRITING", font=small, fill=(64, 61, 49))
        regions = [{"kind": "text", "box": [26, 185, 395, 365]},
                   {"kind": "signature", "box": [96, 440, 390, 495]},
                   {"kind": "text", "box": [22, 650, 402, 745]}]
    else:
        draw.text((42, 65), "A quiet afternoon.", font=font, fill=(44, 43, 36))
        draw.text((42, 120), "Light rests here; the day goes on.", font=font, fill=(44, 43, 36))
        draw.text((470, 210), "- Test author", font=font, fill=(44, 43, 36))
        draw.text((42, 294), "TEST PAGE ONLY / NOT HANDWRITING", font=small, fill=(64, 61, 49))
        regions = [{"kind": "text", "box": [34, 55, 755, 170]},
                   {"kind": "signature", "box": [462, 200, 750, 254]},
                   {"kind": "text", "box": [34, 284, 770, 338]}]
    if holes:
        for x in range(38, width, 65):
            draw.ellipse((x, 16, x + 14, 30), fill=(0, 0, 0, 0))
    return im, regions


def create_demo(root):
    root = Path(root)
    require(not root.exists(), "示例输出目录已存在，请选择新目录。")
    photos = root / "assets" / "photos"
    pages = root / "assets" / "handcopies"
    recipes_dir = root / "recipes"
    for folder in (photos, pages, recipes_dir):
        folder.mkdir(parents=True, exist_ok=True)
    fixture_photo().save(photos / "scene.png")
    landscape, land_regions = fixture_paper((800, 360), holes=True)
    portrait, port_regions = fixture_paper((420, 780), portrait=True, holes=True)
    landscape.save(pages / "landscape.png")
    portrait.save(pages / "portrait.png")
    base = {
        "schema_version": 1,
        "photo": {"image": "photos/scene.png", "protected_regions": [[780, 140, 1270, 770]],
                  "look": {"preset": "japanese-film", "strength": 0.45, "grain": 0.35, "seed": 1729}},
        "paper": {
            "image": "handcopies/landscape.png", "asset_kind": "synthetic-test",
            "expected_transcript": "A quiet afternoon.\nLight rests here; the day goes on.\n- Test author\nTEST PAGE ONLY / NOT HANDWRITING",
            "regions": land_regions, "smallest_character_px": 18,
            "minimum_character_px": 12, "allow_upscale": False,
            "rights": {"basis": "synthetic-test", "evidence": "Original procedural test drawings and original test sentences; no external quotation, personal image or real handwriting."},
        },
        "background": [239, 230, 208],
    }
    layouts = {
        "vertical": {"type": "vertical", "panel_size": 370, "margin": 20, "gap": 0},
        "horizontal": {"type": "horizontal", "panel_size": 440, "margin": 22, "gap": 0, "paper_side": "before"},
        "triptych": {"type": "triptych", "axis": "x", "split_at": 620, "panel_size": 440, "margin": 22, "gap": 0},
        "overlay": {"type": "overlay", "box": [45, 72, 730, 415], "margin": 12, "gap": 0},
    }
    recipes = {}
    for name, layout in layouts.items():
        recipe = copy.deepcopy(base)
        recipe["layout"] = layout
        if name in ("horizontal", "triptych"):
            recipe["paper"]["image"] = "handcopies/portrait.png"
            recipe["paper"]["regions"] = port_regions
            recipe["paper"]["expected_transcript"] = "A quiet afternoon.\nLight rests here;\nthe day goes on.\n- Test author\nTEST PAGE ONLY\nNOT HANDWRITING"
        if name == "overlay":
            recipe["paper"].update({"opacity": 0.55, "ink_opacity": 0.96})
        recipes[name] = recipe
        write_json(recipes_dir / f"{name}.json", recipe)
    (root / "NOTICE.txt").write_text("All images are procedural non-private test fixtures. Printed test text is not real handwriting. No literary quotation or referenced-chat image is included.\n", encoding="utf-8")
    return recipes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    create_demo(args.out)
    print(f"Created synthetic fixtures and four recipes: {args.out}")
