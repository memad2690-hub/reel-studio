import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine'))
from timing import Anchors, align_script, chunk_captions, map_through_cuts, norm  # noqa: E402
from footage import propose_cuts  # noqa: E402


def W(text, t0=0.0, step=0.4):
    out, t = [], t0
    for w in text.split():
        out.append({'text': w, 'start': round(t, 2), 'end': round(t + 0.3, 2)}); t += step
    return out


class TimingTests(unittest.TestCase):
    def test_norm_unifies_alef_and_strips_punct(self):
        self.assertEqual(norm('بـ"أحمد،'), norm('باحمد'))

    def test_anchor_substring_and_tiny_words(self):
        a = Anchors(W('إعلانك جاب ROAS خمسة ما فيش ربح'))
        self.assertEqual(a.at('ROAS'), 0.8)
        self.assertEqual(a.at('ما'), 1.6)          # exact token, not inside other words
        self.assertIsNone(a.at('مش'))

    def test_anchor_phrase_and_after(self):
        a = Anchors(W('عشان الروس عشان كدة احسب'))
        self.assertEqual(a.at('عشان كدة'), 0.8)
        self.assertEqual(a.at('عشان', after=0.5), 0.8)
        self.assertEqual(a.resolve({'rel': 0.3}, scene_start=2.0), 2.3)
        self.assertEqual(a.resolve({'at': 'احسب', 'offset': -0.1}), 1.5)

    def test_align_script_interpolates(self):
        stt = W('الإعلان بيقولك انك كسبت')
        out = align_script('الإعلان بيقولك إنك فعلا كسبت', stt)
        self.assertEqual(len(out), 5)
        self.assertEqual(out[0]['start'], 0.0)
        self.assertTrue(out[2]['start'] < out[3]['start'] < out[4]['start'])

    def test_map_through_cuts(self):
        words = W('a b c d e f')  # starts 0,.4,.8,1.2,1.6,2.0
        out = map_through_cuts(words, [[0.0, 0.7], [1.5, 2.4]])
        self.assertEqual([w['text'] for w in out], ['a', 'b', 'e', 'f'])
        self.assertAlmostEqual(out[2]['start'], 0.7 + 0.1, places=2)

    def test_captions_balanced_and_bounded(self):
        caps = chunk_captions(W('واحد اتنين تلاتة اربعة خمسة'), 1, 3, orphan_slack=0)
        self.assertTrue(all(len(c['text'].split()) <= 3 for c in caps))
        self.assertNotIn(1, [len(c['text'].split()) for c in caps])
        caps = chunk_captions(W('ليه؟ عشان كدة'), 2, 4)
        self.assertEqual(caps[0]['text'], 'ليه؟')


class CutTests(unittest.TestCase):
    def test_keeps_last_take(self):
        words = W('النهارده هنتكلم عن', 0.0) + W('النهارده هنتكلم عن الربح.', 3.0) + W('يلا نبدأ', 6.0)
        segs, report = propose_cuts(words, 8.0)
        self.assertFalse(report[0]['kept'])
        self.assertTrue(report[1]['kept'])
        self.assertGreaterEqual(segs[0][0], 2.8)


if __name__ == '__main__':
    unittest.main()
