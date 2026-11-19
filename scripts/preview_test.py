#!/usr/bin/env python3
"""Regression checks for whole-image proofs and readable-size warnings."""
import copy
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw
from collage_core import REVIEW_FIELDS, read_json, render, sha_file, write_json
from finalize import finalize
from make_demo import create_demo
from preview import create_previews


class PreviewTests(unittest.TestCase):
    def test_export_requires_internal_review_then_returns_only_finished_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            recipes = create_demo(root/'fixture')
            assets = root/'fixture/assets'
            render(recipes['vertical'], assets, root/'result')
            create_previews([root/'result'], root/'preview')
            with self.assertRaises(ValueError):
                finalize(root/'result', assets, root/'delivery')
            self.assertFalse((root/'delivery').exists())
            # This is a copyright-clear synthetic fixture, not a review of a real work.
            review = read_json(root/'result/review.json')
            review.update(checked_by='synthetic-regression-test',
                          notes='Only testing export mechanics on procedural test assets.',
                          checks={field:True for field in REVIEW_FIELDS})
            write_json(root/'result/review.json', review)
            result = finalize(root/'result', assets, root/'delivery')
            self.assertTrue(result['delivery_ready'])
            self.assertEqual([path.resolve() for path in (root/'delivery').iterdir()], [Path(result['image'])])
            self.assertEqual(sha_file(result['image']), sha_file(root/'result/final.png'))

    def test_export_rejects_a_preview_of_another_draft(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            recipes = create_demo(root/'fixture')
            assets = root/'fixture/assets'
            render(recipes['vertical'], assets, root/'first')
            render(recipes['horizontal'], assets, root/'second')
            create_previews([root/'first'], root/'preview')
            with self.assertRaises(ValueError):
                finalize(root/'second', assets, root/'delivery')
            self.assertFalse((root/'delivery').exists())

    def test_all_edges_visible_and_source_never_changed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / 'result'
            bundle.mkdir()
            image = Image.new('RGB', (900, 1500), (230, 220, 200))
            draw = ImageDraw.Draw(image)
            corners = [(0, 0, 49, 49), (850, 0, 899, 49),
                       (0, 1450, 49, 1499), (850, 1450, 899, 1499)]
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 0, 255)]
            for box, color in zip(corners, colors):
                draw.rectangle(box, fill=color)
            image.save(bundle / 'final.png')
            before = sha_file(bundle / 'final.png')
            write_json(bundle / 'manifest.json', {
                'artifact_sha256': {'final.png': before},
                'geometry': {'canvas_size': [900, 1500], 'paper_box': [0, 750, 900, 1500],
                             'effective_smallest_character_px': 40},
                'recipe': {'layout': {'type': 'vertical'}}})
            proof = create_previews([bundle], root/'proof', size=(180, 300))
            with Image.open(proof['previews'][0]) as preview:
                self.assertEqual(preview.size, (180, 300))
                points = [(0, 0), (179, 0), (0, 299), (179, 299)]
                self.assertEqual([preview.getpixel(point) for point in points], colors)
            self.assertEqual(sha_file(bundle/'final.png'), before)

    def test_pixel_valid_collage_can_still_have_unreadable_small_paper(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            recipes = create_demo(root/'fixture')
            assets = root/'fixture/assets'
            Image.new('RGB', (2400, 1600), (100, 150, 180)).save(assets/'photos/large.png')
            recipe = copy.deepcopy(recipes['vertical'])
            recipe['photo'].update(image='photos/large.png', look={'preset':'none'})
            report = render(recipe, assets, root/'result')
            self.assertTrue(report['automatic_pass'])
            proof = create_previews([root/'result'], root/'proof')
            codes = {warning['code'] for warning in proof['warnings']}
            self.assertIn('small-text-at-view-size', codes)
            self.assertIn('narrow-paper-in-panel', codes)
            self.assertFalse(report['delivery_ready'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
