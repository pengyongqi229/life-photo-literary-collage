#!/usr/bin/env python3
"""Paper-surface embedding invariants, using only procedural non-private assets."""
import copy
from pathlib import Path
import random
import tempfile
import unittest

from PIL import Image, ImageDraw, ImageFont
from collage_core import (build, check_pixels, read_json, render, resource_limits,
                          review_fields, sha_file, sha_pixels, verify_bundle, write_json)
from finalize import finalize
from paper_frame import plan_frame
from prepare import prepare
from preview import create_previews


def create_frame_fixture(root):
    root = Path(root)
    (root/'photos').mkdir(parents=True)
    (root/'handcopies').mkdir()
    grain = Image.frombytes('L', (960,960), random.Random(81).randbytes(960*960))
    paper = Image.merge('RGB', [grain.point([base + v%7 for v in range(256)])
                                for base in (235,225,205)])
    draw = ImageDraw.Draw(paper)
    font = ImageFont.load_default(size=26)
    draw.text((342,350), 'SYNTHETIC TEST PAGE', font=font, fill=(40,40,35))
    draw.text((342,395), 'A quiet afternoon.', font=font, fill=(40,40,35))
    draw.text((342,440), 'NOT HANDWRITING', font=font, fill=(40,40,35))
    draw.text((405,532), '- Test author', font=font, fill=(40,40,35))
    paper.save(root/'handcopies/page.png')
    photo = Image.new('RGB', (240,160), (95,145,180))
    d = ImageDraw.Draw(photo)
    for box,color in [((0,0,35,35),(240,60,50)),((205,0,239,35),(60,200,90)),
                      ((0,125,35,159),(70,70,225)),((205,125,239,159),(220,160,50))]:
        d.rectangle(box,fill=color)
    photo.save(root/'photos/input.png')
    config = {'schema_version':1,'photo':{'image':'photos/input.png'},
              'paper':{'image':'handcopies/page.png','asset_kind':'synthetic-test',
                       'expected_transcript':'SYNTHETIC TEST PAGE\nA quiet afternoon.\nNOT HANDWRITING\n- Test author',
                       'regions':[{'kind':'text','box':[330,340,635,485]},
                                  {'kind':'signature','box':[395,520,620,570]}],
                       'smallest_character_px':24,'minimum_character_px':12,
                       'rights':{'basis':'synthetic-test','evidence':'Original procedural fixture only.'}},
              'layout':{'type':'paper-frame','mode':'embed','canvas_size':[960,960],
                        'paper_xy':[0,0],'photo_xy':[60,380],'photo_side':'left',
                        'border':40,'text_clearance':12}}
    return config


class PaperFrameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='paper-frame-test-')
        self.root = Path(self.temp.name)
        self.assets = self.root/'assets'
        self.config = create_frame_fixture(self.assets)

    def tearDown(self):
        self.temp.cleanup()

    def extension(self, side='right'):
        config = copy.deepcopy(self.config)
        positions = {'left':[40,420],'right':[1250,420], 'top':[500,40], 'bottom':[500,1000]}
        config['layout'].update(mode='extend',canvas_size=[1600,1200],paper_xy=[100,100],
                                photo_side=side,photo_xy=positions[side],
                                extension={'sample_box':[20,20,300,300],
                                           'blank_sample_confirmed':True,'seed':1729})
        return config

    def assert_pixels(self, images, geometry):
        with Image.open(self.assets/'handcopies/page.png') as paper:
            preserved = images['paper-surface.png'].crop(geometry['paper_box'])
            self.assertEqual(sha_pixels(preserved),sha_pixels(paper.convert('RGBA')))
        box = geometry['paper_frame']['photo_box']
        self.assertEqual(sha_pixels(images['final.png'].crop(box)),sha_pixels(images['photo-graded.png']))
        report = check_pixels(images, geometry)
        self.assertEqual(report['visible_photo_different_pixels'],0)
        self.assertEqual(report['covered_photo_pixels'],0)
        self.assertTrue(report['text_and_signature_pixels_unchanged_by_embedding'])

    def test_all_four_relations_embed_and_extend_without_touching_text_or_photo(self):
        positions = {'left':[60,380],'right':[650,380],'top':[350,80],'bottom':[350,700]}
        before = {str(p):sha_file(p) for p in self.assets.rglob('*.png')}
        for mode in ('embed','extend'):
            for side,xy in positions.items():
                with self.subTest(mode=mode,side=side):
                    config = self.extension(side) if mode=='extend' else copy.deepcopy(self.config)
                    if mode=='embed':config['layout'].update(photo_side=side,photo_xy=xy)
                    images, geometry, *_ = build(config,self.assets)
                    self.assert_pixels(images,geometry)
        self.assertEqual(before,{str(p):sha_file(p) for p in self.assets.rglob('*.png')})

    def test_no_grade_mode_keeps_all_native_photo_pixels(self):
        config = self.extension()
        config['photo']['look']={'preset':'none'}
        images,geometry,*_ = build(config,self.assets)
        self.assertEqual(sha_pixels(images['photo-native.png']),sha_pixels(images['photo-graded.png']))
        self.assert_pixels(images,geometry)

    def test_extended_texture_uses_the_same_scale_as_the_complete_paper(self):
        config=self.extension('left')
        config['layout'].update(canvas_size=[2400,2200],paper_xy=[300,100],photo_xy=[70,900],paper_scale=2)
        config['paper']['allow_upscale']=True
        images,geometry,*_=build(config,self.assets)
        provenance=geometry['paper_frame']['texture_extension']
        self.assertEqual(provenance['texture_work_size'],[1200,1100])
        self.assertEqual(provenance['output_scale'],[2,2])
        self.assertEqual(provenance['original_page_scale'],[2,2])
        with Image.open(self.assets/'handcopies/page.png') as paper:
            expected=paper.convert('RGBA').resize((1920,1920),Image.Resampling.LANCZOS)
        self.assertEqual(sha_pixels(images['paper-surface.png'].crop(geometry['paper_box'])),sha_pixels(expected))
        photo_box=geometry['paper_frame']['photo_box']
        self.assertEqual(sha_pixels(images['final.png'].crop(photo_box)),sha_pixels(images['photo-graded.png']))

    def test_rejects_text_coverage_bad_sampling_clipped_page_and_missing_paper_border(self):
        cases=[]
        c=copy.deepcopy(self.config);c['layout']['photo_xy']=[350,350];cases.append(c)
        c=copy.deepcopy(self.config);c['layout']['photo_xy']=[0,380];cases.append(c)
        c=copy.deepcopy(self.config);c['layout']['canvas_size']=[950,950];cases.append(c)
        c=self.extension();c['layout']['extension']['sample_box']=[350,350,550,470];cases.append(c)
        c=self.extension();c['layout']['extension']['blank_sample_confirmed']=False;cases.append(c)
        c=self.extension();c['layout']['extension']['sample_box']=[20,20,21,300];cases.append(c)
        c=self.extension();c['layout']['photo_side']='top';cases.append(c)
        for index,config in enumerate(cases):
            with self.subTest(case=index),self.assertRaises(ValueError):build(config,self.assets)

    def test_extension_is_reproducible_and_seed_does_not_change_original_page(self):
        config=self.extension()
        a,ga,*_=build(config,self.assets)
        b,gb,*_=build(config,self.assets)
        self.assertEqual(sha_pixels(a['paper-surface.png']),sha_pixels(b['paper-surface.png']))
        self.assertEqual(ga,gb)
        config['layout']['extension']['seed']=919
        c,gc,*_=build(config,self.assets)
        self.assertNotEqual(sha_pixels(a['paper-surface.png']),sha_pixels(c['paper-surface.png']))
        self.assert_pixels(c,gc)
        self.assertEqual(ga['paper_frame']['texture_extension']['sample_box'],[20,20,300,300])

    def test_rebuild_detects_tampered_texture_even_with_updated_file_hash(self):
        out=self.root/'result'
        render(self.extension(),self.assets,out)
        with Image.open(out/'paper-surface.png') as original:
            changed=original.copy()
        changed.putpixel((1,1),(0,0,0,255));changed.save(out/'paper-surface.png')
        m=read_json(out/'manifest.json')
        m['artifact_sha256']['paper-surface.png']=sha_file(out/'paper-surface.png')
        write_json(out/'manifest.json',m)
        with self.assertRaises(ValueError):verify_bundle(out,self.assets)

    def test_large_native_photo_can_be_planned_with_explicit_resource_budget(self):
        layout={'type':'paper-frame','mode':'extend','canvas_size':[7600,6000],
                'paper_xy':[6300,4800],'photo_xy':[500,400],'photo_side':'top','border':100,
                'extension':{'sample_box':[20,650,300,790],'blank_sample_confirmed':True}}
        boxes=[[50,50,1100,550],[700,600,1100,700]]
        cfg={'smallest_character_px':24}
        with self.assertRaises(ValueError):
            plan_frame((6000,4000),(1206,805),layout,boxes,cfg,resource_limits({}))
        limits=resource_limits({'resources':{'max_canvas_pixels':80_000_000,'max_working_memory_mb':8192}})
        plan=plan_frame((6000,4000),(1206,805),layout,boxes,cfg,limits)
        self.assertEqual([plan['photo_box'][2]-plan['photo_box'][0],plan['photo_box'][3]-plan['photo_box'][1]],[6000,4000])
        limits['max_working_memory_mb']=1
        with self.assertRaises(ValueError):plan_frame((6000,4000),(1206,805),layout,boxes,cfg,limits)
        with self.assertRaises(ValueError):resource_limits({'resources':{'max_canvas_pixels':121_000_000}})

    def test_prepare_preview_and_finished_export_require_extension_visual_review(self):
        config=self.extension()
        page=copy.deepcopy(config['paper'])
        page.update(id='test',moods=['安静'],sha256=sha_file(self.assets/page['image']),
                    source_verification={'status':'synthetic-test'})
        write_json(self.assets/'catalog.json',{'version':'test','items':[page]})
        job=self.root/'job'
        prepared=prepare(self.assets/'photos/input.png',job,library=self.assets,
                         paper_id='test',layout='paper-frame',frame=config['layout'])
        self.assertTrue(prepared['automatic_pass'])
        self.assertTrue(Path(prepared['preview_image']).is_file())
        review=read_json(job/'result/review.json')
        review.update(checked_by='synthetic-regression-test',notes='Procedural test assets only.')
        review['checks']={field:True for field in review_fields(config)}
        review['checks']['paper_extension_natural']=False
        write_json(job/'result/review.json',review)
        with self.assertRaises(ValueError):finalize(job/'result',job/'assets',self.root/'delivery')
        self.assertFalse((self.root/'delivery').exists())
        review['checks']['paper_extension_natural']=True
        write_json(job/'result/review.json',review)
        result=finalize(job/'result',job/'assets',self.root/'delivery')
        self.assertEqual(sha_file(result['image']),sha_file(job/'result/final.png'))


if __name__=='__main__':unittest.main(verbosity=2)
