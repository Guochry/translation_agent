import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

spec=importlib.util.spec_from_file_location('prepare_candidates',Path(__file__).resolve().parents[1]/'prepare_multilingual_comparison.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class MultilingualComparisonPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        self.key='book/ja/004.jpg'
        original=self.source/'originals/book__004.jpg';original.parent.mkdir();Image.new('RGB',(8,9),'white').save(original)
        original_hash=module.sha(original)
        self.original={'page_id':'book:5','page_index':5,'original_image':self.key,'regions':[
            {'region_id':'r1','text_ja':'日本語','text_bounding_box':[0,0,3,4]}]}
        self.write(self.source/'originals/book__004.json',self.original)
        (self.root/'public').mkdir();(self.root/'public/original.jpg').write_bytes(original.read_bytes())
        self.baseline=[dict(id='old:en:page',language='en',language_label='English',page_key=self.key,
            original_image='public/original.jpg',translated_image='baseline.jpg',reference_texts=['Japanese'],reference_texts_ja=['日本語'],
            metadata=dict(original_sha256=original_hash,translated_sha256='baseline'),translation_regions=[dict(id='b1',source='日本語',target='Japanese',quality_score=70,presentation_score=80,edits=[{'id':1}])])]
        self.basepath=self.root/'baseline.json';self.write(self.basepath,self.baseline)
        render=self.source/'gpt/en/book__004.png';render.parent.mkdir(parents=True);Image.new('RGB',(8,9),'red').save(render)
        document=dict(profile='gpt',model='gpt',target_language='en',status='completed',original_dataset_image=self.key,
            page_id='book:5',page_index=5,regions=[dict(region_id='r1',text_ja='日本語',text_translated='Japanese',rendered_text='JAPANESE',
            text_bounding_box=[0,0,3,4],render_status='rendered')])
        text_path=self.source/'gpt/en/book__004.json';self.write(text_path,document)
        self.manifest=dict(scope={'profiles':['gpt','qwen'],'languages':['en']},originals=[dict(text_json='originals/book__004.json',image='originals/book__004.jpg',sha256=original_hash)],
            images=[dict(profile='gpt',target_language='en',original_dataset_image=self.key,image='gpt/en/book__004.png',
            text_json='gpt/en/book__004.json',text_json_sha256=module.sha(text_path),sha256=module.sha(render))],
            missing_pages=[dict(profile='qwen',target_language='en',original_dataset_image=self.key,reason='Missing render')])
        self.write(self.source/'manifest.json',self.manifest)
    def write(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False))
    def run_converter(self):
        with patch.object(module,'ROOT',self.root),patch('builtins.print'):
            return module.prepare(self.source,self.basepath,workers=1)
    def test_preserves_pixels_exact_sources_missing_outputs_and_stable_candidate_order(self):
        tasks=self.run_converter();self.assertEqual(len(tasks),1)
        candidates={c['id']:c for c in tasks[0]['candidates']};self.assertEqual(set(candidates),{'baseline','gpt','qwen'})
        self.assertFalse(candidates['qwen']['available']);self.assertIsNone(candidates['qwen']['translated_image'])
        region=candidates['gpt']['translation_regions'][0];self.assertEqual(region['source'],'日本語');self.assertEqual(region['target'],'Japanese');self.assertEqual(region['rendered_text'],'JAPANESE')
        self.assertEqual(region['source_alignment'],'exact_annotation');self.assertIsNone(region['quality_score']);self.assertIsNone(region['presentation_score'])
        self.assertIsNone(candidates['baseline']['translation_regions'][0]['quality_score']);self.assertEqual(candidates['baseline']['translation_regions'][0]['edits'],[])
        with Image.open(self.source/'gpt/en/book__004.png') as source,Image.open(self.root/candidates['gpt']['translated_image']) as packed:
            self.assertEqual(source.convert('RGBA').tobytes(),packed.convert('RGBA').tobytes())
        self.assertEqual(tasks,self.run_converter())
        self.assertEqual(json.loads(self.basepath.read_text()),self.baseline)
    def test_rejects_altered_source_text_and_unaccounted_missing_pages(self):
        text=self.source/'gpt/en/book__004.json';d=json.loads(text.read_text());d['regions'][0]['text_ja']='違う';self.write(text,d)
        self.manifest['images'][0]['text_json_sha256']=module.sha(text);self.write(self.source/'manifest.json',self.manifest)
        with self.assertRaisesRegex(ValueError,'Japanese text'):self.run_converter()
        d['regions'][0]['text_ja']='日本語';self.write(text,d);self.manifest['images'][0]['text_json_sha256']=module.sha(text);self.manifest['missing_pages']=[];self.write(self.source/'manifest.json',self.manifest)
        with self.assertRaisesRegex(ValueError,'account for every'):self.run_converter()
