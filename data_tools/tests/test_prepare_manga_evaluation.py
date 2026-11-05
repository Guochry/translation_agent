"""Fixture-based checks for matching, preservation, and invalid-input handling."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


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
        self.rendered = self.root / "rendered"
        self.public = self.root / "public"
        self.output = self.public / "data/demo/manga_translation.json"
        self.assets = self.public / "data/manga/test_run"
        self.dataset.mkdir()
        self.rendered.mkdir()
        (self.dataset / "LICENSE.md").write_text("Dataset license\n", encoding="utf-8")
        self.books = [{"book_title": "example_book", "pages": []}]

    def page(self, stem="009", page_index=10, references=None, rendered=True):
        path = self.dataset / "images/example_book/ja" / f"{stem}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"original JPEG bytes\x00\xff" + stem.encode())
        self.books[0]["pages"].append({
            "page_index": page_index,
            "image_paths": {"ja": f"images/example_book/ja/{stem}.jpg"},
            "text": [{"text_en": reference} for reference in (references if references is not None else ["Hello!"])],
        })
        if rendered:
            self.render(stem)
        return path

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
        self.assertEqual(json.loads(self.output.read_text()), tasks)
        self.assertEqual(json.loads(self.output.with_suffix(".report.json").read_text()), report)

    def test_preserves_reference_order_newlines_unicode_and_empty_page(self):
        self.page("001", 2, ["second\nline", "  日本語 & <reference>  ", ""])
        self.page("000", 1, [])
        tasks, report = self.prepare()
        self.assertEqual([task["metadata"]["page_index"] for task in tasks], [1, 2])
        self.assertEqual(tasks[0]["reference_texts"], [])
        self.assertEqual(tasks[1]["reference_texts"], ["second\nline", "  日本語 & <reference>  ", ""])
        self.assertEqual(report["reference_text_count"], 3)
        self.assertEqual(report["pages_without_reference_text"], 1)

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

    def test_rejects_source_directory_as_destination(self):
        self.page()
        self.output = self.dataset / "output.json"
        with self.assertRaisesRegex(ValueError, "inside either source directory"):
            self.prepare()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
