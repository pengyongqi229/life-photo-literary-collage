#!/usr/bin/env python3
"""Observable invariant and failure tests using only synthetic fixtures."""
import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageCms
from collage_core import (ARTIFACTS, CollageError, REVIEW_FIELDS, build, difference_pixels,
                          read_json, render, sha_file, verify_bundle, write_json)
from make_demo import create_demo
from photo_look import apply_photo_look, resolve_look


class CollageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="literary-collage-test-")
        cls.root = Path(cls.temp.name)
        cls.recipes = create_demo(cls.root / "fixture")
        cls.assets = cls.root / "fixture" / "assets"

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.config = copy.deepcopy(self.recipes["overlay"])
        self.out = self.root / self._testMethodName

    def assert_bad(self, config=None):
        with self.assertRaises((CollageError, KeyError, TypeError)):
            build(config if config is not None else self.config, self.assets)

    def test_four_layouts_preserve_photo(self):
        for kind, config in self.recipes.items():
            with self.subTest(kind=kind):
                out = self.out / kind
                report = render(config, self.assets, out)
                checks = report["pixel_checks"]
                self.assertEqual(checks["base_reassembled_different_pixels"], 0)
                self.assertEqual(checks["visible_photo_different_pixels"], 0)
                if kind != "overlay":
                    self.assertEqual(checks["covered_photo_pixels"], 0)
                    self.assertEqual(checks["visible_photo_pixels_checked"], 1280 * 900)
                else:
                    self.assertGreater(checks["covered_photo_pixels"], 0)

    def test_source_bytes_unchanged(self):
        files = list(self.assets.rglob("*.png"))
        hashes = {p: sha_file(p) for p in files}
        render(self.config, self.assets, self.out)
        self.assertEqual(hashes, {p: sha_file(p) for p in files})

    def test_caller_unicode_paths(self):
        target = self.assets / "调用者素材"
        target.mkdir(exist_ok=True)
        with Image.open(self.assets / "photos" / "scene.png") as im:
            im.save(target / "生活照.png")
        with Image.open(self.assets / "handcopies" / "landscape.png") as im:
            im.save(target / "完整纸张.png")
        self.config["photo"]["image"] = "调用者素材/生活照.png"
        self.config["paper"]["image"] = "调用者素材/完整纸张.png"
        self.assertTrue(render(self.config, self.assets, self.out)["automatic_pass"])

    def test_vertical_before(self):
        recipe = copy.deepcopy(self.recipes["vertical"])
        recipe["layout"]["paper_side"] = "before"
        self.assertTrue(render(recipe, self.assets, self.out)["automatic_pass"])

    def test_horizontal_after(self):
        recipe = copy.deepcopy(self.recipes["horizontal"])
        recipe["layout"]["paper_side"] = "after"
        self.assertTrue(render(recipe, self.assets, self.out)["automatic_pass"])

    def test_triptych_y_reassembles(self):
        recipe = copy.deepcopy(self.recipes["vertical"])
        recipe["photo"]["protected_regions"] = []
        recipe["layout"] = {"type": "triptych", "axis": "y", "split_at": 430, "panel_size": 370, "margin": 20, "gap": 3}
        self.assertTrue(render(recipe, self.assets, self.out)["automatic_pass"])

    def test_exif_orientation_is_lossless_permutation(self):
        path = self.assets / "photos" / "oriented.jpg"
        im = Image.new("RGB", (900, 1280), (45, 112, 184))
        exif = im.getexif()
        exif[274] = 6
        im.save(path, exif=exif)
        recipe = copy.deepcopy(self.recipes["vertical"])
        recipe["photo"]["image"] = "photos/oriented.jpg"
        render(recipe, self.assets, self.out)
        manifest = read_json(self.out / "manifest.json")
        self.assertEqual(manifest["sources"]["photo"]["stored_size"], [900, 1280])
        self.assertEqual(manifest["sources"]["photo"]["display_size"], [1280, 900])
        self.assertTrue(verify_bundle(self.out, self.assets)["automatic_pass"])

    def test_real_source_holes_preserved(self):
        images, _, _, _, _ = build(self.config, self.assets)
        layer_alpha = images["paper-layer.png"].getchannel("A")
        self.assertEqual(layer_alpha.getextrema()[0], 0)
        # At native size, a source hole stays exactly transparent and border stays visible.
        recipe = copy.deepcopy(self.recipes["vertical"])
        recipe["layout"].update({"panel_size": 400, "margin": 20})
        images, geometry, _, _, _ = build(recipe, self.assets)
        x, y = geometry["paper_box"][:2]
        self.assertEqual(images["paper-layer.png"].getpixel((x + 45, y + 23))[3], 0)
        self.assertEqual(images["paper-layer.png"].getpixel((x, y))[3], 255)

    def test_reject_missing_signature(self):
        self.config["paper"]["regions"] = [r for r in self.config["paper"]["regions"] if r["kind"] != "signature"]
        self.assert_bad()

    def test_reject_out_of_bounds_text(self):
        self.config["paper"]["regions"][0]["box"][2] = 99999
        self.assert_bad()

    def test_reject_clipped_page_container(self):
        self.config["layout"]["box"] = [-1, 0, 600, 300]
        self.assert_bad()

    def test_reject_tiny_characters(self):
        self.config["paper"]["smallest_character_px"] = 2
        self.assert_bad()

    def test_reject_protected_subject_overlap(self):
        self.config["photo"]["protected_regions"] = [[100, 100, 500, 300]]
        self.assert_bad()

    def test_reject_split_through_subject(self):
        recipe = copy.deepcopy(self.recipes["triptych"])
        recipe["layout"]["split_at"] = 900
        self.assert_bad(recipe)

    def test_reject_path_traversal(self):
        self.config["paper"]["image"] = "../outside.png"
        self.assert_bad()

    def test_reject_symlink_escape(self):
        outside = self.root / "outside.png"
        Image.new("RGB", (10, 10)).save(outside)
        target = self.assets / "handcopies" / "escape.png"
        try:
            target.symlink_to(outside)
        except OSError:
            self.skipTest("Symlink creation unavailable on this host")
        self.config["paper"]["image"] = "handcopies/escape.png"
        self.assert_bad()

    def test_reject_overwriting_output(self):
        self.out.mkdir()
        with self.assertRaises(CollageError):
            render(self.config, self.assets, self.out)

    def test_reject_no_rights_evidence(self):
        self.config["paper"]["rights"]["evidence"] = ""
        self.assert_bad()

    def test_reject_cmyk_photo(self):
        Image.new("CMYK", (100, 100)).save(self.assets / "photos" / "cmyk.jpg")
        self.config["photo"]["image"] = "photos/cmyk.jpg"
        self.assert_bad()

    def test_reject_transparent_photo(self):
        Image.new("RGBA", (100, 100), (1, 2, 3, 128)).save(self.assets / "photos" / "alpha.png")
        self.config["photo"]["image"] = "photos/alpha.png"
        self.assert_bad()

    def test_reject_different_embedded_icc(self):
        srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        lab = ImageCms.ImageCmsProfile(ImageCms.createProfile("LAB")).tobytes()
        with Image.open(self.assets / "photos" / "scene.png") as im:
            im.save(self.assets / "photos" / "profile.png", icc_profile=srgb)
        with Image.open(self.assets / "handcopies" / "landscape.png") as im:
            im.save(self.assets / "handcopies" / "profile.png", icc_profile=lab)
        self.config["photo"]["image"] = "photos/profile.png"
        self.config["paper"]["image"] = "handcopies/profile.png"
        self.assert_bad()

    def test_rgba_difference_detects_rgb_change_with_same_alpha(self):
        first = Image.new("RGBA", (3, 3), (10, 20, 30, 255))
        second = first.copy()
        second.putpixel((1, 1), (11, 20, 30, 255))
        self.assertEqual(difference_pixels(first, second), 1)

    def test_detect_final_tampering_even_with_updated_hash(self):
        render(self.config, self.assets, self.out)
        with Image.open(self.out / "final.png") as im:
            changed = im.copy()
        changed.putpixel((0, 0), (0, 0, 0, 255))
        changed.save(self.out / "final.png")
        manifest = read_json(self.out / "manifest.json")
        manifest["artifact_sha256"]["final.png"] = sha_file(self.out / "final.png")
        write_json(self.out / "manifest.json", manifest)
        with self.assertRaises(CollageError):
            verify_bundle(self.out, self.assets)

    def test_detect_inflated_mask_even_with_updated_hash(self):
        render(self.config, self.assets, self.out)
        with Image.open(self.out / "coverage-mask.png") as im:
            Image.new("L", im.size, 255).save(self.out / "coverage-mask.png")
        manifest = read_json(self.out / "manifest.json")
        manifest["artifact_sha256"]["coverage-mask.png"] = sha_file(self.out / "coverage-mask.png")
        write_json(self.out / "manifest.json", manifest)
        with self.assertRaises(CollageError):
            verify_bundle(self.out, self.assets)

    def test_detect_source_change(self):
        path = self.assets / "photos" / "mutable.png"
        with Image.open(self.assets / "photos" / "scene.png") as im:
            im.save(path)
        self.config["photo"]["image"] = "photos/mutable.png"
        render(self.config, self.assets, self.out)
        Image.new("RGB", (1280, 900)).save(path)
        with self.assertRaises(CollageError):
            verify_bundle(self.out, self.assets)

    def test_detect_changed_output_icc_even_with_updated_hash(self):
        render(self.config, self.assets, self.out)
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        with Image.open(self.out / "final.png") as im:
            changed = im.copy()
        changed.save(self.out / "final.png", icc_profile=profile)
        manifest = read_json(self.out / "manifest.json")
        manifest["artifact_sha256"]["final.png"] = sha_file(self.out / "final.png")
        write_json(self.out / "manifest.json", manifest)
        with self.assertRaises(CollageError):
            verify_bundle(self.out, self.assets)

    def test_output_strips_exif_but_keeps_photo_pixels(self):
        path = self.assets / "photos" / "exif.jpg"
        im = Image.new("RGB", (1280, 900), (45, 112, 184))
        exif = im.getexif()
        exif[270] = "Synthetic private metadata test"
        im.save(path, exif=exif)
        self.config["photo"]["image"] = "photos/exif.jpg"
        render(self.config, self.assets, self.out)
        for name in ARTIFACTS:
            with Image.open(self.out / name) as output:
                self.assertFalse(output.getexif())
        self.assertTrue(verify_bundle(self.out, self.assets)["automatic_pass"])

    def test_manual_review_required(self):
        report = render(self.config, self.assets, self.out)
        self.assertFalse(report["delivery_ready"])
        with self.assertRaises(CollageError):
            verify_bundle(self.out, self.assets, require_review=True)
        review = read_json(self.out / "review.json")
        review.update({"checked_by": "synthetic test assertion only", "checks": {key: True for key in REVIEW_FIELDS}})
        write_json(self.out / "review.json", review)
        self.assertTrue(verify_bundle(self.out, self.assets, require_review=True)["delivery_ready"])

    def test_cli_failure_removes_stale_success_report(self):
        render(self.config, self.assets, self.out)
        # Force an old report to look successful; the failed command must replace it.
        write_json(self.out / "verification.json", {"automatic_pass": True, "delivery_ready": True})
        with (self.out / "final.png").open("ab") as stream:
            stream.write(b"tampering")
        proc = subprocess.run([sys.executable, str(Path(__file__).with_name("verify.py")),
                               str(self.out), "--assets", str(self.assets)], capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(read_json(self.out / "verification.json")["delivery_ready"])

    def test_cli_manual_pending_reports_automatic_pass(self):
        render(self.config, self.assets, self.out)
        proc = subprocess.run([sys.executable, str(Path(__file__).with_name("verify.py")),
                               str(self.out), "--assets", str(self.assets), "--require-review"], capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(self.out / "verification.json")
        self.assertTrue(report["automatic_pass"])
        self.assertFalse(report["delivery_ready"])

    def test_default_look_preserves_native_and_records_changed_colors(self):
        report = render(self.config, self.assets, self.out)
        self.assertEqual(report["photo_processing"]["preset"], "japanese-film")
        self.assertGreater(report["pixel_checks"]["native_to_graded_different_pixels"], 0)
        self.assertEqual(report["pixel_checks"]["comparison_baseline"], "photo-graded.png")
        with Image.open(self.assets / "photos/scene.png") as source, Image.open(self.out / "photo-native.png") as native:
            self.assertEqual(difference_pixels(source.convert("RGBA"), native), 0)

    def test_disable_look_is_exact_for_all_layouts(self):
        for name, base in self.recipes.items():
            recipe = copy.deepcopy(base)
            recipe["photo"]["look"] = {"preset": "none"}
            report = render(recipe, self.assets, self.out / name)
            self.assertEqual(report["pixel_checks"]["native_to_graded_different_pixels"], 0)
            self.assertFalse(report["photo_processing"]["pixel_values_may_change"])

    def test_zero_strength_is_identity(self):
        image = Image.new("RGBA", (20, 20), (65, 120, 195, 255))
        graded, _ = apply_photo_look(image, {"strength": 0})
        self.assertEqual(difference_pixels(image, graded), 0)

    def test_default_look_is_gentle_and_keeps_yellow_blue_separation(self):
        image = Image.new("RGBA", (512, 1))
        image.putdata([(r, g, b, 255) for r in range(0, 256, 36)
                       for g in range(0, 256, 36) for b in range(0, 256, 36)])
        graded, record = apply_photo_look(image, {"grain": 0})
        self.assertLessEqual(record["max_channel_delta"], 16)
        swatches = Image.new("RGBA", (4, 1))
        swatches.putdata([(225, 180, 40, 255), (35, 100, 190, 255), (0, 0, 0, 255), (255, 255, 255, 255)])
        result, _ = apply_photo_look(swatches, {"grain": 0})
        yellow, blue, black, white = [result.getpixel((x, 0)) for x in range(4)]
        self.assertGreater(yellow[0], yellow[1]); self.assertGreater(yellow[1], yellow[2])
        self.assertGreater(blue[2], blue[1]); self.assertGreater(blue[1], blue[0])
        self.assertGreater(max(yellow[:3]) - min(yellow[:3]), 0.85 * 185)
        self.assertGreater(max(blue[:3]) - min(blue[:3]), 0.85 * 155)
        self.assertTrue(all(0 < value < 10 for value in black[:3]))
        self.assertTrue(all(value >= 250 for value in white[:3]))
        self.assertEqual(graded.size, image.size)

    def test_grain_is_seeded_and_monochrome(self):
        original = Image.new("RGBA", (80, 80), (128, 128, 128, 255))
        first, _ = apply_photo_look(original, {"seed": 1})
        same, _ = apply_photo_look(original, {"seed": 1})
        other, _ = apply_photo_look(original, {"seed": 2})
        no_grain, _ = apply_photo_look(original, {"grain": 0})
        self.assertEqual(difference_pixels(first, same), 0)
        self.assertGreater(difference_pixels(first, other), 0)
        diff = ImageChops.difference(first, no_grain)
        self.assertEqual(diff.getchannel("R").tobytes(), diff.getchannel("G").tobytes())
        self.assertEqual(diff.getchannel("G").tobytes(), diff.getchannel("B").tobytes())

    def test_look_does_not_touch_paper_layer(self):
        original_recipe = copy.deepcopy(self.config)
        original_recipe["photo"]["look"] = {"preset": "none"}
        unchanged, _, _, _, _ = build(original_recipe, self.assets)
        graded, _, _, _, _ = build(self.config, self.assets)
        self.assertEqual(difference_pixels(unchanged["paper-layer.png"], graded["paper-layer.png"]), 0)

    def test_reject_invalid_look_parameters(self):
        for look in ({"preset": "unknown"}, {"strength": -0.1}, {"strength": 1.1},
                     {"strength": float("nan")}, {"grain": True}, {"seed": -1},
                     {"seed": 1.2}, {"seed": 2**32}, {"unexpected": 1}, "film"):
            with self.subTest(look=look), self.assertRaises(ValueError):
                resolve_look(look)

    def test_detect_graded_layer_tampering_with_updated_hash(self):
        render(self.config, self.assets, self.out)
        path = self.out / "photo-graded.png"
        with Image.open(path) as source:
            tampered = source.copy()
        tampered.putpixel((0, 0), (0, 0, 0, 255)); tampered.save(path)
        manifest = read_json(self.out / "manifest.json")
        manifest["artifact_sha256"]["photo-graded.png"] = sha_file(path)
        write_json(self.out / "manifest.json", manifest)
        with self.assertRaises(CollageError):
            verify_bundle(self.out, self.assets)

    def test_detect_forged_look_record(self):
        render(self.config, self.assets, self.out)
        manifest = read_json(self.out / "manifest.json")
        manifest["photo_processing"]["strength"] = 0.9
        write_json(self.out / "manifest.json", manifest)
        with self.assertRaises(CollageError):
            verify_bundle(self.out, self.assets)


if __name__ == "__main__":
    unittest.main(verbosity=2)
