"""Pipeline guards: slugs, version numbering/overwrite protection, timing problems, QA."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import reel  # noqa: E402
import build as builder  # noqa: E402  (reel puts engine/ on sys.path)


def W(text, t0=0.0, step=0.5):
    out, t = [], t0
    for w in text.split():
        out.append({'text': w, 'start': round(t, 2), 'end': round(t + 0.4, 2)}); t += step
    return out


class Tmp(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def write(self, rel, data):
        p = os.path.join(self.d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            if isinstance(data, str):
                f.write(data)
            else:
                json.dump(data, f, ensure_ascii=False)


class SlugTests(unittest.TestCase):
    def test_valid(self):
        for s in ('mb-007', 'ceos_012', '_demo-a', 'x1'):
            self.assertTrue(reel.valid_slug(s), s)

    def test_invalid(self):
        for s in ('MB-007', 'my reel', '../x', '', '-x', 'a/b'):
            self.assertFalse(reel.valid_slug(s), s)


class VersionTests(Tmp):
    def test_next_version_skips_unjoined_parts(self):
        self.write('versions.json', [{'id': 'v001'}, {'id': 'sb001'}])
        self.write('exports/v002_part_0000.00.mp4', '')
        self.assertEqual(reel.next_version(self.d, 'v'), 'v003')
        self.assertEqual(reel.next_version(self.d, 'sb'), 'sb002')

    def test_version_taken(self):
        self.write('versions.json', [{'id': 'v001'}])
        self.write('exports/v002.mp4', '')
        self.assertTrue(reel.version_taken(self.d, 'v001'))
        self.assertTrue(reel.version_taken(self.d, 'v002'))
        self.assertFalse(reel.version_taken(self.d, 'v003'))


class TimingProblemTests(Tmp):
    def build(self, elements):
        self.write('project.json', {'mode': 'A'})
        self.write('words.json', W('النهارده هنتكلم عن الربح وبعدين اكتب AUDIT'))
        self.write('scenes.json', {'mode': 'A', 'duration': 5.0, 'scenes': [
            {'id': 'hook', 'elements': elements},
            {'id': 'cta', 'start': 'اكتب', 'elements': [{'type': 'text', 'text': 'AUDIT', 'in': 'AUDIT'}]}]})
        return builder.build(self.d)

    def test_ok_element_has_no_problem(self):
        self.assertEqual(self.build([{'type': 'text', 'text': 'ربح', 'in': 'الربح'}])['anchor_misses'], [])

    def test_element_anchored_in_a_later_scene_is_flagged(self):
        misses = self.build([{'type': 'text', 'text': 'TEST', 'in': 'AUDIT'}])['anchor_misses']
        self.assertEqual(len(misses), 1)
        self.assertIn('never appears', misses[0]['problem'])

    def test_late_steps_item_is_flagged(self):
        misses = self.build([{'type': 'steps', 'items': [{'text': 'a', 'in': 'الربح'}, {'text': 'b', 'in': 'AUDIT'}]}])['anchor_misses']
        self.assertEqual([m['element'] for m in misses], ['b'])

    def test_missing_anchor_still_reported(self):
        misses = self.build([{'type': 'text', 'text': 'x', 'in': 'مش موجودة'}])['anchor_misses']
        self.assertEqual(misses[0]['anchor'], 'مش موجودة')


class SnapTests(unittest.TestCase):
    def test_snap_to_frames(self):
        import footage
        self.assertEqual(footage.snap([[1.14, 4.64], [5.1, 5.11]]), [[1.1333, 4.6333]])  # zero-length dropped

    def test_lone_punctuation_glued(self):
        from timing import load_words
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump({'words': [{'text': 'بتاعك', 'start': 0, 'end': 0.5, 'type': 'word'},
                                 {'text': '.', 'start': 0.5, 'end': 0.5, 'type': 'word'},
                                 {'text': '[صوت]', 'start': 0.6, 'end': 1, 'type': 'audio_event'}]}, f)
        try:
            self.assertEqual([w['text'] for w in load_words(f.name)], ['بتاعك.'])
        finally:
            os.remove(f.name)


@unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg not installed')
class QATests(Tmp):
    def make(self, fps, adur):
        out = os.path.join(self.d, 'x.mp4')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'color=s=1080x1920:r={fps}:d=1',
                        '-f', 'lavfi', '-i', f'sine=d={adur}', '-c:v', 'libx264', '-c:a', 'aac', out], check=True)
        return out

    def test_good_file(self):
        self.assertEqual(reel.qa(self.make(24, 1), 'A')['problems'], [])

    def test_wrong_fps_and_length(self):
        probs = reel.qa(self.make(25, 2), 'A')['problems']
        self.assertTrue(any(p.startswith('fps 25') for p in probs), probs)
        self.assertTrue(any('lengths differ' in p for p in probs), probs)


if __name__ == '__main__':
    unittest.main()
