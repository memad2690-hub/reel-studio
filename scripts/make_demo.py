#!/usr/bin/env python3
"""Create synthetic demo projects (_demo-a cut-out, _demo-b split-screen) and use them as a smoke test.

No ElevenLabs credits or real footage needed: words get synthetic timings, audio is a quiet tone,
and Mode B 'footage' is an FFmpeg test pattern.
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCRIPT_A = ('إعلانك جاب ROAS خمسة… بس انت خسران فلوس. ليه؟ عشان الـROAS مش هو الربح. '
            'لو بعت بمية ألف، اطرح تكلفة المنتج والشحن والمرتجعات. '
            'الـBreak-even ROAS عندك ممكن يكون أربعة أصلا. يعني خمسة دي بالكاد فوق الصفر. '
            'عشان كدة احسب الـContribution Margin الأول. اكتب AUDIT في الكومنتات وأنا أبعتلك الشيت.')

SCENES_A = {
    'mode': 'A', 'words': 'words.json', 'audio': 'audio/vo.mp3', 'captions': True,
    'scenes': [
        {'id': 'hook', 'title': 'Hook', 'elements': [
            {'type': 'torn', 'text': 'ROAS 5', 'x': 360, 'y': 300, 'w': 420, 'h': 150, 'size': 80, 'in': 'ROAS', 'anim': 'stamp'},
            {'type': 'person', 'x': 360, 'y': 640, 'color': 'navy', 'in': {'rel': 0.1}},
            {'type': 'money', 'x': 360, 'y': 790, 'stacks': 3, 'in': 'خسران', 'anim': 'shake'},
            {'type': 'xmark', 'x': 360, 'y': 720, 'size': 70, 'in': 'فلوس', 'anim': 'stamp'}]},
        {'id': 'context', 'title': 'Context', 'start': 'ليه', 'elements': [
            {'type': 'label', 'text': 'ROAS ≠ ربح', 'x': 360, 'y': 260, 'size': 54, 'in': 'الربح'},
            {'type': 'number', 'text': '100,000', 'count_to': 100000, 'suffix': ' ج', 'x': 360, 'y': 470, 'size': 96, 'color': 'navy', 'in': 'بمية'},
            {'type': 'steps', 'x': 360, 'y': 620, 'gap': 90, 'size': 38, 'items': [
                {'text': 'تكلفة المنتج', 'in': 'تكلفة', 'color': 'cream'},
                {'text': 'الشحن', 'in': 'والشحن', 'color': 'cream'},
                {'text': 'المرتجعات', 'in': 'والمرتجعات', 'color': 'cream'}]}]},
        {'id': 'tension', 'title': 'Tension', 'start': 'Break', 'elements': [
            {'type': 'card', 'title': 'Break-even', 'lines': ['ROAS 4'], 'x': 200, 'y': 360, 'w': 260, 'h': 170, 'accent': 'red', 'in': 'Break'},
            {'type': 'card', 'title': 'إعلانك', 'lines': ['ROAS 5'], 'x': 520, 'y': 360, 'w': 260, 'h': 170, 'accent': 'teal', 'in': 'خمسة', 'anim': 'pop'},
            {'type': 'seats', 'n': 20, 'cols': 10, 'filled': 16, 'x': 360, 'y': 640, 'color': 'mustard', 'in': 'يعني', 'fill_end': 'الصفر'},
            {'type': 'text', 'text': 'مثال', 'x': 360, 'y': 760, 'size': 30, 'color': 'red', 'in': 'يعني'}]},
        {'id': 'cta', 'title': 'CTA', 'start': 'عشان كدة', 'elements': [
            {'type': 'calendar', 'top': 'الأول', 'text': 'CM', 'x': 360, 'y': 330, 'in': 'Contribution', 'anim': 'pop'},
            {'type': 'stamp', 'text': 'اكتب AUDIT', 'x': 360, 'y': 620, 'size': 64, 'in': 'AUDIT', 'anim': 'stamp'},
            {'type': 'check', 'x': 360, 'y': 780, 'size': 60, 'in': 'الشيت'}]},
    ]}

SCRIPT_B = ('الإعلان بيقولك إنك كسبت. بس السؤال الحقيقي، فاضلك كام في جيبك؟ '
            'لو المبيعات مية ألف، شيل الإعلانات والشحن والمرتجعات. '
            'فاضلك خمستاشر ألف بس. ولو المرتجعات زادت، تبقى خسارة. اكتب AUDIT في الكومنتات.')

SCENES_B = {
    'mode': 'B', 'words': 'words.json', 'audio': 'build/cut_audio.m4a', 'captions': True,
    'scenes': [
        {'id': 'hook', 'card': 'top', 'elements': [
            {'type': 'headline', 'pre': 'الإعلان', 'hl': 'كسبان', 'post': '؟', 'x': 540, 'y': 160, 'size': 100, 'in': 'كسبت'},
            {'type': 'icon', 'name': 'megaphone', 'x': 300, 'y': 470, 'in': 'الإعلان'},
            {'type': 'icon', 'name': 'money', 'x': 780, 'y': 470, 'in': 'جيبك', 'anim': 'shake'},
            {'type': 'arrow', 'x': 400, 'y': 470, 'dx': 270, 'dy': 0, 'in': 'السؤال'}]},
        {'id': 'math', 'start': 'لو المبيعات', 'elements': [
            {'type': 'number', 'text': '100,000', 'count_to': 100000, 'x': 540, 'y': 130, 'size': 110, 'in': 'مية'},
            {'type': 'steps', 'x': 540, 'y': 300, 'gap': 120, 'size': 46, 'items': [
                {'type': 'pill', 'text': 'إعلانات 40,000', 'in': 'الإعلانات'},
                {'type': 'pill', 'text': 'شحن 25,000', 'in': 'والشحن'},
                {'type': 'pill', 'text': 'مرتجعات 20,000', 'in': 'والمرتجعات'}]}]},
        {'id': 'payoff', 'start': 'فاضلك', 'elements': [
            {'type': 'headline', 'pre': 'فاضلك', 'hl': '15,000', 'post': 'بس', 'x': 540, 'y': 180, 'size': 104},
            {'type': 'wcard', 'lines': ['خسارة 5,000 ج'], 'x': 540, 'y': 420, 'size': 60, 'text_color': 'red', 'in': 'خسارة', 'anim': 'stamp'},
            {'type': 'pill', 'text': 'مثال', 'color': 'blue', 'x': 540, 'y': 600, 'size': 36, 'in': 'خسارة'}]},
        {'id': 'cta', 'start': 'اكتب', 'elements': [
            {'type': 'cta', 'keyword': 'AUDIT', 'magnet': 'شيت حساب الربح', 'x': 540, 'y': 200, 'in': 'اكتب'}]},
    ]}


def synth_words(script, start=0.4, per=0.36):
    words, t = [], start
    for w in script.split():
        dur = per + 0.02 * max(0, len(w) - 4)
        words.append({'text': w, 'start': round(t, 3), 'end': round(t + dur, 3)})
        t += dur + (0.45 if w.endswith(('.', '؟', '…', '،')) else 0.06)
    return words


def run(cmd):
    print('+', ' '.join(cmd)); subprocess.run(cmd, check=True, cwd=ROOT)


def make(slug, mode, script, scenes):
    d = os.path.join(ROOT, 'projects', slug)
    shutil.rmtree(d, ignore_errors=True)
    run([sys.executable, 'reel.py', 'new', slug, '--mode', mode, '--title', f'Demo {mode}', '--cta', 'AUDIT'])
    words = synth_words(script)
    dur = words[-1]['end'] + 1.0
    with open(os.path.join(d, 'scenes.json'), 'w', encoding='utf-8') as f:
        json.dump(scenes, f, ensure_ascii=False, indent=1)
    with open(os.path.join(d, 'script.md'), 'w', encoding='utf-8') as f:
        f.write('# Script (synthetic demo)\n\n' + script + '\n')
    tone = f'sine=frequency=220:duration={dur:.2f},volume=0.05'
    if mode == 'A':
        with open(os.path.join(d, 'words.json'), 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', tone, '-c:a', 'libmp3lame', '-b:a', '128k',
                        os.path.join(d, 'audio', 'vo.mp3')], check=True)
    else:
        raw = os.path.join(d, 'raw', 'raw.mp4')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'testsrc2=size=1080x1920:rate=30:duration={dur:.2f}',
                        '-f', 'lavfi', '-i', tone, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', raw], check=True)
        with open(os.path.join(d, 'words_raw.json'), 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False)
    return d


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'both'
    if which in ('a', 'both'):
        make('_demo-a', 'A', SCRIPT_A, SCENES_A)
        run([sys.executable, 'reel.py', 'storyboard', '_demo-a'])
    if which in ('b', 'both'):
        make('_demo-b', 'B', SCRIPT_B, SCENES_B)
        run([sys.executable, 'reel.py', 'roughcut', '_demo-b'])
        run([sys.executable, 'reel.py', 'finalize-cut', '_demo-b', '--crop', '1080:994:0:500'])
        run([sys.executable, 'reel.py', 'storyboard', '_demo-b'])
    print('\nDemo projects ready. Full renders: python3 reel.py render _demo-a  /  python3 reel.py render _demo-b')
