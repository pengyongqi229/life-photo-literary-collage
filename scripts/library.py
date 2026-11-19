#!/usr/bin/env python3
"""Unpack the bundled original reference ZIP locally, without altering its images."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from PIL import Image
from collage_core import read_json, require, sha_file, write_json

SKILL=Path(__file__).resolve().parents[1]
ARCHIVE=SKILL/'assets/参考图.zip'
META=SKILL/'assets/reference-archive.json'
MAX_EXPANDED=120_000_000


def ensure_library(cache):
    info=read_json(META)
    require(ARCHIVE.is_file() and sha_file(ARCHIVE)==info['sha256'],
            '随包参考图.zip 缺失或校验失败，请修复完整安装；无需用户重新提供素材。')
    root=Path(cache).resolve()/info['sha256'][:16]
    static=read_json(SKILL/'assets/catalog.json')
    root.mkdir(parents=True,exist_ok=True)
    references=root/'references'
    references.mkdir(exist_ok=True)
    with zipfile.ZipFile(ARCHIVE) as z:
        entries={entry.filename:entry for entry in z.infolist() if not entry.is_dir()}
        require(sum(e.file_size for e in entries.values())<=MAX_EXPANDED,'素材解压大小超限。')
        for item in static['items']:
            entry=entries.get(item['archive_entry'])
            require(entry is not None,'参考包缺少索引中的图片。')
            # Names in the original ZIP may have legacy encoding. Write safe normalized
            # names from the index instead of trusting any ZIP member path.
            dest=references/f"ref-{item['extraction']['reference_number']:03d}.jpg"
            if dest.exists() and sha_file(dest)==item['reference_sha256']:
                continue
            raw=z.read(entry)
            require(hashlib.sha256(raw).hexdigest()==item['reference_sha256'],'原参考图片哈希不匹配。')
            with tempfile.NamedTemporaryFile(dir=references,delete=False) as tmp:
                tmp.write(raw)
                temporary=Path(tmp.name)
            temporary.replace(dest)
    catalog=copy.deepcopy(static)
    for item in catalog['items']:
        item['reference_image']=f"references/ref-{item['extraction']['reference_number']:03d}.jpg"
    write_json(root/'catalog.json',catalog)
    return root,catalog


def materialize_page(root,page,crop_box=None):
    """Crop only the selected page; originals and original ZIP remain untouched."""
    source=Path(root)/page['reference_image']
    require(sha_file(source)==page['reference_sha256'],'本地原参考图片已变化。')
    box=crop_box or page['extraction']['crop_box']
    with Image.open(source) as original:
        rgb=original.convert('RGB')
        require(len(box)==4 and 0<=box[0]<box[2]<=rgb.width and 0<=box[1]<box[3]<=rgb.height,
                '纸张裁切坐标越界。')
        paper=rgb.crop(tuple(box))
    target=Path(root)/page['image']
    target.parent.mkdir(parents=True,exist_ok=True)
    paper.save(target,optimize=True)
    with Image.open(target) as saved:
        require(saved.convert('RGB').tobytes()==paper.tobytes(),'纸区像素保存校验失败。')
    item=copy.deepcopy(page)
    item['extraction']['crop_box']=list(box)
    item['sha256']=sha_file(target)
    return item


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True,help='Agent 选择的本地素材缓存目录')
    args=p.parse_args()
    try:
        root,c=ensure_library(args.out)
    except (ValueError,OSError,KeyError,zipfile.BadZipFile) as exc:
        print(f'素材准备失败：{exc}')
        return 1
    print(json.dumps({'library':str(root),'references':len(c['items']),
        'original_archive_unchanged':True,'next':'查看 references/ 原图，从全部69张中匹配后裁取真实手抄。'},ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
