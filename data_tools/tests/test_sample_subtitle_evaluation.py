import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('subtitle_sample', ROOT / 'data_tools/sample_subtitle_evaluation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SubtitleSamplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = json.loads((ROOT / 'data_tools/datasets/subtitle_multilingual_pool.json').read_text())

    def test_reproducible_length_balanced_selection_sorted_by_actual_movie_time(self):
        original = copy.deepcopy(self.pool)
        selected, report = module.sample_tasks(self.pool)
        self.assertEqual(self.pool, original)
        self.assertEqual((selected, report), module.sample_tasks(self.pool))
        self.assertNotEqual(report['selected_clip_ids_in_movie_order'], module.sample_tasks(self.pool, seed=1)[1]['selected_clip_ids_in_movie_order'])
        self.assertEqual([s['selected_count'] for s in report['strata']], [16, 24, 40])
        self.assertEqual(len(selected), 480)
        reference_ids = report['selected_clip_ids_in_movie_order']
        self.assertEqual(len(set(reference_ids)), 80)
        pool_by_id = {row['id']: row for row in self.pool}
        for language in ['en', 'vi', 'ka', 'ar', 'hi', 'ru']:
            rows = [row for row in selected if row['language'] == language]
            self.assertEqual([row['clip_id'] for row in rows], reference_ids)
            self.assertEqual([row['clip_index'] for row in rows], list(range(1, 81)))
            starts = [row['metadata']['movie_interval_ms']['start'] for row in rows]
            self.assertEqual(starts, sorted(starts))
            for row in rows:
                original_row = pool_by_id[row['id']]
                self.assertEqual(row['candidates'], original_row['candidates'])
                self.assertEqual(row['post_edit'], original_row['post_edit'])
                self.assertEqual(row['post_edit_origin'], original_row['post_edit_origin'])
                self.assertEqual(row['metadata']['movie_order_index'], original_row['metadata']['movie_order_index'])

    def test_bad_counts_duplicates_and_coverage_are_rejected(self):
        for count in [0, 2, 178, True, 1.5]:
            with self.subTest(count=count), self.assertRaises(ValueError): module.sample_tasks(self.pool, count)
        with self.assertRaises(ValueError): module.sample_tasks(self.pool + [self.pool[0]])
        with self.assertRaises(ValueError): module.sample_tasks(self.pool[1:])
        wrong = copy.deepcopy(self.pool)
        wrong[-1]['source'] += 'changed'
        with self.assertRaises(ValueError): module.sample_tasks(wrong)

    def test_published_selection_matches_seeded_sampler(self):
        expected, report = module.sample_tasks(self.pool)
        actual = json.loads((ROOT / 'public/data/demo/subtitle_multilingual.json').read_text())
        saved_report = json.loads((ROOT / 'public/data/demo/subtitle_multilingual_sample.report.json').read_text())
        self.assertEqual(actual, expected)
        self.assertEqual(saved_report, report)


if __name__ == '__main__':
    unittest.main()
