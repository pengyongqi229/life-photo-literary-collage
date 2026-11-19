"""A complete real handcopy page surrounding an unscaled photo; no generated paper."""
from __future__ import annotations

import math
import random

from PIL import Image, ImageChops, ImageOps, ImageStat
from collage_core import (check_box, check_resource_budget, integer, number,
                          opaque_background, require, safe_size, sha_pixels)


def intersects(a, b, clearance=0):
    return (a[0] < b[2] + clearance and a[2] > b[0] - clearance
            and a[1] < b[3] + clearance and a[3] > b[1] - clearance)


def pair(value, name):
    require(isinstance(value, list) and len(value) == 2, f'{name} 须为两个整数。')
    return tuple(integer(v, name) for v in value)


def plan_frame(photo_size, paper_size, layout, region_boxes, paper_cfg, limits):
    canvas = pair(layout['canvas_size'], 'layout.canvas_size')
    photo_xy = pair(layout['photo_xy'], 'layout.photo_xy')
    paper_xy = pair(layout.get('paper_xy', [0, 0]), 'layout.paper_xy')
    border = integer(layout.get('border', 24), 'layout.border', 1)
    clearance = integer(layout.get('text_clearance', 12), 'layout.text_clearance')
    scale = number(layout.get('paper_scale', 1), 'layout.paper_scale', 0.01, 8)
    allow = paper_cfg.get('allow_upscale', False)
    require(type(allow) is bool and (scale <= 1 or allow),
            '放大整张手抄须显式设置 paper.allow_upscale: true 并复核字迹。')
    page_size = tuple(max(1, round(v * scale)) for v in paper_size)
    sx, sy = page_size[0] / paper_size[0], page_size[1] / paper_size[1]
    page_box = list(paper_xy) + [paper_xy[0] + page_size[0], paper_xy[1] + page_size[1]]
    photo_box = list(photo_xy) + [photo_xy[0] + photo_size[0], photo_xy[1] + photo_size[1]]
    check_box(page_box, canvas, '完整原手抄页')
    check_box(photo_box, canvas, '完整照片')
    require(photo_box[0] >= border and photo_box[1] >= border
            and canvas[0] - photo_box[2] >= border and canvas[1] - photo_box[3] >= border,
            '照片四周必须留出真实纸面，不能贴到画布边缘。')
    mapped = [[paper_xy[0] + math.floor(b[0] * sx), paper_xy[1] + math.floor(b[1] * sy),
               paper_xy[0] + math.ceil(b[2] * sx), paper_xy[1] + math.ceil(b[3] * sy)]
              for b in region_boxes]
    require(not any(intersects(photo_box, b, clearance) for b in mapped),
            '照片或安全间距覆盖了文字/标点/署名；换位置或纸页，不能抹字。')
    side = layout['photo_side']
    require(side in ('left', 'right', 'top', 'bottom'), 'photo_side 须为 left/right/top/bottom。')
    relationships = {'left': all(photo_box[2] + clearance <= b[0] for b in mapped),
                     'right': all(photo_box[0] - clearance >= b[2] for b in mapped),
                     'top': all(photo_box[3] + clearance <= b[1] for b in mapped),
                     'bottom': all(photo_box[1] - clearance >= b[3] for b in mapped)}
    require(relationships[side], 'photo_side 与照片/完整文字实际位置不符。')
    mode = layout.get('mode', 'embed')
    require(mode in ('embed', 'extend'), 'paper-frame.mode 须为 embed 或 extend。')
    if mode == 'embed':
        require(paper_xy == (0, 0) and canvas == page_size,
                'embed 须直接使用整张原纸作为画布；需要延展时明确使用 extend。')
    else:
        extension = layout.get('extension', {})
        require(extension.get('blank_sample_confirmed') is True,
                '延展纸面前必须看图确认采样区没有文字、标点、署名或其他印记。')
        sample = check_box(extension['sample_box'], paper_size, 'extension.sample_box')
        require(min(sample[2]-sample[0], sample[3]-sample[1]) >= 64,
                '无字纹理采样区至少 64×64；请换更适合的原纸，不采字迹或生成纸纹。')
        require(not any(intersects(sample, b, 8) for b in region_boxes),
                '纹理采样区触及文字/署名安全区；不可复制文字到延展纸面。')
    smallest = number(paper_cfg['smallest_character_px'], 'paper.smallest_character_px', 1, max(paper_size))
    minimum = number(paper_cfg.get('minimum_character_px', 12), 'paper.minimum_character_px', 8, 200)
    require(smallest * min(sx, sy) >= minimum, '完整手抄字迹过小，请调整整页纸幅或换素材。')
    estimate = check_resource_budget(canvas, photo_size, paper_size, limits)
    texture_work_size = None
    if mode == 'extend':
        texture_work_size = [math.ceil(canvas[0]/sx), math.ceil(canvas[1]/sy)]
        safe_size(*texture_work_size, limits['max_canvas_pixels'])
        estimate += 8 * math.prod(texture_work_size)
        require(estimate <= limits['max_working_memory_mb'] * 1024**2,
                '纸纹工作画布超过内存预算；调整整纸比例/纸页或按宿主资源配置预算，不缩小照片。')
    return {'canvas_size': list(canvas), 'paper_box': page_box, 'paper_size': list(page_size),
            'paper_scale': [sx, sy], 'photo_box': photo_box, 'photo_xy': list(photo_xy),
            'mapped_boxes': mapped, 'effective_smallest_character_px': smallest * min(sx, sy),
            'mode': mode, 'photo_side': side, 'border': border,
            'texture_work_size': texture_work_size,
            'estimated_working_bytes': estimate}


def quilt_texture(paper, size, extension):
    """Overlap only real blank-paper samples, with deterministic offset/flip selection."""
    box = check_box(extension['sample_box'], paper.size, 'extension.sample_box')
    sample = paper.crop(box)
    require(sample.getchannel('A').getextrema() == (255, 255), '纹理采样区不能含透明孔洞。')
    seed = integer(extension.get('seed', 1729), 'extension.seed')
    require(seed < 2**32, 'extension.seed 超出范围。')
    requested = integer(extension.get('patch_size', 192), 'extension.patch_size', 32)
    require(requested <= 1024, 'patch_size 上限为 1024。')
    patch = min(requested, sample.width // 2, sample.height // 2)
    require(patch >= 32, '纹理采样区太小。')
    overlap = min(integer(extension.get('overlap', 32), 'extension.overlap', 4), patch // 3)
    step = patch - overlap
    rng = random.Random(seed)
    surface = Image.new('RGBA', size, (0, 0, 0, 0))
    count = 0
    for y in range(0, size[1], step):
        for x in range(0, size[0], step):
            width, height = min(patch, size[0]-x), min(patch, size[1]-y)
            target = surface.crop((x, y, x+width, y+height))
            best, best_score = None, None
            for _ in range(6):
                left, top = rng.randrange(sample.width-patch+1), rng.randrange(sample.height-patch+1)
                candidate = sample.crop((left, top, left+patch, top+patch))
                if rng.randrange(2): candidate = ImageOps.mirror(candidate)
                if rng.randrange(2): candidate = ImageOps.flip(candidate)
                candidate = candidate.crop((0, 0, width, height))
                score = 0
                if x:
                    strip = (0, 0, min(overlap, width), height)
                    score += sum(ImageStat.Stat(ImageChops.difference(candidate.crop(strip).convert('RGB'), target.crop(strip).convert('RGB'))).mean)
                if y:
                    strip = (0, 0, width, min(overlap, height))
                    score += sum(ImageStat.Stat(ImageChops.difference(candidate.crop(strip).convert('RGB'), target.crop(strip).convert('RGB'))).mean)
                if best_score is None or score < best_score: best, best_score = candidate, score
            mask = Image.new('L', (width, height), 255)
            if x:
                ramp = Image.new('L', (width, 1))
                ramp.putdata([round(255*min(1, i/overlap)) for i in range(width)])
                mask = ImageChops.darker(mask, ramp.resize((width, height)))
            if y:
                ramp = Image.new('L', (1, height))
                ramp.putdata([round(255*min(1, i/overlap)) for i in range(height)])
                mask = ImageChops.darker(mask, ramp.resize((width, height)))
            # Never blend against unfilled transparent pixels at the first row/column.
            mask = ImageChops.lighter(mask, ImageOps.invert(target.getchannel('A')))
            surface.paste(best, (x, y), mask)
            count += 1
    provenance = {'method': 'overlap-real-paper-patches-v1', 'sample_box': list(box),
                  'sample_pixel_sha256': sha_pixels(sample), 'seed': seed,
                  'sample_mean_rgb': [round(v, 3) for v in ImageStat.Stat(sample.convert('RGB')).mean],
                  'patch_size': patch, 'overlap': overlap, 'patch_count': count,
                  'source_file_modified': False, 'whole_page_preserved': True,
                  'blankness_check': 'Agent visual confirmation plus declared text/signature exclusion; not OCR.'}
    return surface, provenance


def render_frame(photo, native, paper, config, boxes, photo_meta, paper_meta, icc, processing, limits):
    layout, paper_cfg = config['layout'], config['paper']
    require(layout.get('gap', 0) == 0, 'paper-frame 用纸面留白，不使用分栏 gap。')
    require(paper_cfg.get('opacity', 1) == paper_cfg.get('ink_opacity', 1) == 1,
            '整页纸底须保留原纸，不能用透明度把纸或字淡掉。')
    plan = plan_frame(photo.size, paper.size, layout, boxes, paper_cfg, limits)
    page_size = tuple(plan['paper_size'])
    page = paper.resize(page_size, Image.Resampling.LANCZOS) if page_size != paper.size else paper.copy()
    provenance = None
    if plan['mode'] == 'extend':
        work_size = tuple(plan['texture_work_size'])
        surface, provenance = quilt_texture(paper, work_size, layout['extension'])
        target_size = tuple(plan['canvas_size'])
        if work_size != target_size:
            surface = surface.resize(target_size, Image.Resampling.LANCZOS)
        provenance.update(texture_work_size=list(work_size), output_size=list(target_size),
                          output_scale=[target_size[0]/work_size[0], target_size[1]/work_size[1]],
                          original_page_scale=plan['paper_scale'], texture_scale_follows_paper=True)
    else:
        surface = Image.new('RGBA', tuple(plan['canvas_size']), (0, 0, 0, 0))
    # Copy the complete page after texture construction. No source-page pixel is
    # quilted, erased, split into text blocks, or blended away.
    surface.paste(page, tuple(plan['paper_box'][:2]))
    require(surface.getchannel('A').crop(plan['photo_box']).getextrema() == (255, 255),
            '照片覆盖区含透明孔洞或缺失纸面，请换真实留白位置。')
    base = Image.new('RGBA', surface.size, opaque_background(config.get('background', [240,235,221])))
    base.paste(photo, tuple(plan['photo_xy']))
    layer = surface.copy()
    layer.paste((0, 0, 0, 0), tuple(plan['photo_box']))
    coverage = layer.getchannel('A').point([0]+[255]*255)
    final = Image.alpha_composite(base, layer)
    mapped = [{'kind': region['kind'], 'source_box': list(source), 'output_box': target}
              for region, source, target in zip(paper_cfg['regions'], boxes, plan['mapped_boxes'])]
    geometry = {'canvas_size': plan['canvas_size'], 'paper_box': plan['paper_box'],
                'paper_scale': plan['paper_scale'],
                'effective_smallest_character_px': plan['effective_smallest_character_px'],
                'regions': mapped,
                'photo_tiles': [{'source_box': [0,0,photo.width,photo.height], 'destination': plan['photo_xy']}],
                'paper_frame': {'mode': plan['mode'], 'photo_side': plan['photo_side'],
                                'photo_box': plan['photo_box'], 'source_page_box': plan['paper_box'],
                                'border': plan['border'], 'texture_extension': provenance,
                                'resource_limits': limits, 'estimated_working_bytes': plan['estimated_working_bytes']}}
    images = {'final.png': final, 'photo-native.png': native, 'photo-graded.png': photo,
              'photo-base.png': base, 'paper-layer.png': layer,
              'paper-surface.png': surface, 'coverage-mask.png': coverage}
    return images, geometry, {'photo':photo_meta,'paper':paper_meta}, icc, processing
