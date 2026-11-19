#!/usr/bin/env python3
"""Prepare and render a photo using the installed shared handwriting library."""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
import shutil
import sys

from collage_core import asset_path, load_source, read_json, render, require, sha_file, write_json

SKILL = Path(__file__).resolve().parents[1]


def select_page(catalog, mood='', paper_id=None):
    items = catalog['items']
    if paper_id:
        selected = next((item for item in items if item['id'] == paper_id), None)
        require(selected is not None, f'找不到手抄编号：{paper_id}')
        return selected
    terms = [term.strip() for term in mood.replace('，', ',').split(',') if term.strip()]
    def score(item):
        return sum(1 for term in terms for tag in item['moods'] if term in tag or tag in term)
    # The agent observes the photo and supplies mood; this script does not pretend to do vision.
    ranked = sorted(items, key=lambda item: (-score(item), item['id'] != 'quiet', item['id']))
    require(not terms or score(ranked[0])>0,'没有情绪标签匹配的共享页；Agent 应检查全部参考，再决定是否补充外部文字。')
    return ranked[0]


def prepare(photo_path, out, mood='', paper_id=None, layout='auto', box=None,
            axis='y', split_at=None, protected=None, no_grade=False, library=None,
            transcript=None, regions=None, crop_box=None):
    if library is None:
        from library import ensure_library, materialize_page
        library,catalog=ensure_library(Path(out).resolve().parent/'.literary-reference-cache')
        bundled=True
    else:
        library=Path(library).resolve()
        catalog=read_json(library/'catalog.json')
        bundled=False
    page = select_page(catalog, mood, paper_id)
    require(page.get('transcript_status')!='ocr-draft-needs-visual-check' or
            (transcript is not None and regions is not None),
            '此页转录为 OCR 草稿，Agent 必须逐字核对后提供 --transcript-file 和 --regions-file。')
    if bundled:
        page=materialize_page(library,page,crop_box)
    paper_path = asset_path(library, page['image'])
    require(sha_file(paper_path) == page['sha256'], '共享手抄校验失败，请重新安装完整 Skill。')
    photo_path = Path(photo_path).resolve()
    photo, profile, photo_meta = load_source(photo_path, 'photo')
    paper, paper_profile, _ = load_source(paper_path, 'paper')
    require(not (profile and paper_profile and profile != paper_profile), '照片与手抄色彩配置不兼容。')
    out = Path(out).resolve()
    require(not out.exists(), '工作目录已存在，请使用新的 --out。')
    width, height = photo.size
    margin = max(8, min(24, min(width, height) // 50))
    kind = ('horizontal' if height > width * 1.2 else 'vertical') if layout == 'auto' else layout
    require(kind in ('vertical', 'horizontal', 'overlay', 'triptych'), '不支持的布局。')
    if kind == 'vertical' or (kind == 'triptych' and axis == 'y'):
        scale = min(1, (width - 2 * margin) / paper.width)
        extent = max(1, math.floor(paper.height * scale)) + 2 * margin
    else:
        scale = min(1, (height - 2 * margin) / paper.height)
        extent = max(1, math.floor(paper.width * scale)) + 2 * margin
    require(scale > 0 and page['smallest_character_px'] * scale >= page['minimum_character_px'],
            '照片分辨率不足以清楚呈现完整手抄；请使用高清生活照或改用较大容器。')
    layout_cfg = {'type':kind, 'margin':margin, 'gap':0}
    if kind in ('vertical','horizontal'):
        layout_cfg.update(panel_size=extent, paper_side='after')
    elif kind == 'triptych':
        require(split_at is not None, '穿页布局需由 Agent 根据照片提供 --split-at。')
        layout_cfg.update(panel_size=extent, axis=axis, split_at=split_at)
    else:
        require(box is not None, '叠纸布局需由 Agent 根据真实留白提供 --box。')
        layout_cfg['box'] = box
    paper_cfg = {key:copy.deepcopy(page[key]) for key in
                 ('image','expected_transcript','regions','smallest_character_px','minimum_character_px','rights')}
    paper_cfg.update(asset_kind=page.get('asset_kind','real-handcopy'), allow_upscale=False)
    if 'production' in page:
        paper_cfg['production']=copy.deepcopy(page['production'])
    if transcript is not None:
        paper_cfg['expected_transcript']=transcript
    if regions is not None:
        paper_cfg['regions']=regions
    if kind == 'overlay':
        paper_cfg.update(opacity=0.72, ink_opacity=0.96)
    config = {'schema_version':1,
        'photo':{'image':'photos/input'+photo_path.suffix.lower(),
                 'protected_regions':protected or [],
                 'look':{'preset':'none'} if no_grade else
                    {'preset':'japanese-film','strength':0.45,'grain':0.35,'seed':1729}},
        'paper':paper_cfg,'layout':layout_cfg,'background':[240,235,221]}
    out.mkdir(parents=True)
    assets=out/'assets'
    (assets/'photos').mkdir(parents=True)
    (assets/'handcopies').mkdir()
    shutil.copy2(photo_path, assets/config['photo']['image'])
    shutil.copy2(paper_path, assets/page['image'])
    require(sha_file(photo_path)==sha_file(assets/config['photo']['image']), '复制照片校验失败。')
    write_json(assets/'catalog.json', {'schema_version':1,'items':[page]})
    write_json(out/'recipe.json', config)
    report=render(config, assets, out/'result')
    write_json(out/'selection.json', {'paper_id':page['id'],'mood':mood,
        'library_version':catalog['version'],'source_verification':page['source_verification'],
        'photo_file_sha256':photo_meta['file_sha256'], 'shared_paper_sha256':page['sha256'],
        'attribution_note':'图中文字和落款按原图保留；不可把图上落款当作已核实作者。'})
    return {'workspace':str(out),'image':str(out/'result/final.png'),
            'paper_id':page['id'],'automatic_pass':report['automatic_pass'],
            'delivery_ready':report['delivery_ready'],
            'next':'Agent 对照原纸完成文字、审美与出处/权利复核，再运行 verify.py --require-review。'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--photo', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--mood', default='安静')
    p.add_argument('--paper-id')
    p.add_argument('--layout', choices=('auto','vertical','horizontal','overlay','triptych'), default='auto')
    p.add_argument('--box', nargs=4, type=int)
    p.add_argument('--axis', choices=('x','y'), default='y')
    p.add_argument('--split-at', type=int)
    p.add_argument('--protected-json', default='[]')
    p.add_argument('--no-grade', action='store_true')
    p.add_argument('--library', help='Agent 生成的外部片段素材目录；默认随包 69 张参考素材库')
    p.add_argument('--transcript-file', help='Agent 逐字核对后的完整转录；用于替换 OCR 草稿')
    p.add_argument('--regions-file', help='Agent 对选定纸页核对后的正文与署名框 JSON')
    p.add_argument('--crop-box', nargs=4, type=int, help='Agent 在原参考图上确认的完整纸区坐标')
    args=p.parse_args()
    try:
        result=prepare(args.photo,args.out,args.mood,args.paper_id,args.layout,args.box,
                       args.axis,args.split_at,json.loads(args.protected_json),args.no_grade,args.library,
                       Path(args.transcript_file).read_text(encoding='utf-8') if args.transcript_file else None,
                       read_json(args.regions_file) if args.regions_file else None,args.crop_box)
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print(f'制作失败：{exc}', file=sys.stderr)
        return 1
    print(json.dumps(result,ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
