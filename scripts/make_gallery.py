"""Data-storytelling gallery (Style 04): one scene per chart, synthetic words + test-pattern footage.

    python3 scripts/make_gallery.py            # builds projects/_demo-data and its storyboard
    python3 reel.py render _demo-data --draft  # optional full render

Every number here is an illustrative example (each scene carries a مثال pill); the builder checks the arithmetic.
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from make_demo import synth_words  # noqa: E402

SLUG = '_demo-data'
SCRIPT = ('الأرباح بتتوزع كده المبيعات مية ألف والبضاعة خمسين ألف والإعلانات خمسة وعشرين ألف والشحن عشرة آلاف يبقى الربح خمستاشر ألف. '
          'شوف الـ ROAS في تلات حملات الأولى اتنين والتانية أربعة والتالتة ستة والـ break-even خمسة. '
          'الميزانية رايحة فين ستين في المية prospecting وتلاتين retargeting وعشرة testing. '
          'المبيعات في ست شهور يناير فبراير مارس أبريل مايو يونيو. '
          'الـ funnel عشرة آلاف زيارة ألفين add to cart خمسمية checkout ميتين شراء. '
          'لو الهامش عشرين في المية يبقى الـ break-even خمسة والـ ROAS بتاعك أربعة.')

EX = {'type': 'pill', 'text': 'مثال', 'color': 'blue', 'size': 34, 'anim': 'fade', 'in': {'rel': 0.05}}


def ex(x, y):
    e = dict(EX); e.update(x=x, y=y); return e


SCENES = {
    'mode': 'B', 'brand': 'media-buying', 'words': 'words.json', 'audio': 'build/cut_audio.m4a', 'captions': True,
    'caption_style': 'highlight', 'caption_keywords': ['ROAS', 'break-even', 'funnel', 'الربح'],
    'scenes': [
        {'id': 'waterfall', 'title': 'Profit waterfall', 'layout': 'pip-right', 'elements': [
            {'type': 'headline', 'pre': '', 'hl': 'الربح فين؟', 'post': '', 'x': 290, 'y': -330, 'size': 74, 'anim': 'wipe', 'in': {'rel': 0.02}},
            ex(540, 60),
            {'type': 'waterfall', 'x': 540, 'y': 420, 'w': 940, 'h': 560, 'unit': 'ج', 'rows': [
                {'label': 'المبيعات', 'value': 100000, 'in': 'المبيعات'},
                {'label': 'البضاعة', 'value': 50000, 'op': '-', 'in': 'والبضاعة'},
                {'label': 'الإعلانات', 'value': 25000, 'op': '-', 'in': 'والإعلانات'},
                {'label': 'الشحن', 'value': 10000, 'op': '-', 'in': 'والشحن'}],
             'result': {'label': 'الربح', 'label_negative': 'خسارة', 'value': 15000, 'in': 'الربح'}}]},
        {'id': 'bars', 'title': 'ROAS vs break-even', 'start': 'شوف', 'layout': 'top', 'elements': [
            ex(900, 40),
            {'type': 'bars', 'x': 540, 'y': 400, 'w': 860, 'h': 470, 'unit': '', 'items': [
                {'label': 'حملة 1', 'value': 2, 'tone': 'negative', 'in': 'الأولى'},
                {'label': 'حملة 2', 'value': 4, 'tone': 'negative', 'in': 'والتانية'},
                {'label': 'حملة 3', 'value': 6, 'tone': 'positive', 'in': 'والتالتة'}],
             'ref': {'value': 5, 'label': 'Break-even', 'tone': 'red', 'in': 'break'}}]},
        {'id': 'donut', 'title': 'Budget split', 'start': 'الميزانية', 'layout': 'bottom', 'elements': [
            {'type': 'headline', 'pre': 'الميزانية', 'hl': 'رايحة فين؟', 'post': '', 'x': 540, 'y': 80, 'size': 70, 'anim': 'wipe', 'in': {'rel': 0.02}},
            {'type': 'donut', 'x': 540, 'y': 470, 'total': 100, 'center': '100%', 'segments': [
                {'label': 'Prospecting', 'value': 60, 'tone': 'blue', 'in': 'ستين'},
                {'label': 'Retargeting', 'value': 30, 'tone': 'green', 'in': 'وتلاتين'},
                {'label': 'Testing', 'value': 10, 'tone': 'yellow', 'in': 'وعشرة'}]},
            ex(540, 760)]},
        {'id': 'line', 'title': 'Sales trend', 'start': 'المبيعات في', 'layout': 'pip-left', 'elements': [
            ex(800, 0),
            {'type': 'line', 'x': 540, 'y': 470, 'w': 880, 'h': 440, 'unit': 'ج', 'tone': 'green', 'points': [
                {'label': 'يناير', 'value': 40000, 'in': 'يناير'}, {'label': 'فبراير', 'value': 55000, 'in': 'فبراير'},
                {'label': 'مارس', 'value': 48000, 'in': 'مارس'}, {'label': 'أبريل', 'value': 70000, 'in': 'أبريل'},
                {'label': 'مايو', 'value': 85000, 'in': 'مايو'}, {'label': 'يونيو', 'value': 120000, 'in': 'يونيو'}]}]},
        {'id': 'funnel', 'title': 'Ad funnel', 'start': 'الـ funnel', 'layout': 'top', 'elements': [
            ex(900, 30),
            {'type': 'funnel', 'x': 560, 'y': 400, 'w': 820, 'stages': [
                {'label': 'زيارات', 'value': 10000, 'in': 'زيارة'},
                {'label': 'Add to cart', 'value': 2000, 'in': 'add'},
                {'label': 'Checkout', 'value': 500, 'in': 'checkout'},
                {'label': 'شراء', 'value': 200, 'in': 'شراء'}]}]},
        {'id': 'breakeven', 'title': 'Break-even ROAS', 'start': 'لو الهامش', 'layout': 'pip-right', 'elements': [
            ex(290, -300),
            {'type': 'breakeven', 'x': 540, 'y': 380, 'margin_pct': 20, 'expect': 5, 'actual': 4, 'in': 'الهامش', 'in_be': 'break', 'in_actual': 'بتاعك'}]},
    ]}


def run(cmd):
    print('$', ' '.join(cmd)); subprocess.run(cmd, cwd=ROOT, check=True)


def main():
    d = os.path.join(ROOT, 'projects', SLUG)
    shutil.rmtree(d, ignore_errors=True)
    run([sys.executable, 'reel.py', 'new', SLUG, '--mode', 'B', '--title', 'Data storytelling gallery'])
    words = synth_words(SCRIPT)
    dur = words[-1]['end'] + 1.0
    with open(os.path.join(d, 'words.json'), 'w', encoding='utf-8') as f:
        json.dump(words, f, ensure_ascii=False)
    os.makedirs(os.path.join(d, 'build'), exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'sine=frequency=220:duration={dur:.2f},volume=0.05',
                    '-c:a', 'aac', '-b:a', '128k', os.path.join(d, 'build', 'cut_audio.m4a')], check=True)
    sc = dict(SCENES); sc['duration'] = round(dur, 2)
    with open(os.path.join(d, 'scenes.json'), 'w', encoding='utf-8') as f:
        json.dump(sc, f, ensure_ascii=False, indent=1)
    run([sys.executable, 'reel.py', 'storyboard', SLUG])


if __name__ == '__main__':
    main()
