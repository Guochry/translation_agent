import copy
import unittest
from data_tools.manga_source_alignment import apply_alignment, fingerprint


class SourceAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.hit = dict(id='example', page_key='book/ja/004.jpg', language='ar',
                        reference_texts_ja=['最初', '次', '最後'], reference_texts=['First','Next','Last'],
                        translation_regions=[dict(id='ar:1', target='الأخير', quality_score=0, edits=[]), dict(id='ar:2', target='الأول', quality_score=50, edits=[])])
        self.record = dict(fingerprint=fingerprint(self.hit), regions=[
            dict(region_id='ar:1', source_indices=[2], status='matched'),
            dict(region_id='ar:2', source_indices=[0,1], status='uncertain')])

    def test_semantic_reordering_and_multiple_sources_preserve_annotations(self):
        result = apply_alignment(self.hit, self.record)
        self.assertEqual(result['translation_regions'][0]['source'], '最後')
        self.assertEqual(result['translation_regions'][1]['source'], '最初\n次')
        self.assertEqual(result['translation_regions'][0]['quality_score'], 0)
        self.assertEqual(result['translation_regions'][1]['source_alignment'], 'uncertain')
        self.assertEqual(fingerprint(result), self.record['fingerprint'])

    def test_rejects_stale_text_invalid_indices_and_missing_regions(self):
        for mutate in [lambda r:r.update(fingerprint='stale'),
                       lambda r:r['regions'][0].update(source_indices=[3]),
                       lambda r:r['regions'].pop(),
                       lambda r:r['regions'][0].update(source_indices=[]),
                       lambda r:r['regions'][1].update(region_id='ar:1')]:
            record=copy.deepcopy(self.record);mutate(record)
            with self.assertRaises(ValueError): apply_alignment(copy.deepcopy(self.hit),record)

    def test_unmatched_sources_are_explicit_without_invented_japanese(self):
        self.record['regions'][0].update(source_indices=[],status='unmatched')
        result=apply_alignment(self.hit,self.record)
        self.assertEqual(result['translation_regions'][0]['source'],'')
        self.assertEqual(result['translation_regions'][0]['source_alignment'],'unmatched')

    def test_blank_japanese_reference_cannot_appear_as_a_confirmed_source(self):
        self.hit['reference_texts_ja'][2] = ''
        self.record['fingerprint'] = fingerprint(self.hit)
        result = apply_alignment(self.hit, self.record)
        self.assertEqual(result['translation_regions'][0]['source'], '')
        self.assertEqual(result['translation_regions'][0]['source_reference_indices'], [])
        self.assertEqual(result['translation_regions'][0]['source_alignment'], 'unmatched')
