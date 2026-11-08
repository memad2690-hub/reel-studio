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


class Style09Tests(Tmp):
    """Cinematic style, chapter titles, photos, sticker layout and behind-the-speaker fallback."""
    scenes = EditorialV2Tests.scenes

    def page(self):
        return open(os.path.join(self.d, 'build', 'page.html'), encoding='utf-8').read()

    def test_cinematic_defaults_grain(self):
        self.scenes([{'id': 'a', 'elements': []}], style='cinematic')
        self.assertIn('id="grt"', self.page())
        self.scenes([{'id': 'a', 'elements': []}])
        self.assertNotIn('id="grt"', self.page())

    def test_chapter_renders(self):
        self.scenes([{'id': 'a', 'elements': [{'type': 'chapter', 'number': '01', 'text': 'الحسبة', 'sub': 'مثال'}]}])
        page = self.page()
        for t in ('01', 'الحسبة', 'مثال'):
            self.assertIn(t, page)

    def test_photo_missing_asset_blocks(self):
        misses = self.scenes([{'id': 'a', 'elements': [{'type': 'photo', 'src': 'nope.jpg'}]}])['anchor_misses']
        self.assertTrue(any('missing asset' in m['problem'] for m in misses), misses)

    def test_behind_without_cutouts_drawn_in_front_with_note(self):
        m = self.scenes([{'id': 'a', 'layout': 'full', 'elements': [{'type': 'text', 'text': 'خسارة', 'behind': True}]}])
        self.assertTrue(any('behind' in n for n in m['notes']), m['notes'])
        self.assertNotIn('id="behind"', self.page())
        self.assertIn('خسارة', self.page())

    def test_behind_with_cutouts_goes_behind(self):
        from PIL import Image
        os.makedirs(os.path.join(self.d, 'build', 'cut'))
        Image.new('RGBA', (4, 4)).save(os.path.join(self.d, 'build', 'cut', '00001.png'))
        m = self.scenes([{'id': 'a', 'layout': 'full', 'elements': [{'type': 'text', 'text': 'خسارة', 'behind': True}]}])
        self.assertFalse(any('behind' in n for n in m['notes']))
        self.assertIn('id="behind"', self.page())

    def test_sticker_layout_known(self):
        self.assertTrue(builder.LAYOUTS['sticker'].get('sticker'))
        misses = self.scenes([{'id': 'a', 'layout': 'sticker', 'elements': []}])['anchor_misses']
        self.assertFalse(any('layout' in m['problem'] for m in misses))


class SegmentTests(unittest.TestCase):
    """Mask cleanup and the quality score that decides the fallback (no model needed)."""

    def body(self):
        import numpy as np
        m = np.zeros((200, 120), np.float32)
        m[60:, 30:90] = 0.95          # torso touching the bottom edge
        m[20:60, 45:75] = 0.95        # head
        return m

    def test_refine_drops_blob_and_fills_holes(self):
        import numpy as np
        import segment
        m = self.body()
        m[5:25, 0:15] = 0.9           # seat blob, not touching the bottom
        m[120:135, 50:70] = 0.1       # shirt stripe read as background
        r = segment.refine(m)
        self.assertLess(r[10, 5], 0.1)
        self.assertGreater(r[128, 60], 0.9)

    def test_exclude_zone(self):
        import segment
        m = self.body()
        r = segment.refine(m, exclude=[(0, 0.8, 1, 1)])
        self.assertLess(r[190, 60], 0.05)

    def test_quality_clean_vs_noisy(self):
        import numpy as np
        import segment
        good, _ = segment.quality(self.body())
        noisy = self.body() * 0.6 + np.random.default_rng(1).random((200, 120)).astype(np.float32) * 0.35
        bad, _ = segment.quality(noisy)
        empty, _ = segment.quality(np.zeros((200, 120), np.float32))
        self.assertGreater(good, 0.62)
        self.assertLess(bad, 0.62)
        self.assertEqual(empty, 0.0)

    def test_mask_min_passed_to_page(self):
        with tempfile.TemporaryDirectory() as d:
            t = Style09Tests('test_sticker_layout_known'); t.d = d
            t.scenes([{'id': 'a', 'elements': []}], mask_min_quality=0.7)
            self.assertIn('"maskMin": 0.7', open(os.path.join(d, 'build', 'page.html'), encoding='utf-8').read())


class MixTests(Tmp):
    """Milestone 7: style mixing, scene transitions, per-scene captions, brand presets."""
    scenes = EditorialV2Tests.scenes

    def page(self):
        return open(os.path.join(self.d, 'build', 'page.html'), encoding='utf-8').read()

    def two(self, a=None, b=None, **spec):
        return self.scenes([dict({'id': 'a', 'elements': []}, **(a or {})),
                            dict({'id': 'b', 'start': 'والإعلانات', 'elements': []}, **(b or {}))], **spec)

    def test_style_defaults_and_scene_keys_win(self):
        m = self.two({'style': 'cinematic'}, {'style': '07', 'layout': 'bottom'})
        a, b = m['scenes']
        self.assertEqual((a['card'], a['zoom'], a['style'], a.get('cap')), ('full', [1.0, 1.06], 'cinematic', 'minimal'))
        self.assertEqual((b['card'], b['tr'][0], b['style']), ('bottom', 'whip', 'battle'))
        self.assertNotIn('tr', a)                       # no transition into the first scene

    def test_unknown_style_and_floating_ui_block(self):
        misses = self.two({'style': 'vaporwave'}, {'style': '05'})['anchor_misses']
        self.assertTrue(any('unknown style' in x['problem'] for x in misses))
        self.assertTrue(any('CEOS' in x['problem'] for x in misses))

    def test_transition_layer_only_when_used(self):
        self.two()
        self.assertNotIn('id="main"', self.page())
        self.two(b={'transition': 'flash'})
        self.assertIn('id="main"', self.page()); self.assertIn('id="flash"', self.page())

    def test_unknown_transition_and_caption_style_block(self):
        misses = self.two(b={'transition': 'spin', 'caption_style': 'comic'})['anchor_misses']
        self.assertTrue(any('unknown transition' in x['problem'] for x in misses))
        self.assertTrue(any('caption_style' in x['problem'] for x in misses))

    def test_brand_defaults_overrides_and_preset_untouched(self):
        import kits
        cfg_before = open(os.path.join(ROOT, 'studio.config.json'), encoding='utf-8').read()
        m = self.two(brand='ceos', brand_overrides={'palette': {'red': '#ff0000'}})
        self.assertEqual((m['capStyle'], m['scenes'][1]['tr'][0]), ('energy', 'blur'))
        self.assertEqual((kits.B['red'], kits.B['yellow']), ('#ff0000', '#D1FE17'))
        self.assertEqual(open(os.path.join(ROOT, 'studio.config.json'), encoding='utf-8').read(), cfg_before)
        self.assertTrue(any('unknown brand' in x['problem'] for x in self.two(brand='acme')['anchor_misses']))

    def test_mix_notes(self):
        sc = [{'id': f's{i}', 'style': st, 'elements': []} for i, st in enumerate(['01', '02', '04', '09'])]
        for s_, w in zip(sc[1:], ['ألف', 'والإعلانات', 'خسارة']):
            s_['start'] = w
        m = self.scenes(sc)
        self.assertTrue(any('4 styles' in n for n in m['notes']), m['notes'])
        self.assertTrue(any('s1: style changes' in n for n in m['notes']), m['notes'])


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


class GradeTests(unittest.TestCase):
    ORIGINAL = {'exposure': -12, 'contrast': 8, 'highlights': -45, 'shadows': 8, 'saturation': -14, 'temperature': 3,
                'tint': -3, 'sharpen': 5, 'fade': 5, 'vignette': 12}
    HSL = {'red': (0, -10, 0), 'orange': (-3, -12, 4), 'yellow': (-15, -30, -8), 'green': (-15, -35, -5),
           'cyan': (0, -20, -5), 'blue': (-8, -25, -10)}

    def test_preset_keeps_original_capcut_values(self):
        import grade
        pre = grade.load_preset('RC_Warm_Cinematic_v1')
        self.assertTrue(pre['locked'])
        self.assertEqual(pre['source']['basic'], self.ORIGINAL)
        self.assertEqual({k: (v['hue'], v['saturation'], v['lightness']) for k, v in pre['source']['hsl'].items()}, self.HSL)

    def test_code_never_writes_presets(self):
        for f in ('engine/grade.py', 'reel.py'):
            src = open(os.path.join(ROOT, f), encoding='utf-8').read()
            self.assertNotRegex(src, r"open\([^)]*grades[^)]*['\"]w['\"]")

    def test_intensity_zero_is_identity_and_skin_is_protected(self):
        import numpy as np
        import grade
        pre = grade.load_preset('RC_Warm_Cinematic_v1')
        x = np.array([[0.82, 0.6, 0.48], [0.3, 0.6, 0.25], [0.5, 0.5, 0.5]])
        self.assertTrue(np.allclose(grade.apply(x, pre, 0.0), x))
        y = grade.apply(x, pre, 1.0)
        hb, sb, _ = grade._hsv(x); ha, sa, _ = grade._hsv(y)
        self.assertLess(abs(ha[0] - hb[0]), 2.0)            # skin hue stays
        self.assertGreater(sa[0] / sb[0], 0.9)              # skin keeps >90% saturation
        self.assertLess(sa[1] / sb[1], 0.8)                 # greens are muted
        self.assertGreater(y[2].max() - y[2].min(), -1)     # grey stays near-neutral
        self.assertLess(y[2].max() - y[2].min(), 0.02)

    def test_half_intensity_is_between(self):
        import numpy as np
        import grade
        pre = grade.load_preset('RC_Warm_Cinematic_v1')
        x = np.array([[0.3, 0.6, 0.25]])
        a, b, c = grade.apply(x, pre, 0), grade.apply(x, pre, 0.5), grade.apply(x, pre, 1)
        self.assertTrue(np.allclose(b, (a + c) / 2, atol=1e-6))

    def test_metrics_flag_problems(self):
        import numpy as np
        import grade
        before = np.full((40, 40, 3), 0.5)
        after = before.copy(); after[:10] = 1.0; after[10:20] = 0.0
        p = grade.problems(grade.metrics(before, after))
        self.assertTrue(any('clipping' in x for x in p) and any('crushed' in x for x in p))

    def test_style09_default(self):
        import grade
        d = tempfile.mkdtemp()
        try:
            with open(os.path.join(d, 'scenes.json'), 'w') as f:
                json.dump({'style': 'cinematic', 'scenes': []}, f)
            self.assertEqual(grade.project_grade(d)['preset'], 'RC_Warm_Cinematic_v1')
            with open(os.path.join(d, 'grade.json'), 'w') as f:
                json.dump({'preset': None, 'intensity': 0}, f)
            self.assertIsNone(grade.project_grade(d))       # explicitly off wins
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
