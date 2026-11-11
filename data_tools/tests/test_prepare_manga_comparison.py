import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / 'prepare_manga_comparison.py'
spec = importlib.util.spec_from_file_location('prepare_manga_comparison', MODULE_PATH)
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class ComparisonPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.baseline = self.root / 'baseline'
        self.baseline.mkdir()
        image = self.baseline / 'book__ja__000__hash.jpg'
        image.write_bytes(b'fixture image')
        self.page = dict(manga='book', page_index=0, image=image.name, status='complete',
                         image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                         regions=[dict(text='Baseline wording', kind='dialogue', uncertain=True)], notes='Uncertain wording')
        self.hit = dict(id='openmantra:run:book:000', original_image='source.jpg', translated_image='agent.png',
                        reference_texts=['Hello'], reference_texts_ja=['こんにちは'],
                        metadata=dict(book_title='book', filename_stem='000', page_index=1),
                        translation_regions=[dict(id='r1', source='こんにちは', target='Hello', quality_score=90, edits=[{'id': 1}])])
        output = self.root / 'public/data/demo'
        output.mkdir(parents=True)
        missing = dict(self.hit, id='openmantra:run:book:001', metadata=dict(book_title='book', filename_stem='001', page_index=2))
        (output / 'manga_translation.json').write_text(json.dumps([self.hit, missing]))
        self.write_baseline([self.page])

    def write_baseline(self, pages):
        (self.baseline / 'translated_text.json').write_text(json.dumps(dict(pages=pages)))

    def run_converter(self):
        with patch.object(converter, 'ROOT', self.root), patch('builtins.print'):
            return converter.prepare(self.baseline)

    def test_intersection_identity_and_independent_blank_ratings(self):
        tasks = self.run_converter()
        self.assertEqual(len(tasks), 1)
        by_id = {c['id']: c for c in tasks[0]['candidates']}
        self.assertEqual(set(by_id), {'agent', 'baseline'})
        self.assertEqual(by_id['agent']['translation_regions'][0]['source'], 'こんにちは')
        self.assertNotIn('source', by_id['baseline']['translation_regions'][0])
        self.assertTrue(by_id['baseline']['translation_regions'][0]['uncertain'])
        self.assertEqual(by_id['baseline']['metadata']['text_origin'], 'image_transcription')
        self.assertEqual((self.root / 'public' / by_id['baseline']['translated_image']).read_bytes(), b'fixture image')
        for candidate in by_id.values():
            self.assertIsNone(candidate['fidelity_score'])
            self.assertIsNone(candidate['presentation_score'])
            self.assertIsNone(candidate['translation_regions'][0]['quality_score'])
            self.assertEqual(candidate['translation_regions'][0]['edits'], [])
        self.assertEqual(tasks, self.run_converter())
        report = json.loads((self.root / 'public/data/demo/manga_comparison.report.json').read_text())
        self.assertEqual(report['excluded_agent_pages'], ['openmantra:run:book:001'])
        original = json.loads((self.root / 'public/data/demo/manga_translation.json').read_text())
        self.assertEqual(original[0]['translation_regions'][0]['quality_score'], 90)

    def test_rejects_changed_images(self):
        (self.baseline / self.page['image']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed baseline image'):
            self.run_converter()

    def test_rejects_duplicate_page_identity(self):
        self.write_baseline([self.page, self.page])
        with self.assertRaisesRegex(ValueError, 'Duplicate baseline page'):
            self.run_converter()
