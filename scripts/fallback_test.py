#!/usr/bin/env python3
"""Exercise external-page layout mechanics without inventing literary attribution."""
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from collage_core import sha_file,verify_bundle
from render_excerpt import make_page,validate_record,wrap,FONT
from prepare import prepare
from PIL import ImageFont


class ExcerptTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.text='这是一段原创测试文字，\n用来检查完整排版。'
        self.record={'test_only':True,'text':self.text,'author':'测试作者',
            'rights':{'basis':'synthetic-test','evidence':'程序原创测试文字，不是文学摘句。'}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_complete_page_can_compose_with_photo_only_inputs(self):
        result=make_page(self.text,'测试作者',self.record,self.root/'page',test_only=True)
        self.assertFalse(result['is_real_handwriting'])
        photo=self.root/'photo.png'
        Image.new('RGB',(1206,800),(170,180,190)).save(photo)
        before=sha_file(photo)
        job=self.root/'job'
        prepared=prepare(photo,job,paper_id='external-excerpt',library=result['assets'])
        self.assertTrue(prepared['automatic_pass'])
        self.assertFalse(prepared['delivery_ready'])
        self.assertTrue(verify_bundle(job/'result',job/'assets')['automatic_pass'])
        self.assertEqual(before,sha_file(photo))

    def test_unverified_external_source_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_record({'text':self.text,'author':'测试作者'},self.text,'测试作者')
        with self.assertRaises(ValueError):
            make_page(self.text,'错误作者',self.record,self.root/'bad',test_only=True)
        self.assertFalse((self.root/'bad').exists())

    def test_wrap_preserves_every_character(self):
        font=ImageFont.truetype(str(FONT),68)
        text='完整保留文字，标点也完整。下一行不能少字！'
        lines=wrap(text,font,350)
        self.assertEqual(''.join(lines),text)
        self.assertTrue(all(font.getlength(line)<=350 for line in lines))


if __name__=='__main__':
    unittest.main(verbosity=2)
