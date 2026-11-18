import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('subtitle_packager', Path(__file__).parents[1] / 'prepare_subtitle_evaluation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SubtitlePackagingTests(unittest.TestCase):
    def test_srt_unicode_multiline_and_boundaries(self):
        cues = module.parse_srt('\ufeff1\r\n00:00:00,125 --> 00:00:02,500\r\nمرحبا\r\nبالعالم\r\n\r\n2\r\n00:00:02,500 --> 00:00:05,590\r\nदुनिया\r\n')
        self.assertEqual(cues[0]['target'], 'مرحبا\nبالعالم')
        self.assertEqual(cues[0]['start_seconds'], .125)
        self.assertEqual(cues[1]['end_seconds'], 5.59)
        self.assertEqual(cues[1]['id'], '2')

    def test_bad_srt_rejected(self):
        for text in ['', '1\n00:00:01,000 --> 00:00:00,000\nhello', '1\n00:99:00,000 --> 00:00:01,000\nhello',
                     '1\n00:00:00,000 --> 00:00:02,000\na\n\n2\n00:00:01,000 --> 00:00:03,000\nb']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                module.parse_srt(text)

    def test_media_link_and_copy_preserve_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source.mp4'
            source.write_bytes(b'example-video-bytes')
            url, size = module.stage_media(source, 'original/1.mp4', root / 'media', 'link')
            target = root / 'media/original/1.mp4'
            self.assertTrue(target.is_symlink())
            self.assertEqual(size, source.stat().st_size)
            self.assertEqual(url, module.MEDIA_PREFIX + 'original/1.mp4')
            module.stage_media(source, 'original/1.mp4', root / 'media', 'copy')
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_candidate_order_deterministic(self):
        self.assertEqual(module.candidate_order('430711'), module.candidate_order('430711'))
        self.assertEqual(set(module.candidate_order('430711')), set(module.MODELS))


if __name__ == '__main__':
    unittest.main()
