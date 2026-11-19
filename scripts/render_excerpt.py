#!/usr/bin/env python3
"""Make an honestly labelled handwriting-style page from a verified new excerpt.

Uses a bundled OFL font and Pillow, never a user's photo or imitation author signature.
The executing agent must establish the source/rights evidence; this script checks its
record and layout but does not turn unchecked declarations into legal verification.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import random
import sys

from PIL import Image, ImageDraw, ImageFont
from collage_core import read_json, require, sha_file, write_json

SKILL=Path(__file__).resolve().parents[1]
FONT=SKILL/'assets/fonts/LongCang-Regular.ttf'
CLOSE='，。！？；：、）》】」』”’…'
OPEN='（《【「『“‘'


def wrap(text,font,width):
    result=[]
    for paragraph in text.split('\n'):
        line=''
        for char in paragraph:
            if line and font.getlength(line+char)>width:
                if char in CLOSE or line[-1] in OPEN:
                    carry=line[-1]
                    result.append(line[:-1])
                    line=carry+char
                else:
                    result.append(line)
                    line=char
            else:
                line+=char
        result.append(line)
    require(''.join(result)==text.replace('\n',''),'换行时文字发生变化。')
    return result


def validate_record(record,text,author,test_only=False):
    require(record.get('text')==text and record.get('author')==author,'出处记录必须逐字对应本次文字和作者。')
    if test_only:
        require(record.get('test_only') is True and record.get('rights',{}).get('basis')=='synthetic-test',
                '测试模式必须明确声明原创测试文字，不能当作文学查证。')
        return
    require(record.get('text_verified') is True and record.get('author_verified') is True,
            '须先核实原文与作者，不可直接使用搜索摘要。')
    require(all(isinstance(record.get(key),str) and record[key].strip()
                for key in ('work','edition_or_locator','verified_by','verified_on')),
            '须记录作品、版本/定位、核实者与日期。')
    date.fromisoformat(record['verified_on'])
    sources=record.get('sources',[])
    require(bool(sources) and all(isinstance(s,dict) and str(s.get('url','')).startswith('https://')
            and s.get('title') for s in sources),'须记录支持原文和归属的直接来源链接。')
    rights=record.get('rights',{})
    require(rights.get('basis') in ('permission','licensed','public-domain','user-original')
            and isinstance(rights.get('evidence'),str) and rights['evidence'].strip(),
            '须记录适用的文本/译文使用依据；短句不自动等于可自由使用。')


def make_page(text,author,record,out,test_only=False):
    require(isinstance(text,str) and text.strip() and len(text)<=600,'请提供不超过 600 字的完整短片段。')
    require(isinstance(author,str) and author.strip() and len(author)<=40,'作者署名不完整或过长。')
    validate_record(record,text,author,test_only)
    require(FONT.is_file(),'缺少随包字体，请修复完整安装。')
    font=ImageFont.truetype(str(FONT),68)
    signature_font=ImageFont.truetype(str(FONT),50)
    label_font=ImageFont.truetype(str(FONT),30)
    missing=font.getmask('\U0010ffff')
    missing_key=(missing.size,bytes(missing))
    for ch in set(text+author+'—— 手写风排印'):
        if not ch.isspace():
            mask=font.getmask(ch)
            require((mask.size,bytes(mask))!=missing_key,f'随包字体缺少字符：{ch}，不能漏字或画方框。')
    width=1206
    margin=100
    lines=wrap(text,font,width-2*margin)
    height=max(800,margin+len(lines)*100+240)
    require(height<=4000,'片段过长，请选择完整但更短的片段；不能截字。')
    rng=random.Random(1729)
    image=Image.new('RGB',(width,height))
    image.putdata([(243+d,235+d,219+d) for d in (rng.choice((-1,0,0,0,1)) for _ in range(width*height))])
    draw=ImageDraw.Draw(image)
    boxes=[]
    for i,line in enumerate(lines):
        if not line:
            continue
        xy=(margin+rng.randint(-1,1),margin+i*100+rng.randint(-1,1))
        draw.text(xy,line,font=font,fill=(44,43,35),anchor='lt')
        boxes.append(list(draw.textbbox(xy,line,font=font,anchor='lt')))
    signature='—— '+author
    sig_width=signature_font.getlength(signature)
    require(sig_width<=width-2*margin,'署名过宽，不能截断。')
    sig_xy=(round(width-margin-sig_width),height-170)
    draw.text(sig_xy,signature,font=signature_font,fill=(44,43,35),anchor='lt')
    sig_box=list(draw.textbbox(sig_xy,signature,font=signature_font,anchor='lt'))
    label='手写风排印'
    label_xy=(margin,height-78)
    draw.text(label_xy,label,font=label_font,fill=(95,88,73),anchor='lt')
    boxes.append(list(draw.textbbox(label_xy,label,font=label_font,anchor='lt')))
    require(all(0<=b[0]<b[2]<=width and 0<=b[1]<b[3]<=height for b in boxes+[sig_box]),'文字越出纸页。')
    out=Path(out).resolve()
    require(not out.exists(),'输出目录已存在，请使用新目录。')
    (out/'handcopies').mkdir(parents=True)
    page=out/'handcopies/external-excerpt.png'
    image.save(page,optimize=True)
    production={'method':'font-render','is_real_handwriting':False,'author_penmanship':False,
        'font':'Long Cang','font_license':'SIL OFL 1.1','font_sha256':sha_file(FONT),
        'disclosure':'手写风排印，非真实手抄或作者亲笔'}
    item={'id':'external-excerpt','image':'handcopies/external-excerpt.png','moods':record.get('moods',[]),
        'expected_transcript':'\n'.join(lines)+'\n'+signature+'\n'+label,
        'asset_kind':'synthetic-test' if test_only else 'typeset-handwriting','production':production,
        'source_verification':record,'rights':record['rights'],
        'regions':[{'kind':'text','box':b} for b in boxes]+[{'kind':'signature','box':sig_box}],
        'smallest_character_px':30,'minimum_character_px':12,'sha256':sha_file(page)}
    write_json(out/'catalog.json',{'schema_version':1,'version':'1.2.0','items':[item]})
    write_json(out/'source-record.json',record)
    return {'assets':str(out),'page':str(page),'is_real_handwriting':False,'production':production}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text-file',required=True)
    parser.add_argument('--author',required=True)
    parser.add_argument('--source-record',required=True)
    parser.add_argument('--out',required=True)
    parser.add_argument('--test-only',action='store_true')
    args=parser.parse_args()
    try:
        report=make_page(Path(args.text_file).read_text(encoding='utf-8').rstrip('\n'),args.author,
                         read_json(args.source_record),args.out,args.test_only)
    except (ValueError,TypeError,OSError,KeyError) as exc:
        print(f'制作失败：{exc}',file=sys.stderr)
        return 1
    print(json.dumps(report,ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
