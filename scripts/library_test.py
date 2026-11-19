#!/usr/bin/env python3
"""Verify photo-only use, real library integrity, isolation and error behavior."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from PIL import Image
from collage_core import read_json, sha_file, sha_pixels, verify_bundle
from prepare import SKILL, prepare, select_page
from library import ensure_library,materialize_page,ARCHIVE,META


class PhotoOnlyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.photo = self.root / '只上传一张照片 with spaces.png'
        # Synthetic fixture is solely for automated mechanics; it is never a handcopy.
        im = Image.new('RGB', (1206, 800), (95, 146, 184))
        im.paste((180, 150, 86), (250, 300, 830, 750))
        im.save(self.photo)
        self.before = sha_file(self.photo)
        self.catalog = read_json(SKILL/'assets/catalog.json')

    def tearDown(self):
        self.temp.cleanup()

    def test_every_page_photo_only_and_review_gate(self):
        self.assertEqual(len(self.catalog['items']),69)
        local,catalog=ensure_library(self.root/'reference-cache')
        self.assertEqual(sha_file(ARCHIVE),read_json(META)['sha256'])
        self.assertEqual(len(list((local/'references').glob('*.jpg'))),69)
        for page in self.catalog['items']:
            with self.subTest(page=page['id']):
                source=local/page['reference_image']
                self.assertEqual(sha_file(source),page['reference_sha256'])
                crop=page['extraction']['crop_box']
                w,h=crop[2]-crop[0],crop[3]-crop[1]
                for region in page['regions']:
                    l,t,r,b=region['box']
                    self.assertTrue(0<=l<r<=w and 0<=t<b<=h)
                if page['transcript_status']=='ocr-draft-needs-visual-check' or not page.get('ready_for_composition',True):
                    with self.assertRaises(ValueError):
                        prepare(self.photo,self.root/page['id'],paper_id=page['id'])
                    continue
                job = self.root/page['id']
                report = prepare(self.photo, job, paper_id=page['id'])
                self.assertTrue(report['automatic_pass'])
                self.assertFalse(report['delivery_ready'])
                verified = verify_bundle(job/'result', job/'assets')
                self.assertTrue(verified['automatic_pass'])
                self.assertFalse(verified['delivery_ready'])
                with Image.open(self.photo) as original, Image.open(job/'result/photo-native.png') as native:
                    self.assertEqual(sha_pixels(original.convert('RGBA')), sha_pixels(native))
                self.assertEqual(sha_file(self.photo), self.before)
                self.assertTrue((job/'assets'/page['image']).is_file())
                with self.assertRaises(ValueError):
                    verify_bundle(job/'result', job/'assets', require_review=True)

    def test_mood_selection_and_explicit_override(self):
        self.assertEqual(select_page(self.catalog, '爱情,陪伴')['id'], 'companionship')
        self.assertEqual(select_page(self.catalog, '阅读,书房')['id'], 'reading')
        self.assertEqual(select_page(self.catalog, '爱情', 'quiet')['id'], 'quiet')
        with self.assertRaises(ValueError):
            select_page(self.catalog, paper_id='does-not-exist')
        with self.assertRaises(ValueError):
            select_page(self.catalog,'标签完全不相关的内容')

    def test_all_layouts_and_no_grade(self):
        settings=[('horizontal',{}),('vertical',{}),('triptych',{'axis':'y','split_at':300}),
                  ('overlay',{'box':[80,80,1125,740]})]
        for kind,kw in settings:
            with self.subTest(layout=kind):
                job=self.root/kind
                prepare(self.photo,job,paper_id='love-world',layout=kind,no_grade=True,**kw)
                self.assertTrue(verify_bundle(job/'result',job/'assets')['automatic_pass'])
                with Image.open(job/'result/photo-native.png') as native, Image.open(job/'result/photo-graded.png') as graded:
                    self.assertEqual(sha_pixels(native),sha_pixels(graded))

    def test_checksum_failure_does_not_create_workspace(self):
        local=self.root/'library'
        (local/'handcopies').mkdir(parents=True)
        page=copy.deepcopy(next(x for x in self.catalog['items'] if x['id']=='love-world'))
        cache,_=ensure_library(self.root/'reference-cache')
        page=materialize_page(cache,page)
        shutil.copy2(cache/page['image'],local/page['image'])
        (local/page['image']).write_bytes(b'changed')
        (local/'catalog.json').write_text(json.dumps({'version':'test','items':[page]}))
        with self.assertRaises(ValueError):
            prepare(self.photo,self.root/'bad',paper_id=page['id'],library=local)
        self.assertFalse((self.root/'bad').exists())

    def test_never_overwrites_photo_or_workspace(self):
        job=self.root/'existing'
        job.mkdir()
        sentinel=job/'keep.txt'
        sentinel.write_text('keep')
        with self.assertRaises(ValueError):
            prepare(self.photo,job)
        self.assertEqual(sentinel.read_text(),'keep')
        self.assertEqual(sha_file(self.photo),self.before)


if __name__=='__main__':
    unittest.main(verbosity=2)
