import copy
import unittest
from data_tools.export_manga_source_alignments import enrich_document
from data_tools.manga_source_alignment import fingerprint


class ExportJapaneseAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.task = dict(id='task', language='ar', page_key='book/ja/004.jpg',
            reference_texts_ja=['一', '二'], reference_texts=['One', 'Two'],
            metadata=dict(original_sha256='original', translated_sha256='translated'),
            translation_regions=[dict(id='ar:1', target='اثنان'), dict(id='ar:2', target='واحد')])
        self.document = dict(model='existing-transcriber', usage={'total': 123}, pages=[dict(
            image='book/ja/004.jpg', image_sha256='translated', status='complete', text='اثنان\n\nواحد',
            notes='Original notes', regions=[dict(text='اثنان', kind='dialogue', uncertain=False),
                                            dict(text='واحد', kind='dialogue', uncertain=True)])])
        self.records = {'task': dict(model='matcher', fingerprint=fingerprint(self.task), regions=[
            dict(region_id='ar:1', source_indices=[1], status='matched'),
            dict(region_id='ar:2', source_indices=[], status='unmatched')])}

    def test_adds_japanese_without_changing_extraction_or_input(self):
        before=copy.deepcopy(self.document)
        updated=enrich_document('ar',self.document,[self.task],self.records)
        self.assertEqual(self.document,before)
        page=updated['pages'][0]
        self.assertEqual(page['regions'][0]['source_text'],'二')
        self.assertEqual(page['regions'][1]['source_text'],'')
        self.assertEqual(page['regions'][1]['source_alignment'],'unmatched')
        for field in ['image','image_sha256','status','text','notes']:
            self.assertEqual(page[field],before['pages'][0][field])
        for index,region in enumerate(before['pages'][0]['regions']):
            for field,value in region.items(): self.assertEqual(page['regions'][index][field],value)
        self.assertEqual(updated['usage'],before['usage'])
        self.assertEqual(updated,enrich_document('ar',updated,[self.task],self.records))

    def test_rejects_changed_translation_and_stale_mapping(self):
        self.document['pages'][0]['regions'][0]['text']='Changed'
        with self.assertRaisesRegex(ValueError,'translation text differs'):
            enrich_document('ar',self.document,[self.task],self.records)
        self.document['pages'][0]['regions'][0]['text']='اثنان'
        self.records['task']['fingerprint']='stale'
        with self.assertRaisesRegex(ValueError,'Stale'):
            enrich_document('ar',self.document,[self.task],self.records)

    def test_failed_extraction_remains_failed_without_invented_regions(self):
        self.task['translation_regions']=None
        self.document['pages'][0]={'image':'book/ja/004.jpg','status':'error','error':'Original error'}
        updated=enrich_document('ar',self.document,[self.task],{})['pages'][0]
        self.assertNotIn('regions',updated)
        self.assertEqual(updated['status'],'error')
        self.assertEqual(updated['error'],'Original error')
        self.assertEqual(updated['japanese_alignment']['status'],'extraction_unavailable')
        self.assertEqual(updated['reference_texts_ja'],['一','二'])
