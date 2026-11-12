import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('multilingual_packager', Path(__file__).resolve().parents[1] / 'prepare_manga_multilingual.py')
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class MultilingualPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.key = 'book/ja/004.jpg'
        original, digest = self.image(self.source / 'originals' / self.key, b'original image')
        self.write(self.source / 'manifest.json', {'pages': [{'id': self.key, 'original': 'originals/' + self.key, 'sha256': digest}]})
        self.refs = self.root / 'references.json'
        self.write(self.refs, [{'book_title': 'book', 'pages': [{'image_paths': {'ja': 'images/' + self.key},
                    'text': [{'text_ja': 'こんにちは', 'text_en': 'Hello'}]}]}])
        for code, text in [('en', 'Hello'), ('ar', 'مرحبا'), ('ka', 'გამარჯობა')]:
            _, digest = self.image(self.source / code / self.key, code.encode())
            page = {'image': self.key, 'manga': 'book', 'page_index': 4, 'image_sha256': digest,
                    'status': 'complete', 'regions': [{'text': text, 'kind': 'dialogue', 'uncertain': True}]}
            self.write(self.source / code / 'translated_text.json', {'model': 'transcriber', 'pages': [page]})
        self.languages = [(code, code.upper(), code) for code in ['en', 'ar', 'ka']]

    def image(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path, hashlib.sha256(content).hexdigest()

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False))

    def run_converter(self):
        with patch.object(converter, 'ROOT', self.root), patch.object(converter, 'LANGUAGES', self.languages), patch('builtins.print'):
            return converter.prepare(self.source, self.refs)

    def test_language_identity_text_and_byte_preservation(self):
        tasks = self.run_converter()
        self.assertEqual([h['language'] for h in tasks], ['en', 'ar', 'ka'])
        self.assertEqual(len({h['id'] for h in tasks}), 3)
        self.assertEqual(len({h['original_image'] for h in tasks}), 1)
        self.assertEqual(tasks[1]['translation_regions'][0]['target'], 'مرحبا')
        self.assertEqual(tasks[0]['metadata']['page_index'], 5)
        for hit in tasks:
            self.assertEqual((self.root / hit['translated_image']).read_bytes(), hit['language'].encode())
            self.assertEqual(hit['reference_texts_ja'], ['こんにちは'])
            self.assertIsNone(hit['fidelity_score'])
            self.assertIsNone(hit['translation_regions'][0]['quality_score'])
            self.assertEqual(hit['translation_regions'][0]['edits'], [])
        self.assertFalse((self.root / 'public/evaluation_assets').exists())
        self.assertEqual(tasks, self.run_converter())

    def test_failed_extraction_is_unavailable_instead_of_empty_completed_text(self):
        self.write(self.source / 'ka/translated_text.json', {'pages': [{'image': self.key, 'status': 'error', 'error': 'Failed extraction'}]})
        tasks = self.run_converter()
        self.assertIsNone(tasks[2]['translation_regions'])
        self.assertEqual(tasks[2]['metadata']['transcription_status'], 'unavailable')
        self.assertTrue((self.root / tasks[2]['translated_image']).is_file())

    def test_image_hash_mismatch_fails_before_copying(self):
        (self.source / 'ar' / self.key).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.run_converter()
        self.assertFalse((self.root / 'evaluation_assets').exists())

    def test_incomplete_language_coverage_is_rejected(self):
        self.write(self.source / 'ar/translated_text.json', {'pages': []})
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.run_converter()
