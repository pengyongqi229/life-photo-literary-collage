#!/usr/bin/env python3
"""Independently rebuild from sources and compare every output pixel and hash."""
import argparse
import json
import sys
from pathlib import Path
from collage_core import read_json, verify_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="Bundle directory")
    parser.add_argument("--assets", required=True, help="Original caller-owned material directory")
    parser.add_argument("--review", help="Alternative completed review JSON")
    parser.add_argument("--require-review", action="store_true", help="Exit nonzero unless all visual review items pass")
    args = parser.parse_args()
    try:
        # Remove a prior success report before checking: a failed run must not leave stale success.
        report_path = Path(args.output) / "verification.json"
        if report_path.exists():
            report_path.unlink()
        report = verify_bundle(args.output, args.assets, args.review, args.require_review)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        if Path(args.output).is_dir():
            failed = read_json(report_path) if report_path.exists() else {"automatic_pass": False}
            failed.update({"delivery_ready": False, "error": str(exc)})
            report_path.write_text(json.dumps(failed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"验证失败：{exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
