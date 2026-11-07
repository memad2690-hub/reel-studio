"""Build a deterministic HTML page (window.setTime(t)) from a project's scenes.json."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from timing import Anchors, chunk_captions, load_words  # noqa: E402
import kits  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODES = {
    'A': {'W': 720, 'H': 1280, 'scale': 1.5, 'fps': 24, 'bg': '#e8e4da', 'grid': 40, 'grid_color': '#cfc9bb'},
    'B': {'W': 1080, 'H': 1920, 'scale': 1.0, 'fps': 30, 'bg': '#f4eddd', 'grid': 54, 'grid_color': '#e2d9c4'},
}
CARD = {'x': 40, 'top': 130, 'bottom': 900, 'w': 1000, 'h': 920}
REGION = {'top': 1080, 'bottom': 60}   # graphics-half origin when the card is at top / bottom


def load_config():
    with open(os.path.join(ROOT, 'studio.config.json'), encoding='utf-8') as f:
        return json.load(f)


def media_duration(path):
    try:
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                             capture_output=True, text=True, check=True).stdout.strip()
        return float(out)
    except Exception:
        return None


def esc(s):
    return kits.esc(s)


def anim_group(inner, t_in, t_out, kind, x=0, y=0, rot=0, scale=1, extra=''):
    return (f'<g class="a" data-in="{t_in:.3f}" data-out="{t_out:.3f}" data-k="{kind}" {extra}>'
            f'<g transform="translate({x},{y}) rotate({rot}) scale({scale})">{inner}</g></g>')


def flag_late(anchors, spec, t, t_out, s_start, what):
    """An element that comes in at/after the moment it leaves would never be seen: report it."""
    if t >= t_out - 1e-6:
        anchors.misses.append({'anchor': spec, 'after': round(s_start, 2), 'element': what,
                               'problem': f'comes in at {t:.2f}s, after it leaves ({t_out:.2f}s), so it never appears'})


def expand(el, mode, anchors, s_start, s_end, idx, ins=None):
    """Return SVG for one element (seats and steps expand to several animated groups)."""
    ins = ins if ins is not None else []
    t_in = anchors.resolve(el.get('in'), s_start, default=s_start + 0.2 + 0.12 * idx)
    t_out = anchors.resolve(el.get('out'), s_start, default=s_end)
    t_out = min(t_out, s_end)
    what = el.get('text') or el.get('hl') or el.get('title') or el.get('name') or el['type']
    flag_late(anchors, el.get('in'), t_in, t_out, s_start, what)
    ins.append(t_in)
    kind = el.get('anim', 'pop')
    x, y, rot, sc = el.get('x', 0), el.get('y', 0), el.get('rot', 0), el.get('scale', 1)
    t = el['type']
    if t == 'seats':
        n, cols = el.get('n', 20), el.get('cols', 10)
        size, gap = el.get('size', 36), el.get('gap', 10)
        filled = el.get('filled', n)
        pal = kits.A if mode == 'A' else kits.B
        c = kits.col(el.get('color', 'red'), pal)
        fill_end = anchors.resolve(el.get('fill_end'), s_start, default=t_in + 0.12 * filled)
        if filled and fill_end > t_in:
            flag_late(anchors, el.get('fill_end'), fill_end, t_out, s_start, 'seats fill_end')
        rows = (n + cols - 1) // cols
        ox, oy = -(cols * (size + gap) - gap) / 2, -(rows * (size + gap) - gap) / 2
        pos = [(ox + (i % cols) * (size + gap), oy + (i // cols) * (size + gap)) for i in range(n)]
        outline = ''.join(f'<rect x="{px}" y="{py}" width="{size}" height="{size}" rx="4" fill="none" '
                          f'stroke="{kits.col("ink", pal)}" stroke-width="3" opacity=".55"/>' for px, py in pos)
        out = anim_group(outline, t_in, t_out, 'fade', x, y, rot, sc)
        for i in range(filled):
            ti = t_in + (fill_end - t_in) * (i / max(1, filled - 1))
            ins.append(ti)
            px, py = pos[i]
            sq = f'<rect x="{px}" y="{py}" width="{size}" height="{size}" rx="4" fill="{c}"/>'
            out += anim_group(sq, ti, t_out, 'pop', x, y, rot, sc)
        return out
    if t == 'steps':
        out = ''
        gap = el.get('gap', 130)
        for i, item in enumerate(el.get('items', [])):
            ti = anchors.resolve(item.get('in'), s_start, default=t_in + 0.6 * i)
            flag_late(anchors, item.get('in'), ti, t_out, s_start, item.get('text') or f'steps item {i + 1}')
            ins.append(ti)
            sub = dict(item); sub.setdefault('type', 'wcard' if mode == 'B' else 'label')
            sub.setdefault('size', el.get('size', 46))
            out += anim_group(kits.build(sub, mode), ti, t_out, item.get('anim', kind), x, y + i * gap, 0, sc)
        return out
    return anim_group(kits.build(el, mode), t_in, t_out, kind, x, y, rot, sc)


def build(project_dir, out_dir=None):
    cfg = load_config()
    pdir = os.path.abspath(project_dir)
    with open(os.path.join(pdir, 'project.json'), encoding='utf-8') as f:
        proj = json.load(f)
    with open(os.path.join(pdir, 'scenes.json'), encoding='utf-8') as f:
        spec = json.load(f)
    mode = proj.get('mode', spec.get('mode', 'A'))
    M = MODES[mode]
    W, H = M['W'], M['H']
    words_path = os.path.join(pdir, spec.get('words', 'words.json'))
    words = load_words(words_path) if os.path.exists(words_path) else []
    anchors = Anchors(words)

    audio = spec.get('audio') or ('audio/vo.mp3' if mode == 'A' else 'build/cut_audio.m4a')
    audio_path = os.path.join(pdir, audio)
    duration = spec.get('duration') or (media_duration(audio_path) if os.path.exists(audio_path) else None)
    if not duration:
        duration = (words[-1]['end'] + 0.8) if words else 10.0

    # scene starts
    scenes = spec.get('scenes', [])
    starts, prev = [], 0.0
    for i, s in enumerate(scenes):
        st = 0.0 if i == 0 and s.get('start') is None else anchors.resolve(s.get('start'), prev, default=None)
        if st is None:
            st = prev + 0.01
            print(f'[warn] scene {s.get("id", i)} start anchor not found: {s.get("start")!r}', file=sys.stderr)
        starts.append(st); prev = st
    ends = starts[1:] + [duration]

    out_dir = out_dir or os.path.join(pdir, 'build')
    os.makedirs(out_dir, exist_ok=True)
    font = os.path.relpath(os.path.join(ROOT, 'fonts', 'Cairo-Variable.ttf'), out_dir).replace(os.sep, '/')

    scene_meta, scene_svg = [], []
    card_pos = 'bottom'
    for i, s in enumerate(scenes):
        st, en = starts[i], ends[i]
        if mode == 'B':
            card_pos = s.get('card') or ('top' if card_pos == 'bottom' else 'bottom')
        els = []
        latest_in = st
        for j, el in enumerate(s.get('elements', [])):
            ins = []
            svg = expand(el, mode, anchors, st, en, j, ins)
            if mode == 'B' and el.get('space') != 'canvas':
                svg = f'<g transform="translate(0,{REGION[card_pos]})">{svg}</g>'
            els.append(svg)
            latest_in = max([latest_in] + [t for t in ins if t < en])
        sb = min(max(latest_in + 0.6, st + 1.0), en - 0.35)
        scene_meta.append({'id': s.get('id', f's{i + 1}'), 'title': s.get('title', ''), 'start': round(st, 3),
                           'end': round(en, 3), 'card': card_pos if mode == 'B' else None,
                           'storyboard_t': round(max(st, sb), 3)})
        scene_svg.append(f'<g class="scene" data-start="{st:.3f}" data-end="{en:.3f}">{"".join(els)}</g>')

    cap_cfg = cfg['captions'][mode]
    captions = []
    if spec.get('captions', True) and words:
        captions = chunk_captions(words, cap_cfg['min_words'], cap_cfg['max_words'], max_chars=cap_cfg.get('max_chars', 26),
                                  orphan_slack=cap_cfg.get('orphan_slack', 1))

    brand = spec.get('brand', proj.get('brand', cfg.get('brand', '')))
    show_badge = spec.get('badge', mode == 'A') and brand

    data = {'mode': mode, 'W': W, 'H': H, 'fps': M['fps'], 'duration': duration, 'card': CARD,
            'scenes': scene_meta, 'captions': captions, 'cap': cap_cfg}

    g = M['grid']
    bg = f'''<svg id="bg" width="{W}" height="{H}" style="position:absolute;left:0;top:0">
<defs><pattern id="grid" width="{g}" height="{g}" patternUnits="userSpaceOnUse">
<path d="M{g},0 L0,0 0,{g}" fill="none" stroke="{M['grid_color']}" stroke-width="1.5"/></pattern>
<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="7"/>
<feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .09 0"/></filter></defs>
<rect width="{W}" height="{H}" fill="{M['bg']}"/><rect width="{W}" height="{H}" fill="url(#grid)"/>
{'<rect width="%d" height="%d" filter="url(#grain)"/>' % (W, H) if mode == 'A' else ''}</svg>'''

    card_html = ''
    if mode == 'B':
        card_html = (f'<div id="card" style="position:absolute;left:{CARD["x"]}px;top:{CARD["top"]}px;'
                     f'width:{CARD["w"]}px;height:{CARD["h"]}px;border:7px solid #222;border-radius:44px;'
                     'box-sizing:border-box;overflow:hidden;background:#333;box-shadow:12px 14px 0 rgba(34,34,34,.22)">'
                     '<img id="cardimg" style="width:100%;height:100%;object-fit:cover;display:block" alt=""></div>')

    fg = (f'<svg id="fg" width="{W}" height="{H}" style="position:absolute;left:0;top:0" '
          f'font-family="Cairo, sans-serif"><defs>'
          '<pattern id="hatch" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
          '<rect width="12" height="12" fill="rgba(34,34,34,.10)"/><line x1="0" y1="0" x2="0" y2="12" stroke="#222" stroke-width="3"/></pattern>'
          f'</defs>{"".join(scene_svg)}</svg>')

    badge = ''
    if show_badge:
        badge = (f'<div id="badge" style="position:absolute;top:{36 if mode == "A" else 40}px;left:28px;'
                 'background:#f3efe4;color:#1b1b1b;font:800 24px Cairo;padding:6px 18px;transform:rotate(-3deg);'
                 f'box-shadow:4px 5px 0 rgba(0,0,0,.18)">{esc(brand)}</div>')

    if mode == 'A':
        cap_style = (f'position:absolute;left:50%;top:{cap_cfg["y"]}px;transform:translate(-50%,-50%);'
                     f'max-width:{W - 80}px;background:#141414;color:#fff;font:{cap_cfg["weight"]} {cap_cfg["size"]}px Cairo;'
                     'padding:8px 26px 12px;border-radius:16px;text-align:center;white-space:nowrap;display:none')
    else:
        cap_style = (f'position:absolute;left:{CARD["x"] + CARD["w"] / 2}px;transform:translateX(-50%);'
                     f'background:rgba(20,20,20,.78);color:#fff;font:{cap_cfg["weight"]} {cap_cfg["size"]}px Cairo;'
                     'padding:6px 26px 12px;border-radius:18px;white-space:nowrap;display:none')

    with open(os.path.join(os.path.dirname(__file__), 'runtime.js'), encoding='utf-8') as f:
        runtime = f.read()

    page = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<style>@font-face{{font-family:Cairo;src:url("{font}") format("truetype");font-weight:200 1000}}
html,body{{margin:0;background:#000}} #stage{{position:relative;width:{W}px;height:{H}px;overflow:hidden}}
.a{{transform-box:fill-box;transform-origin:center;opacity:0}} text{{font-family:Cairo}}</style></head>
<body><div id="stage">{bg}{card_html}{fg}{badge}<div id="cap" style="{cap_style}"></div></div>
<script>window.D={json.dumps(data, ensure_ascii=False)};</script><script>{runtime}</script></body></html>'''

    with open(os.path.join(out_dir, 'page.html'), 'w', encoding='utf-8') as f:
        f.write(page)
    meta = dict(data)
    meta.update({'scale': M['scale'], 'audio': audio if os.path.exists(audio_path) else None,
                 'anchor_misses': anchors.misses, 'words': len(words)})
    with open(os.path.join(out_dir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return meta


if __name__ == '__main__':
    m = build(sys.argv[1])
    print(json.dumps({'duration': m['duration'], 'scenes': len(m['scenes']), 'captions': len(m['captions']),
                      'anchor_misses': m['anchor_misses']}, ensure_ascii=False))
