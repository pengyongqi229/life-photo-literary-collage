#!/usr/bin/env python3
"""Export one finished image after current viewing proof and strict source review."""
import argparse
import json
from pathlib import Path
import shutil

from collage_core import read_json, require, sha_file, verify_bundle


def finalize(bundle, assets, out, preview=None):
    bundle, out = Path(bundle).resolve(), Path(out).resolve()
    require(not out.exists(), '交付目录已存在，请使用新目录。')
    preview = Path(preview).resolve() if preview else bundle.parent/'preview'
    proof = read_json(preview/'report.json')
    entry = next((item for item in proof['entries']
                  if Path(item['source_bundle']).resolve() == bundle), None)
    require(entry is not None and entry['source_final_sha256'] == sha_file(bundle/'final.png'),
            '缺少当前版本的完整预览；请重新运行 preview.py 并看图复核。')
    require((preview/entry['preview_file']).is_file(), '完整预览图片缺失，请重新生成。')
    verified = verify_bundle(bundle, assets, require_review=True)
    require(verified['delivery_ready'], '内部复核未通过，不能导出为完成品。')
    out.mkdir(parents=True)
    result = out/'final.png'
    shutil.copy2(bundle/'final.png', result)
    require(sha_file(result) == entry['source_final_sha256'], '交付文件复制校验失败。')
    return {'image': str(result), 'delivery_ready': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle')
    parser.add_argument('--assets', required=True)
    parser.add_argument('--preview', help='Current preview directory; defaults to sibling preview/')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        result = finalize(args.bundle, args.assets, args.out, args.preview)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f'完成品导出失败：{exc}')
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
