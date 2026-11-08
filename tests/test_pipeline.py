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


class CardSlideTests(Tmp):
    def test_graphics_wait_for_card_slide(self):
        import re
        self.write('project.json', {'mode': 'B'})
        self.write('words.json', W('واحد اتنين تلاتة اربعة خمسة ستة'))
        self.write('scenes.json', {'mode': 'B', 'duration': 4.0, 'scenes': [
            {'id': 'a', 'elements': [{'type': 'text', 'text': 'x', 'in': {'rel': 0.05}}]},
            {'id': 'b', 'start': 'اربعة', 'elements': [{'type': 'text', 'text': 'y', 'in': {'rel': 0.05}},
                                                       {'type': 'text', 'text': 'z', 'space': 'canvas', 'in': {'rel': 0.05}}]}]})
        builder.build(self.d)
        page = open(os.path.join(self.d, 'build', 'page.html'), encoding='utf-8').read()
        ins = [float(x) for x in re.findall(r'data-in="([\d.]+)"', page)]
        self.assertEqual(ins, [0.05, 1.5 + builder.CARD_SLIDE, 1.55])  # first scene and canvas elements unaffected


class EditorialV2Tests(Tmp):
    def scenes(self, scenes, **spec):
        self.write('project.json', {'mode': 'B'})
        self.write('words.json', W('المبيعات مية ألف والتكاليف تمانين والإعلانات خمسة وعشرين يبقى خسارة'))
        d = {'mode': 'B', 'duration': 6.0, 'scenes': scenes}; d.update(spec)
        self.write('scenes.json', d)
        return builder.build(self.d)

    EQ = {'type': 'equation', 'rows': [{'label': 'مبيعات', 'value': 100000}, {'label': 'تكاليف', 'value': 80000, 'op': '-'},
                                       {'label': 'إعلانات', 'value': 25000, 'op': '-'}],
          'result': {'label': 'ربح', 'label_negative': 'خسارة', 'value': -5000, 'tone': 'negative'}}

    def test_equation_arithmetic_ok(self):
        self.assertEqual(builder.equation_result(self.EQ), (-5000, []))
        self.assertEqual(self.scenes([{'id': 'a', 'elements': [self.EQ]}])['anchor_misses'], [])

    def test_equation_wrong_result_blocks(self):
        bad = json.loads(json.dumps(self.EQ)); bad['result']['value'] = -15000
        misses = self.scenes([{'id': 'a', 'elements': [bad]}])['anchor_misses']
        self.assertTrue(any('finance' in m['problem'] and 'add up' in m['problem'] for m in misses), misses)

    def test_equation_wrong_tone_blocks(self):
        bad = json.loads(json.dumps(self.EQ)); bad['result'] = {'tone': 'positive'}
        self.assertTrue(any('tone' in p for p in builder.equation_result(bad)[1]))

    def test_negative_result_shown_without_minus(self):
        self.scenes([{'id': 'a', 'elements': [self.EQ]}])
        page = open(os.path.join(self.d, 'build', 'page.html'), encoding='utf-8').read()
        self.assertIn('خسارة', page); self.assertIn('5,000 ج', page)
        self.assertNotIn('-5,000', page); self.assertNotIn('\u22125,000', page)

    def test_unknown_layout_flagged(self):
        misses = self.scenes([{'id': 'a', 'layout': 'sideways', 'elements': []}])['anchor_misses']
        self.assertTrue(any('unknown layout' in m['problem'] for m in misses))

    def test_layout_region_and_floor(self):
        import re
        self.scenes([{'id': 'a', 'layout': 'full', 'elements': []},
                     {'id': 'b', 'layout': 'pip-right', 'start': 'والإعلانات', 'elements': [{'type': 'text', 'text': 'x', 'y': 10}]}])
        page = open(os.path.join(self.d, 'build', 'page.html'), encoding='utf-8').read()
        self.assertIn(f'translate(0,{builder.LAYOUTS["pip-right"]["y0"]})', page)
        start = 5 * 0.5  # 'والإعلانات' is the 6th word, 0.5 s apart
        self.assertEqual(float(re.findall(r'data-in="([\d.]+)"', page)[0]), start + builder.CARD_SLIDE)

    def test_brand_preset_applies_and_resets(self):
        import kits
        self.scenes([{'id': 'a', 'elements': []}], brand='ceos')
        self.assertEqual(kits.B['yellow'], '#D1FE17')
        self.scenes([{'id': 'a', 'elements': []}])
        self.assertEqual(kits.B['yellow'], '#f2cf4a')

    def test_caption_keywords_marked(self):
        m = self.scenes([{'id': 'a', 'elements': []}], caption_keywords=['خسارة'])
        hl = [c for c in m['captions'] if c['hl']]
        self.assertTrue(hl and 'خسارة' in hl[0]['text'].split()[hl[0]['hl'][0]])

    def test_statcard_negative_absolute(self):
        import kits
        svg = kits.build({'type': 'statcard', 'label': 'Ads', 'value': -25000, 'tone': 'negative'}, 'B')
        self.assertIn('25,000 ج', svg); self.assertNotIn('-25,000', svg)


class ChartCheckTests(unittest.TestCase):
    def check(self, el):
        import charts
        return charts.check(el)

    def test_waterfall_total_and_wrong_result(self):
        wf = {'type': 'waterfall', 'rows': [{'value': 100000}, {'value': 50000, 'op': '-'}, {'value': 25000, 'op': '-'},
                                            {'value': 10000, 'op': '-'}], 'result': {'value': 15000}}
        self.assertEqual(self.check(wf), (15000, []))
        wf['result']['value'] = 25000
        self.assertIn('add up', self.check(wf)[1][0])

    def test_donut_total(self):
        self.assertEqual(self.check({'type': 'donut', 'total': 100, 'segments': [{'value': 60}, {'value': 30}, {'value': 10}]})[1], [])
        self.assertTrue(self.check({'type': 'donut', 'total': 100, 'segments': [{'value': 60}, {'value': 30}]})[1])

    def test_funnel_rates_and_order(self):
        rates, p = self.check({'type': 'funnel', 'stages': [{'value': 10000}, {'value': 2000, 'rate': 20}, {'value': 500}]})
        self.assertEqual((rates, p), ([20.0, 25.0], []))
        self.assertTrue(self.check({'type': 'funnel', 'stages': [{'value': 100}, {'value': 200}]})[1])
        self.assertTrue(self.check({'type': 'funnel', 'stages': [{'value': 100}, {'value': 50, 'rate': 40}]})[1])

    def test_breakeven(self):
        r, p = self.check({'type': 'breakeven', 'margin_pct': 20, 'expect': 5})
        self.assertEqual((round(r['be'], 6), p), (5.0, []))
        r, p = self.check({'type': 'breakeven', 'revenue': 100000, 'variable_costs': 80000})
        self.assertAlmostEqual(r['be'], 5.0)
        self.assertTrue(self.check({'type': 'breakeven', 'margin_pct': 20, 'expect': 4})[1])
        self.assertIn('no break-even', self.check({'type': 'breakeven', 'margin_pct': -5})[1][0])

    def test_percent_is_isolated(self):
        import charts
        self.assertEqual(charts.pct(20), '\u206620%\u2069')

    def test_wrong_chart_blocks_build(self):
        d = tempfile.mkdtemp()
        try:
            for f, v in (('project.json', {'mode': 'B'}), ('words.json', W('واحد اتنين تلاتة')),
                         ('scenes.json', {'mode': 'B', 'duration': 2, 'scenes': [{'id': 'a', 'elements': [
                             {'type': 'donut', 'total': 100, 'segments': [{'value': 50}]}]}]})):
                with open(os.path.join(d, f), 'w', encoding='utf-8') as fh:
                    json.dump(v, fh, ensure_ascii=False)
            misses = builder.build(d)['anchor_misses']
            self.assertTrue(any(m['problem'].startswith('finance:') for m in misses))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class FxCheckTests(unittest.TestCase):
    def test_scorecard_winner_computed(self):
        import fx
        sc = {'type': 'scorecard', 'rows': [{'a': 6, 'b': 9}, {'a': 7, 'b': 8}, {'a': 5, 'b': 9}]}
        self.assertEqual(fx.check(sc), ({'a': 18, 'b': 26, 'winner': 'b'}, []))
        sc['winner'] = 'a'
        self.assertIn('winner says', fx.check(sc)[1][0])
        sc.pop('winner'); sc['lower_is_better'] = True
        self.assertEqual(fx.check(sc)[0]['winner'], 'a')

    def test_beforeafter_change_and_direction(self):
        import fx
        ba = {'type': 'beforeafter', 'before': {'value': 150}, 'after': {'value': 90}, 'better': 'lower', 'change_pct': -40}
        r, p = fx.check(ba)
        self.assertEqual((round(r['change']), r['good'], p), (-40, True, []))
        ba['change_pct'] = -30
        self.assertTrue(fx.check(ba)[1])
        ba.pop('change_pct'); ba['better'] = 'higher'
        self.assertFalse(fx.check(ba)[0]['good'])

    def test_versus_winner_value(self):
        import fx
        self.assertTrue(fx.check({'type': 'versus', 'winner': 'left'})[1])

    def test_kinetic_uses_exact_spoken_words(self):
        import fx
        from timing import Anchors
        words = W('الإعلان الحلو مش دايمًا هو اللي بيبيع وبعدين')
        fx.WORDS = words
        a = Anchors(words)
        got = fx.kinetic_words({'type': 'kinetic', 'from': 'الحلو', 'to': 'بيبيع'}, a, 0.0)
        self.assertEqual(' '.join(w['text'] for w in got), 'الحلو مش دايمًا هو اللي بيبيع')
        self.assertEqual(len(fx.kinetic_words({'type': 'kinetic', 'from': 'الحلو', 'count': 2}, a, 0.0)), 2)

    def test_caption_word_times(self):
        from timing import chunk_captions
        caps = chunk_captions(W('واحد اتنين تلاتة اربعة خمسة'), 2, 3)
        self.assertTrue(all(len(c['wt']) == len(c['text'].split()) for c in caps))


class PlannerTests(unittest.TestCase):
    def nums(self, t):
        import planner
        return [(x['value'], x['kind']) for x in planner.numbers(W(t))]

    def test_egyptian_numbers(self):
        self.assertEqual(self.nums('صرفت خمسة وعشرين ألف جنيه'), [(25000, 'money')])
        self.assertEqual(self.nums('المبيعات بـ100 ألف'), [(100000, 'money')])
        self.assertEqual(self.nums('الهامش عشرين في المية'), [(20, 'percent')])
        self.assertEqual(self.nums('الـ CPA كان مية وخمسين جنيه وبقى تسعين'), [(150, 'money'), (90, 'money')])
        self.assertEqual(self.nums('عشرة آلاف زيارة ألفين add to cart'), [(10000, 'count'), (2000, 'count')])
        self.assertEqual(self.nums('على creative واحد من الميزانية'), [(1, 'count')])

    def test_cues_respect_word_boundaries(self):
        import planner
        self.assertEqual(planner.has('عاجبه أو لأنه ما عندوش', planner.CUES['process']), [])
        self.assertTrue(planner.has('أول حاجة الـ hook', planner.CUES['process']))

    def test_single_ordinal_is_not_a_list(self):
        import planner
        r = planner.classify({'text': 'أول حاجة لازم تعرفها', 'numbers': []}, 3, 10)
        self.assertNotEqual(r[0], 'process')

    def test_cta_and_min_scene(self):
        import planner
        words = W('مين في الإعلانات دول شكله أغلى؟ ومين بيبيع؟ ' + 'كلام عادي جدا ' * 12 +
                  'لو عايز الشيت اكتب PROFIT', step=0.5)
        pl = planner.plan(words, 'medium')
        self.assertEqual(pl['segments'][-1]['role'], 'cta')
        for s in pl['segments'][:-1]:
            self.assertGreaterEqual(s['end'] - s['start'], planner.INTENSITY['medium']['min_scene'] - 0.6)

    def test_draft_numbers_come_from_speech(self):
        import planner
        words = W('تخيل الـ brand عنده sales بـ100 ألف جنيه صرف 25 ألف على الـ ads. والمبيعات بتقول كده بقى.', step=0.5)
        pl = planner.plan(words, 'medium')
        heard = {x['value'] for s in pl['segments'] for x in s['numbers']}
        draft = planner.draft_scenes(pl, words)
        vals = [e['value'] for sc in draft['scenes'] for e in sc['elements'] if 'value' in e]
        self.assertTrue(vals and set(vals) <= heard, (vals, heard))


class PlanCommandTests(Tmp):
    def test_apply_backs_up_existing_scenes(self):
        import subprocess as sp
        slug = '_test-plan-backup'
        d = os.path.join(ROOT, 'projects', slug)
        shutil.rmtree(d, ignore_errors=True)
        try:
            sp.run([sys.executable, 'reel.py', 'new', slug, '--mode', 'B'], cwd=ROOT, check=True, capture_output=True)
            with open(os.path.join(d, 'words.json'), 'w', encoding='utf-8') as f:
                json.dump(W('بص لو عندك 50 ألف جنيه ميزانية ما تحرقهمش. اكتبلي BUDGET'), f, ensure_ascii=False)
            with open(os.path.join(d, 'scenes.json'), 'w', encoding='utf-8') as f:
                json.dump({'mode': 'B', 'scenes': [{'id': 'mine'}]}, f)
            out = json.loads(sp.run([sys.executable, 'reel.py', 'plan', slug, '--apply'], cwd=ROOT, check=True,
                                    capture_output=True, text=True).stdout.strip().splitlines()[-1])
            self.assertTrue(out['applied'])
            bak = json.load(open(os.path.join(d, out['backup'])))
            self.assertEqual(bak['scenes'][0]['id'], 'mine')
            self.assertTrue(os.path.exists(os.path.join(d, 'plan.md')))
        finally:
            shutil.rmtree(d, ignore_errors=True)


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
