#!/usr/bin/env python3
"""Compose an untouched photo and a complete real handwritten paper page."""
import argparse
import json
import sys
from collage_core import read_json, render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="JSON recipe")
    parser.add_argument("--assets", required=True, help="Caller-owned material directory")
    parser.add_argument("--out", required=True, help="New output directory; never overwrites")
    args = parser.parse_args()
    try:
        report = render(read_json(args.config), args.assets, args.out)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"合成失败：{exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": args.out, "automatic_pass": report["automatic_pass"],
                      "delivery_ready": report["delivery_ready"],
                      "next": "对照原素材填写 review.json，再运行 verify.py --require-review。"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
