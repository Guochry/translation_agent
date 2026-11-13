import copy
import unittest
from data_tools.split_multilingual_comparison import split_tasks


class SplitComparisonTests(unittest.TestCase):
    def make_tasks(self):
        return [dict(id=f'{language}:{index}',language=language,page_key=f'book/ja/{index:03d}.jpg',
                     metadata={'page_index':index+1},candidates=[{'id':'baseline','fidelity_score':60}])
                for language in ['en','ar'] for index in range(5)]

    def test_consecutive_batches_preserve_identity_order_annotations_and_input(self):
        tasks=self.make_tasks();before=copy.deepcopy(tasks)
        parts,total,languages=split_tasks(tasks,3)
        self.assertEqual(total,5);self.assertEqual(languages,['en','ar'])
        self.assertEqual([len(part) for part in parts],[6,4])
        self.assertFalse({h['id'] for h in parts[0]} & {h['id'] for h in parts[1]})
        self.assertEqual({h['id'] for part in parts for h in part},{h['id'] for h in tasks})
        for language in languages:
            self.assertEqual([h['page_key'] for h in parts[0] if h['language']==language],[f'book/ja/{i:03d}.jpg' for i in range(3)])
            self.assertEqual([h['metadata']['original_task_index'] for h in parts[1] if h['language']==language],[4,5])
        self.assertTrue(all(h['candidates'][0]['fidelity_score']==60 for part in parts for h in part))
        self.assertEqual(tasks,before)

    def test_different_language_order_duplicate_ids_and_empty_batches_are_rejected(self):
        tasks=self.make_tasks();tasks[-1],tasks[-2]=tasks[-2],tasks[-1]
        with self.assertRaisesRegex(ValueError,'order or coverage'):split_tasks(tasks,3)
        tasks=self.make_tasks();tasks[1]['id']=tasks[0]['id']
        with self.assertRaisesRegex(ValueError,'Duplicate task'):split_tasks(tasks,3)
        for count in [0,5]:
            with self.assertRaisesRegex(ValueError,'at least one'):split_tasks(self.make_tasks(),count)
