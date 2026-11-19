#!/usr/bin/env python3
"""Create uncropped viewing-size proofs; never modify a full-resolution result."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from collage_core import read_json, require, sha_file, write_json


def create_previews(bundles, out, size=(720, 1080), minimum_text_px=12):
    out = Path(out).resolve()
    require(not out.exists(), '预览目录已存在，请使用新的 --out。')
    require(1 <= len(bundles) <= 8, '一次比较 1–8 个草稿。')
    require(all(type(v) is int and 32 <= v <= 4096 for v in size), '预览宽高须为 32–4096 整数。')
    require(1 <= minimum_text_px <= 100, '预览字高提示阈值须为 1–100。')
    previews, entries = [], []
    for index, source in enumerate(bundles):
        bundle = Path(source).resolve()
        manifest = read_json(bundle / 'manifest.json')
        final = bundle / 'final.png'
        digest = sha_file(final)
        require(digest == manifest['artifact_sha256']['final.png'], '成图已变化，请先重新合成与验证。')
        geometry = manifest['geometry']
        with Image.open(final) as original:
            require(list(original.size) == geometry['canvas_size'], '成图尺寸与布局记录不符。')
            full_size = original.size
            # thumbnail fits the WHOLE canvas. Cropping or cover-fit would hide signatures.
            preview = original.convert('RGB')
            preview.thumbnail(size, Image.Resampling.LANCZOS, reducing_gap=3.0)
        scale = min(preview.width / full_size[0], preview.height / full_size[1])
        smallest = geometry['effective_smallest_character_px'] * scale
        paper = geometry['paper_box']
        layout = manifest['recipe']['layout']
        kind = layout['type']
        axis = ('y' if kind == 'vertical' else 'x') if kind != 'triptych' else layout.get('axis', 'x')
        span = None
        if kind != 'overlay':
            span = ((paper[2] - paper[0]) / full_size[0] if axis == 'y'
                    else (paper[3] - paper[1]) / full_size[1])
        warnings = []
        if smallest < minimum_text_px:
            warnings.append({'code': 'small-text-at-view-size',
                             'note': f'预览最小字高约 {smallest:.1f}px；请看实际文字，调整纸幅、素材或结构。'})
        if span is not None and span < 0.55:
            warnings.append({'code': 'narrow-paper-in-panel',
                             'note': '纸张未占到分栏横向/纵向跨度的一半多，检查是否出现突兀的宽空白带。'})
        entries.append({'label': chr(65 + index), 'source_bundle': str(bundle),
                        'source_final_sha256': digest, 'full_size': list(full_size),
                        'preview_file': f'{chr(65 + index)}.png', 'preview_size': list(preview.size),
                        'paper_box_in_preview': [round(v * scale, 2) for v in paper],
                        'estimated_smallest_text_px': round(smallest, 2),
                        'paper_span_fraction': round(span, 4) if span is not None else None,
                        'warnings': warnings})
        previews.append(preview)
    out.mkdir(parents=True)
    columns = min(2, len(previews))
    rows = (len(previews) + columns - 1) // columns
    cell_w, cell_h = size[0] + 32, size[1] + 64
    sheet = Image.new('RGB', (columns * cell_w, rows * cell_h), (247, 247, 245))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)
    for index, (preview, entry) in enumerate(zip(previews, entries)):
        preview.save(out / entry['preview_file'])
        x, y = (index % columns) * cell_w, (index // columns) * cell_h
        label = f"{entry['label']}  {entry['full_size'][0]} x {entry['full_size'][1]}  / min text ~{entry['estimated_smallest_text_px']:.1f}px"
        draw.text((x + 16, y + 14), label, font=font, fill=(50, 50, 45))
        sheet.paste(preview, (x + 16 + (size[0] - preview.width) // 2, y + 48))
    sheet.save(out / 'comparison.png')
    report = {'purpose': 'Viewing-size proof only; full-resolution results remain unchanged.',
              'crop': False, 'view_box': list(size), 'entries': entries,
              'limits': '字高来自配方声明，不是 OCR 测量；提示不能证明文字、情绪或审美合格。'}
    write_json(out / 'report.json', report)
    return {'comparison_image': str(out / 'comparison.png'), 'report': str(out / 'report.json'),
            'previews': [str(out / entry['preview_file']) for entry in entries],
            'warnings': [warning for entry in entries for warning in entry['warnings']]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundles', nargs='+', help='One or more rendered result directories')
    parser.add_argument('--out', required=True)
    parser.add_argument('--width', type=int, default=720)
    parser.add_argument('--height', type=int, default=1080)
    args = parser.parse_args()
    try:
        result = create_previews(args.bundles, args.out, (args.width, args.height))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f'预览失败：{exc}')
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
