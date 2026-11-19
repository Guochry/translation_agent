import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('subtitle_split', ROOT / 'data_tools/split_subtitle_evaluation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SubtitleBatchTests(unittest.TestCase):
    def test_movie_timestamps_determine_order_preserving_annotations_and_candidates(self):
        tasks = []
        intervals = {'c': {'start': 300, 'end': 350}, 'a': {'start': 100, 'end': 150}, 'b': {'start': 200, 'end': 250}}
        for language in ['en', 'vi']:
            for index, clip_id in enumerate(['c', 'a', 'b'], 1):
                tasks.append({'id': f'{language}-{clip_id}', 'language': language, 'clip_id': clip_id, 'clip_index': index,
                              'post_edit': 'My improved text', 'post_edit_origin': {'type': 'manual'},
                              'candidates': [{'id': 'system', 'translation_regions': [{'target': clip_id, 'quality_score': 80}]}],
                              'metadata': {'source_interval_ms': {'start': 999-index, 'end': 1000}}})
        before = copy.deepcopy(tasks)
        ordered, parts, order, languages, bounds = module.split_tasks(tasks, (1, 1), intervals)
        self.assertEqual(order, ['a', 'b', 'c'])
        self.assertEqual(languages, ['en', 'vi'])
        self.assertEqual(bounds, [0, 1, 2, 3])
        self.assertEqual(tasks, before)
        originals = {task['id']: task for task in tasks}
        for i, part in enumerate(parts, 1):
            self.assertEqual(len(part), 2)
            for task in part:
                self.assertEqual(task['clip_index'], 1)
                self.assertEqual(task['metadata']['movie_order_index'], i)
                self.assertEqual(task['metadata']['evaluation_batch'], f'part{i}')
                self.assertEqual(task['candidates'], originals[task['id']]['candidates'])
                self.assertEqual(task['post_edit_origin'], originals[task['id']]['post_edit_origin'])
        self.assertEqual(module.chronological_tasks(ordered)[0], ordered)
        self.assertEqual(module.split_tasks(ordered, (1, 1))[1], parts)

    def test_bad_coverage_timestamps_and_splits_are_rejected(self):
        tasks = [{'id': str(i), 'language': 'en', 'clip_id': str(i), 'clip_index': i+1,
                  'metadata': {'movie_interval_ms': {'start': i*100, 'end': i*100+50}}} for i in range(3)]
        for bad in [tasks + [tasks[0]], [{**tasks[0], 'metadata': {}}, *tasks[1:]],
                    [*tasks, {**tasks[0], 'id': 'other', 'language': 'vi'}],
                    [{**tasks[0], 'metadata': {'movie_interval_ms': {'start': 5, 'end': 1}}}, *tasks[1:]]]:
            with self.assertRaises(ValueError): module.split_tasks(bad, (1, 1))
        for sizes in [(0, 1), (2, 1), (1.5, 1)]:
            with self.assertRaises(ValueError): module.split_tasks(tasks, sizes)

    def test_published_batches_cover_all_177_clips_once_in_movie_order(self):
        full = json.loads((ROOT / 'public/data/demo/subtitle_multilingual.json').read_text())
        languages = ['en', 'vi', 'ka', 'ar', 'hi', 'ru']
        for language in languages:
            original = [t for t in full if t['language'] == language]
            merged = []
            for number, count in [(1, 60), (2, 60), (3, 57)]:
                data = json.loads((ROOT / f'public/data/demo/subtitle_multilingual_part{number}.json').read_text())
                rows = [t for t in data if t['language'] == language]
                self.assertEqual(len(rows), count)
                self.assertEqual([t['clip_index'] for t in rows], list(range(1, count+1)))
                merged.extend(rows)
            self.assertEqual([t['id'] for t in merged], [t['id'] for t in original])
            self.assertEqual(len({t['clip_id'] for t in merged}), 177)
            starts = [t['metadata']['movie_interval_ms']['start'] for t in merged]
            self.assertEqual(starts, sorted(starts))
            for a, b in zip(original, merged):
                self.assertEqual(a['candidates'], b['candidates'])
                self.assertEqual(a['post_edit_origin'], b['post_edit_origin'])


if __name__ == '__main__':
    unittest.main()
