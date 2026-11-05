"""Fixture-based checks for matching, preservation, and invalid-input handling."""

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "prepare_manga_evaluation.py"
SPEC = importlib.util.spec_from_file_location("prepare_manga_evaluation", SCRIPT)
manga = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manga)


class PrepareMangaEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dataset = self.root / "dataset"
        self.results = self.root / "results"
        self.rendered = self.results / "rendered_results"
        self.public = self.root / "public"
        self.output = self.public / "data/demo/manga_translation.json"
        self.assets = self.public / "data/manga/test_run"
        self.dataset.mkdir()
        self.rendered.mkdir(parents=True)
        (self.dataset / "LICENSE.md").write_text("Dataset license\n", encoding="utf-8")
        self.books = [{"book_title": "example_book", "pages": []}]

    def page(self, stem="009", page_index=10, references=None, rendered=True, japanese_references=None,
             translation_regions=None, reading_order=None):
        path = self.dataset / "images/example_book/ja" / f"{stem}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"original JPEG bytes\x00\xff" + stem.encode())
        references = references if references is not None else ["Hello!"]
        if japanese_references is None:
            japanese_references = ["こんにちは！"] * len(references)
        self.assertEqual(len(references), len(japanese_references))
        self.books[0]["pages"].append({
            "page_index": page_index,
            "image_paths": {"ja": f"images/example_book/ja/{stem}.jpg"},
            "text": [
                {"text_en": reference, "text_ja": japanese}
                for reference, japanese in zip(references, japanese_references)
            ],
        })
        if rendered:
            self.render(stem)
            self.result(stem, page_index, path, translation_regions, reading_order)
        return path

    def result_path(self, page_index=10, subrun="run_001"):
        return self.results / subrun / "pages/example_book" / str(page_index) / "result.json"

    def result(self, stem, page_index, original, regions=None, reading_order=None):
        path = self.result_path(page_index)
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered_image = path.parent / "rendered.png"
        rendered_image.write_bytes((self.rendered / "example_book" / f"{stem}.png").read_bytes())
        if regions is None:
            regions = [{
                "id": f"example_book:{page_index}:d0001", "source_text": "検出した日本語",
                "translation": "  Exact\ntranslation!  ", "bbox": [1, 2, 10, 20],
                "class_name": "text", "layout": {"display_text": "EXACT TRANSLATION!"},
            }]
        path.write_text(json.dumps({
            "status": "completed",
            "page": {
                "series": "example_book", "index": page_index, "image_path": str(original),
                "rendered_image": str(rendered_image), "regions": regions, "reading_order": reading_order,
            },
        }), encoding="utf-8")
        return path

    def update_result(self, update, page_index=10):
        path = self.result_path(page_index)
        value = json.loads(path.read_text(encoding="utf-8"))
        update(value)
        path.write_text(json.dumps(value), encoding="utf-8")

    def render(self, stem, extension="png"):
        path = self.rendered / "example_book" / f"{stem}.{extension}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"translated PNG bytes\x00\xff" + stem.encode())
        return path

    def prepare(self):
        (self.dataset / "annotation.json").write_text(json.dumps(self.books), encoding="utf-8")
        return manga.prepare(
            self.dataset, self.rendered, "test_run", self.output, self.assets,
            public_root=self.public,
        )

    def test_matches_filename_instead_of_page_index_and_copies_exact_bytes(self):
        original = self.page("009", page_index=10)
        original_bytes = original.read_bytes()
        translated = self.rendered / "example_book/009.png"
        translated_bytes = translated.read_bytes()
        tasks, report = self.prepare()
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task["id"], "openmantra:test_run:example_book:009")
        self.assertEqual(task["metadata"], {
            "book_title": "example_book", "page_index": 10,
            "run_id": "test_run", "filename_stem": "009",
            "agent_result_path": "run_001/pages/example_book/10/result.json",
            "translation_order": "region_order",
        })
        self.assertEqual(task["original_image"], "data/manga/test_run/original/example_book/009.jpg")
        self.assertEqual(task["translated_image"], "data/manga/test_run/translated/example_book/009.png")
        self.assertEqual((self.public / task["original_image"]).read_bytes(), original_bytes)
        self.assertEqual((self.public / task["translated_image"]).read_bytes(), translated_bytes)
        self.assertEqual(original.read_bytes(), original_bytes)
        self.assertEqual(translated.read_bytes(), translated_bytes)
        self.assertEqual((self.assets / "LICENSE.md").read_bytes(), (self.dataset / "LICENSE.md").read_bytes())
        self.assertIsNone(task["fidelity_score"])
        self.assertIsNone(task["presentation_score"])
        self.assertEqual(task["edits"], [])
        self.assertEqual(task["translation_regions"], [{
            "id": "example_book:10:d0001", "source": "検出した日本語",
            "target": "  Exact\ntranslation!  ", "bbox": [1, 2, 10, 20],
            "kind": "text", "quality_score": None, "edits": [],
        }])
        self.assertEqual(json.loads(self.output.read_text()), tasks)
        self.assertEqual(json.loads(self.output.with_suffix(".report.json").read_text()), report)

    def test_preserves_reference_order_newlines_unicode_and_empty_page(self):
        self.page(
            "001", 2, ["second\nline", "  日本語 & <reference>  ", ""],
            japanese_references=["二番目\nの行", "", "  原文 & <参照>  "],
        )
        self.page("000", 1, [])
        tasks, report = self.prepare()
        self.assertEqual([task["metadata"]["page_index"] for task in tasks], [1, 2])
        self.assertEqual(tasks[0]["reference_texts"], [])
        self.assertEqual(tasks[0]["reference_texts_ja"], [])
        self.assertEqual(tasks[1]["reference_texts"], ["second\nline", "  日本語 & <reference>  ", ""])
        self.assertEqual(tasks[1]["reference_texts_ja"], ["二番目\nの行", "", "  原文 & <参照>  "])
        self.assertEqual(list(zip(tasks[1]["reference_texts_ja"], tasks[1]["reference_texts"])), [
            ("二番目\nの行", "second\nline"),
            ("", "  日本語 & <reference>  "),
            ("  原文 & <参照>  ", ""),
        ])
        self.assertEqual(report["reference_text_count"], 3)
        self.assertEqual(report["japanese_reference_text_count"], 3)
        self.assertEqual(report["empty_japanese_reference_text_count"], 1)
        self.assertEqual(report["pages_without_reference_text"], 1)

    def test_reuses_unchanged_image_and_license_assets(self):
        self.page()
        self.prepare()
        with patch.object(manga.shutil, "copyfile", side_effect=AssertionError("Unchanged asset was copied")):
            self.prepare()

    def test_preserves_generated_text_and_applies_explicit_reading_order(self):
        first = {
            "id": "example_book:10:d0001", "source_text": "一番\n最初", "translation": "First\nline",
            "bbox": [10, 20, 30, 40], "class_name": "text", "layout": {"display_text": "FIRST LINE"},
        }
        second = {
            "id": "example_book:10:d0002", "source_text": "二番目", "translation": "  <second> & next  ",
            "bbox": [40, 50, 60, 70], "class_name": "onomatopoeia",
        }
        self.page(translation_regions=[first, second], reading_order=[second["id"], first["id"]])
        tasks, report = self.prepare()
        task = tasks[0]
        self.assertEqual([region["id"] for region in task["translation_regions"]], [second["id"], first["id"]])
        self.assertEqual([region["target"] for region in task["translation_regions"]], ["  <second> & next  ", "First\nline"])
        self.assertEqual(task["metadata"]["translation_order"], "reading_order")
        self.assertEqual(report["translated_region_count"], 2)
        self.assertEqual(report["pages_without_generated_text"], 0)

    def test_permits_empty_generated_regions_with_existing_human_reference(self):
        self.page(translation_regions=[])
        tasks, report = self.prepare()
        self.assertEqual(tasks[0]["translation_regions"], [])
        self.assertEqual(tasks[0]["reference_texts"], ["Hello!"])
        self.assertEqual(report["translated_region_count"], 0)
        self.assertEqual(report["pages_without_generated_text"], 1)

    def test_rejects_missing_or_unfinished_result_for_published_image(self):
        self.page()
        self.update_result(lambda result: result.update(status="unfinished"))
        with self.assertRaisesRegex(ValueError, "Missing completed result"):
            self.prepare()
        self.result_path().unlink()
        with self.assertRaisesRegex(ValueError, "Missing completed result"):
            self.prepare()
        self.assertFalse(self.public.exists())

    def test_rejects_duplicate_completed_result(self):
        self.page()
        duplicate = self.result_path(subrun="run_002")
        duplicate.parent.mkdir(parents=True)
        shutil.copyfile(self.result_path(), duplicate)
        with self.assertRaisesRegex(ValueError, "Duplicate completed result identity"):
            self.prepare()
        self.assertFalse(self.public.exists())

    def test_rejects_result_for_wrong_page_index(self):
        self.page()
        self.update_result(lambda result: result["page"].update(index=9))
        with self.assertRaisesRegex(ValueError, "result page index"):
            self.prepare()
        self.assertFalse(self.public.exists())

    def test_rejects_result_render_with_different_bytes(self):
        self.page()
        result = json.loads(self.result_path().read_text())
        Path(result["page"]["rendered_image"]).write_bytes(b"different rendered image")
        with self.assertRaisesRegex(ValueError, "rendered image mismatch"):
            self.prepare()
        self.assertFalse(self.public.exists())

    def test_rejects_invalid_region_fields_and_reading_order(self):
        self.page()
        original = self.result_path().read_text()
        updates = [
            (lambda page: page["regions"].append(page["regions"][0].copy()), "duplicate generated region id"),
            (lambda page: page["regions"][0].update(translation=None), "string translation"),
            (lambda page: page["regions"][0].update(source_text=None), "string source_text"),
            (lambda page: page["regions"][0].update(bbox=[10, 20, 1, 2]), "valid bbox"),
            (lambda page: page.update(reading_order=["unknown-region"]), "reading_order"),
        ]
        for update, expected in updates:
            with self.subTest(expected=expected):
                self.result_path().write_text(original)
                self.update_result(lambda result: update(result["page"]))
                with self.assertRaisesRegex(ValueError, expected):
                    self.prepare()
                self.assertFalse(self.public.exists())

    def test_reports_missing_render_without_creating_task(self):
        self.page("000", 1)
        self.page("004", 5, rendered=False)
        tasks, report = self.prepare()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(report["source_pages"], 2)
        self.assertEqual(report["matched_pages"], 1)
        self.assertEqual(report["missing_render_count"], 1)
        self.assertEqual(report["missing_rendered_pages"][0]["filename_stem"], "004")
        self.assertFalse((self.assets / "original/example_book/004.jpg").exists())

    def test_rejects_duplicate_source_before_writing_output(self):
        self.page()
        self.books[0]["pages"].append(self.books[0]["pages"][0].copy())
        with self.assertRaisesRegex(ValueError, "Duplicate source identity"):
            self.prepare()
        self.assertFalse(self.public.exists())

    def test_rejects_duplicate_render_before_writing_output(self):
        self.page()
        self.render("009", "jpg")
        with self.assertRaisesRegex(ValueError, "Duplicate rendered identity"):
            self.prepare()
        self.assertFalse(self.public.exists())

    def test_rejects_unknown_render_before_writing_output(self):
        self.page()
        self.render("unknown")
        with self.assertRaisesRegex(ValueError, "Unknown rendered image"):
            self.prepare()
        self.assertFalse(self.public.exists())

    def test_rejects_missing_original(self):
        self.page().unlink()
        with self.assertRaisesRegex(ValueError, "Missing or invalid original image"):
            self.prepare()
        self.assertFalse(self.public.exists())

    def test_rejects_invalid_reference(self):
        self.page(references=[None])
        with self.assertRaisesRegex(ValueError, "string text_en"):
            self.prepare()
        self.assertFalse(self.public.exists())

    def test_rejects_invalid_or_missing_japanese_reference(self):
        self.page(japanese_references=[None])
        with self.assertRaisesRegex(ValueError, "string text_ja"):
            self.prepare()
        self.assertFalse(self.public.exists())
        del self.books[0]["pages"][0]["text"][0]["text_ja"]
        with self.assertRaisesRegex(ValueError, "string text_ja"):
            self.prepare()
        self.assertFalse(self.public.exists())

    def test_rejects_source_directory_as_destination(self):
        self.page()
        self.output = self.dataset / "output.json"
        with self.assertRaisesRegex(ValueError, "inside any source directory"):
            self.prepare()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
