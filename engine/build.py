"""Build a deterministic HTML page (window.setTime(t)) from a project's scenes.json."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from timing import Anchors, chunk_captions, load_words, norm  # noqa: E402
import kits  # noqa: E402
import charts  # noqa: E402
import fx  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODES = {
    'A': {'W': 720, 'H': 1280, 'scale': 1.5, 'fps': 24, 'bg': '#e8e4da', 'grid': 40, 'grid_color': '#cfc9bb'},
    'B': {'W': 1080, 'H': 1920, 'scale': 1.0, 'fps': 30, 'bg': '#f4eddd', 'grid': 54, 'grid_color': '#e2d9c4'},
}
CARD = {'x': 40, 'top': 130, 'bottom': 900, 'w': 1000, 'h': 920}
CARD_SLIDE = 0.45                      # must match SLIDE in runtime.js
# Mode B talking-head layouts: card rectangle (canvas px), corner radius, border, and the origin/height
# of the graphics region elements are placed in (element y is measured from region y0).
LAYOUTS = {
    'top':       {'x': 40,  'y': 130, 'w': 1000, 'h': 920,  'r': 44, 'b': 7, 'y0': 1080, 'rh': 820},
    'bottom':    {'x': 40,  'y': 900, 'w': 1000, 'h': 920,  'r': 44, 'b': 7, 'y0': 60,   'rh': 820},
    'hero':      {'x': 40,  'y': 130, 'w': 1000, 'h': 1300, 'r': 44, 'b': 7, 'y0': 1460, 'rh': 420},
    'full':      {'x': 0,   'y': 0,   'w': 1080, 'h': 1920, 'r': 0,  'b': 0, 'y0': 1080, 'rh': 780},
    'pip-right': {'x': 690, 'y': 150, 'w': 350,  'h': 430,  'r': 36, 'b': 6, 'y0': 620,  'rh': 1200},
    'pip-left':  {'x': 40,  'y': 150, 'w': 350,  'h': 430,  'r': 36, 'b': 6, 'y0': 620,  'rh': 1200},
    'half-top':    {'x': 0, 'y': 0,   'w': 1080, 'h': 960, 'r': 0, 'b': 0, 'y0': 1000, 'rh': 880},   # split screen
    'half-bottom': {'x': 0, 'y': 960, 'w': 1080, 'h': 960, 'r': 0, 'b': 0, 'y0': 40,   'rh': 880},
    # collage: the speaker as a paper sticker (cut-out with white outline), no video rectangle
    'sticker':     {'x': 300, 'y': 700, 'w': 760, 'h': 1220, 'r': 0, 'b': 0, 'y0': 60, 'rh': 760, 'rot': -3, 'sticker': 1},
}
BASE_LAYOUTS = json.loads(json.dumps(LAYOUTS))
# Look 2: no tiny talking heads. Bigger PiP (480×600 instead of 350×430), a 'split' layout (big speaker, roomy graphics
# area) and a larger sticker. Look 1 projects keep the layouts they were approved with.
LAYOUTS_V2 = {
    'pip-right': {'x': 560, 'y': 130, 'w': 480, 'h': 600, 'r': 40, 'b': 6, 'y0': 760, 'rh': 1000},
    'pip-left':  {'x': 40,  'y': 130, 'w': 480, 'h': 600, 'r': 40, 'b': 6, 'y0': 760, 'rh': 1000},
    'split':     {'x': 40,  'y': 110, 'w': 1000, 'h': 760, 'r': 44, 'b': 7, 'y0': 900, 'rh': 760},
    'sticker':   {'x': 200, 'y': 620, 'w': 860, 'h': 1300, 'r': 0, 'b': 0, 'y0': 60, 'rh': 700, 'rot': -3, 'sticker': 1},
}
STYLE_V2 = {'data': {'layout': 'split'}, 'whiteboard': {'layout': 'split'}, 'editorial': {}}
SPEAKER_FIRST_GAP = 2.0          # s without graphics after a scene starts → keep the speaker big until they arrive
SPEAKER_FIRST_FROM = ('top', 'bottom', 'split', 'pip-left', 'pip-right', 'sticker')


def set_look(look):
    """Activate a look: layouts and text sizes. Called at the start of every build."""
    LAYOUTS.clear(); LAYOUTS.update(json.loads(json.dumps(BASE_LAYOUTS)))
    if look >= 2:
        LAYOUTS.update(json.loads(json.dumps(LAYOUTS_V2)))
    REGION.clear(); REGION.update({k: v['y0'] for k, v in LAYOUTS.items()})
    kits.LOOK[0] = look


REGION = {k: v['y0'] for k, v in LAYOUTS.items()}

# V2 style mixing: each style is a set of scene defaults (a scene's own keys always win).
STYLES = {
    'editorial':  {'transition': 'cut'},                                                     # 01
    'kinetic':    {'caption_style': 'kinetic', 'transition': 'blur'},                        # 02
    'collage':    {'layout': 'sticker', 'transition': 'zoom'},                               # 03
    'data':       {'layout': 'top', 'transition': 'cut'},                                    # 04
    'parallax':   {'layout': 'full', 'parallax': 1, 'zoom': [1.0, 1.08], 'transition': 'blur'},  # 06
    'battle':     {'layout': 'half-top', 'transition': 'whip'},                              # 07
    'whiteboard': {'layout': 'top', 'transition': 'cut'},                                    # 08
    'cinematic':  {'layout': 'full', 'zoom': [1.0, 1.06], 'transition': 'blur', 'caption_style': 'minimal'},  # 09
}
STYLE_IDS = {'01': 'editorial', '02': 'kinetic', '03': 'collage', '04': 'data', '05': 'floating-ui', '06': 'parallax',
             '07': 'battle', '08': 'whiteboard', '09': 'cinematic'}
TRANSITIONS = {'cut': 0, 'blur': 0.18, 'whip': 0.16, 'flash': 0.25, 'zoom': 0.35}   # half-width / length in seconds
CAPTION_STYLES = ('box', 'highlight', 'clean', 'kinetic', 'editorial', 'energy', 'minimal')


LOOK2 = [False]


def style_name(v):
    v = str(v or '').strip().lower()
    return STYLE_IDS.get(v, STYLE_IDS.get(v.zfill(2), v)) if v else ''


def style_mix(scenes, starts, ends, base_style, problems, notes):
    """Resolve each scene's style into scene defaults and check the mix (returns the effective scene dicts)."""
    out, used, prev = [], [], None
    for i, s in enumerate(scenes):
        sty = style_name(s.get('style') or base_style)
        if sty == 'floating-ui':
            problems.append({'anchor': None, 'element': s.get('id', i),
                             'problem': 'style 05 floating UI needs real CEOS screens/recordings (not built yet)'})
            sty = ''
        elif sty and sty not in STYLES:
            problems.append({'anchor': None, 'element': s.get('id', i),
                             'problem': f'unknown style {s.get("style")!r} (use {", ".join(STYLES)} or 01-09)'})
            sty = ''
        e = dict(STYLES.get(sty, {}))
        if LOOK2[0]:
            e.update(STYLE_V2.get(sty, {}))
        e.update(s)
        if sty: e['_style'] = sty
        out.append(e)
        if sty and sty not in used: used.append(sty)
        if i > 0 and sty != prev and ends[i] - starts[i] < 2.0:
            notes.append(f'{s.get("id", i)}: style changes on a {ends[i] - starts[i]:.1f} s scene (mixing reads best on scenes ≥ 2 s)')
        prev = sty
    if len(used) > 3:
        notes.append(f'{len(used)} styles in one reel ({", ".join(used)}): more than 3 usually reads as noise')
    fancy = [e for e in out[1:] if e.get('transition', 'cut') != 'cut']
    total = (ends[-1] - starts[0]) if out else 0
    if total and len(fancy) > max(2, total / 5):
        notes.append(f'{len(fancy)} non-cut transitions in {total:.0f} s: keep them for real section changes (≈1 per 5 s at most)')
    return out
PROJECT = {'dir': '', 'out': '', 'n': 0}     # set per build (photo assets are resolved against the project)


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


CUR_TYPE = ['']                                                 # element type being expanded (for inspection)
CAP_MUTE = []                                                    # [start, end] windows where captions step aside


def anim_group(inner, t_in, t_out, kind, x=0, y=0, rot=0, scale=1, extra='', exit='fade'):
    return (f'<g class="a" data-in="{t_in:.3f}" data-out="{t_out:.3f}" data-k="{kind}" data-x="{exit}" '
            f'data-type="{CUR_TYPE[0]}" {extra}>'
            f'<g transform="translate({x},{y}) rotate({rot}) scale({scale})">{inner}</g></g>')


def flag_late(anchors, spec, t, t_out, s_start, what):
    """An element that comes in at/after the moment it leaves would never be seen: report it."""
    if t >= t_out - 1e-6:
        anchors.misses.append({'anchor': spec, 'after': round(s_start, 2), 'element': what,
                               'problem': f'comes in at {t:.2f}s, after it leaves ({t_out:.2f}s), so it never appears'})


def expand(el, mode, anchors, s_start, s_end, idx, ins=None, floor=None):
    """Return SVG for one element (seats and steps expand to several animated groups).
    floor: earliest allowed in-time (Mode B: after the face card has finished sliding)."""
    ins = ins if ins is not None else []
    t_in = anchors.resolve(el.get('in'), s_start, default=s_start + 0.2 + 0.12 * idx)
    if floor is not None:
        t_in = max(t_in, floor)
    t_out = anchors.resolve(el.get('out'), s_start, default=s_end)
    t_out = min(t_out, s_end)
    what = el.get('text') or el.get('hl') or el.get('title') or el.get('name') or el['type']
    flag_late(anchors, el.get('in'), t_in, t_out, s_start, what)
    ins.append(t_in)
    kind = el.get('anim', 'pop')
    ex = el.get('exit', 'fade')
    x, y, rot, sc = el.get('x', 0), el.get('y', 0), el.get('rot', 0), el.get('scale', 1)
    t = el['type']
    CUR_TYPE[0] = t
    if t == 'equation':
        return expand_equation(el, mode, anchors, s_start, t_in, t_out, ins, floor, kind, ex)
    if t == 'photo':
        src = os.path.join(PROJECT['dir'], el.get('src', ''))
        if not el.get('src') or not os.path.isfile(src):
            anchors.misses.append({'anchor': None, 'element': 'photo', 'problem': f'missing asset {el.get("src")!r} (put it in assets/)'})
            return ''
        PROJECT['n'] += 1
        href = os.path.relpath(src, PROJECT['out']).replace(os.sep, '/')
        return anim_group(kits.photo_svg(el, href, PROJECT['n']), t_in, t_out, kind, x, y, rot, sc, exit=ex)
    if t in charts.TYPES or t in fx.TYPES:
        return expand_chart(el, mode, anchors, s_start, t_in, t_out, ins, floor, kind, ex)
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
            if floor is not None:
                ti = max(ti, floor)
            flag_late(anchors, item.get('in'), ti, t_out, s_start, item.get('text') or f'steps item {i + 1}')
            ins.append(ti)
            sub = dict(item); sub.setdefault('type', 'wcard' if mode == 'B' else 'label')
            sub.setdefault('size', el.get('size', 46))
            out += anim_group(kits.build(sub, mode), ti, t_out, item.get('anim', kind), x, y + i * gap, 0, sc)
        return out
    return anim_group(kits.build(el, mode), t_in, t_out, kind, x, y, rot, sc, exit=ex)


def equation_result(el):
    """Evaluate an equation element: rows [{value, op}] (first row has no op). Returns (total, problems)."""
    rows = el.get('rows', [])
    problems, total = [], 0.0
    for i, r in enumerate(rows):
        v = r.get('value')
        if not isinstance(v, (int, float)):
            problems.append(f'row {i + 1} ({r.get("label", "")!r}) has no numeric value')
            continue
        op = r.get('op', '+' if i else '=')
        if i and op not in ('+', '-'):
            problems.append(f'row {i + 1}: op must be "+" or "-"')
        total = v if i == 0 else (total + v if op == '+' else total - v)
    res = el.get('result', {})
    if 'value' in res and abs(res['value'] - total) > 1e-6:
        problems.append(f'result says {res["value"]:,} but the rows add up to {total:,}')
    if res.get('tone') == 'negative' and total >= 0 or res.get('tone') == 'positive' and total < 0:
        problems.append(f'result tone {res.get("tone")!r} contradicts the computed total {total:,}')
    return total, problems


def expand_equation(el, mode, anchors, s_start, t_in, t_out, ins, floor, kind, ex):
    """Financial equation: one row per term (label, value, operator in its own glyph so RTL never flips a minus),
    then a rule and the computed result. The arithmetic is checked here; problems block the render."""
    total, problems = equation_result(el)
    for p in problems:
        anchors.misses.append({'anchor': None, 'element': 'equation', 'problem': 'finance: ' + p})
    x, y = el.get('x', 540), el.get('y', 0)
    gap, size, w = el.get('gap', 104), el.get('size', 50), el.get('w', 860)
    out = ''
    rows = el.get('rows', [])
    for i, r in enumerate(rows):
        ti = anchors.resolve(r.get('in'), s_start, default=t_in + 0.5 * i)
        if floor is not None:
            ti = max(ti, floor)
        flag_late(anchors, r.get('in'), ti, t_out, s_start, r.get('label', f'row {i + 1}'))
        ins.append(ti)
        out += anim_group(kits.eq_row(r, i, size, w, mode), ti, t_out, r.get('anim', 'slide-left'), x, y + i * gap, exit=ex)
    res = el.get('result', {})
    tr = anchors.resolve(res.get('in'), s_start, default=t_in + 0.5 * len(rows))
    if floor is not None:
        tr = max(tr, floor)
    flag_late(anchors, res.get('in'), tr, t_out, s_start, 'equation result')
    ins.append(tr)
    out += anim_group(kits.eq_result(res, total, size, w, mode), tr, t_out, res.get('anim', 'stamp'), x,
                      y + len(rows) * gap + 30, exit=ex)
    return out


def expand_chart(el, mode, anchors, s_start, t_in, t_out, ins, floor, kind, ex):
    """Charts/fx: one time per bar/segment/stage/point/node (their own `in`, else staggered), checked numbers."""
    mod = charts if el['type'] in charts.TYPES else fx
    if el['type'] == 'kinetic':
        el['_words'] = fx.kinetic_words(el, anchors, s_start)
        if el['_words']:
            t_in = max(t_in if el.get('in') else el['_words'][0]['start'], floor or 0)
    _, problems = mod.check(el)
    for p in problems:
        anchors.misses.append({'anchor': None, 'element': el['type'], 'problem': 'finance: ' + p})
    if problems and el['type'] in ('waterfall', 'donut', 'funnel', 'breakeven', 'scorecard', 'beforeafter', 'kinetic'):
        return ''
    times = []
    for i, it in enumerate(mod.item_specs(el)):
        ti = t_in if (i == 0 and not it.get('in')) else anchors.resolve(it.get('in'), s_start, default=t_in + 0.5 * i)
        if floor is not None:
            ti = max(ti, floor)
        ti = max(ti, t_in)
        flag_late(anchors, it.get('in'), ti, t_out, s_start, it.get('label') or f'{el["type"]} item {i + 1}')
        times.append(ti); ins.append(ti)
    ref = el.get('ref')
    if ref:
        rt = anchors.resolve(ref.get('in'), s_start, default=times[-1] + 0.5 if times else t_in)
        ref['_t'] = max(rt, t_in)
        flag_late(anchors, ref.get('in'), ref['_t'], t_out, s_start, 'reference line')
        ins.append(ref['_t'])
    x, y = el.get('x', 540), el.get('y', 0)
    if el['type'] == 'kinetic':
        ins.append(el['_words'][-1]['start'])
        if LOOK2[0] and el.get('mute_caption', True):       # the words are on screen already: no duplicate caption
            CAP_MUTE.append([round(el['_words'][0]['start'] - 0.05, 3), round(el['_words'][-1]['end'] + 0.25, 3)])
    return anim_group(mod.build(el, times), t_in, t_out, kind if kind != 'pop' else 'none', x, y, exit=ex)


def apply_brand(name, cfg):
    """Reset palettes, then apply a brand preset from studio.config.json (colors only; fonts stay Cairo)."""
    kits.reset_palettes()
    brand = cfg.get('brands', {}).get(name or '', {})
    kits.B.update(brand.get('palette', {}))
    m = dict(MODES['B'])
    m.update({k: brand[k] for k in ('bg', 'grid_color') if k in brand})
    return m


def rj_safe(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def card_frame_info(out_dir):
    """Full-frame card frames (1080x1920) let layouts crop/zoom freely; legacy frames are pre-cropped."""
    cf = os.path.join(out_dir, 'cf', '00001.png')
    if not os.path.exists(cf):
        return {'full': False}
    try:
        from PIL import Image
        with Image.open(cf) as im:
            w, h = im.size
    except Exception:
        return {'full': False}
    return {'full': (w, h) == (1080, 1920), 'w': w, 'h': h}


def build(project_dir, out_dir=None):
    cfg = load_config()
    pdir = os.path.abspath(project_dir)
    with open(os.path.join(pdir, 'project.json'), encoding='utf-8') as f:
        proj = json.load(f)
    with open(os.path.join(pdir, 'scenes.json'), encoding='utf-8') as f:
        spec = json.load(f)
    mode = proj.get('mode', spec.get('mode', 'A'))
    look = int(spec.get('look', proj.get('look', 1)) or 1)
    set_look(look); LOOK2[0] = look >= 2
    CAP_MUTE.clear()
    M = MODES[mode]
    brand_cfg = {}
    brand_problem = None
    if mode == 'B':
        if spec.get('brand') and spec['brand'] not in cfg.get('brands', {}):
            brand_problem = f'unknown brand {spec["brand"]!r} (use {", ".join(cfg.get("brands", {}))})'
        brand_cfg = json.loads(json.dumps(cfg.get('brands', {}).get(spec.get('brand') or '', {})))
        ov = spec.get('brand_overrides') or {}
        for k, v in ov.items():                                   # project-level tweaks; the preset file is never changed
            if k == 'palette':
                brand_cfg.setdefault('palette', {}).update(v)
            else:
                brand_cfg[k] = v
        M = apply_brand(spec.get('brand'), {'brands': {spec.get('brand') or '': brand_cfg}})
    else:
        kits.reset_palettes()
    W, H = M['W'], M['H']
    words_path = os.path.join(pdir, spec.get('words', 'words.json'))
    words = load_words(words_path) if os.path.exists(words_path) else []
    fx.WORDS = words
    PROJECT.update(dir=pdir, out=out_dir or os.path.join(pdir, 'build'), n=0)
    anchors = Anchors(words)
    if brand_problem:
        anchors.misses.append({'anchor': None, 'element': 'brand', 'problem': brand_problem})

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
    notes = []
    if mode == 'B':
        scenes = style_mix(scenes, starts, ends, spec.get('style'), anchors.misses, notes)

    out_dir = out_dir or os.path.join(pdir, 'build')
    os.makedirs(out_dir, exist_ok=True)
    font = os.path.relpath(os.path.join(ROOT, 'fonts', 'Cairo-Variable.ttf'), out_dir).replace(os.sep, '/')

    scene_meta, scene_svg, behind_svg = [], [], []
    cut_dir = os.path.join(out_dir, 'cut')
    has_cut = mode == 'B' and os.path.isdir(cut_dir) and any(f.endswith('.png') for f in os.listdir(cut_dir))
    maskq = (rj_safe(os.path.join(out_dir, 'mask', 'quality.json')) or {}).get('per_frame', []) if has_cut else []
    card_pos = 'bottom'
    for i, s in enumerate(scenes):
        st, en = starts[i], ends[i]
        prev_pos = card_pos
        if mode == 'B':
            card_pos = s.get('layout') or s.get('card') or ('top' if card_pos == 'bottom' else 'bottom')
            if card_pos not in LAYOUTS:
                anchors.misses.append({'anchor': None, 'element': s.get('id', i),
                                       'problem': f'unknown layout {card_pos!r} (use {", ".join(LAYOUTS)})'})
                card_pos = 'top'
        # Mode B: the card slides for CARD_SLIDE s when it changes side; graphics wait until it has landed
        floor = st + CARD_SLIDE if (mode == 'B' and i > 0 and card_pos != prev_pos) else None
        els, behind = [], []
        latest_in = st
        first_ins = []
        for j, el in enumerate(s.get('elements', [])):
            ins = []
            svg = expand(el, mode, anchors, st, en, j, ins,
                         floor=None if el.get('space') == 'canvas' else floor)
            if mode == 'B' and el.get('space') != 'canvas':
                svg = f'<g transform="translate(0,{LAYOUTS[card_pos]["y0"]})">{svg}</g>'
            (behind if (el.get('behind') and has_cut) else els).append(svg)
            if el.get('behind') and not has_cut:
                notes.append(f'{s.get("id", i)}: "behind" element drawn in front (run reel.py segment for cut-outs)')
            latest_in = max([latest_in] + [t for t in ins if t < en])
            first_ins += ins[:1]
        sb = min(max(latest_in + 0.6, st + 1.0), en - 0.35)
        cam = {}
        if mode == 'B' and LOOK2[0] and s.get('speaker_first', True) and card_pos in SPEAKER_FIRST_FROM:
            first = min([t for t in first_ins if t < en] or [en])
            if first - st >= SPEAKER_FIRST_GAP:
                # nothing to look at yet: the speaker stays big, the card moves to the layout as the graphics arrive
                cam['pre'] = ['hero', round(min(first, en) - (CARD_SLIDE if first < en else 0), 3)]
        if mode == 'B':
            z = s.get('zoom')                                    # slow drift: [start, end] scale over the scene
            if z:
                cam['zoom'] = [float(z[0]), float(z[1])] if isinstance(z, list) else [float(z), float(z)]
            if s.get('punch'):                                   # punch-in on a word: {"at": anchor, "zoom": 1.25}
                pt = anchors.resolve(s['punch'].get('at'), st, default=st)
                cam['punch'] = [round(pt, 3), float(s['punch'].get('zoom', 1.22))]
            if s.get('parallax'):
                cam['parallax'] = float(s['parallax'] if not isinstance(s['parallax'], bool) else 1.0)
            tr = s.get('transition') or (brand_cfg.get('transition') if i > 0 else None) or 'cut'
            if tr not in TRANSITIONS:
                anchors.misses.append({'anchor': None, 'element': s.get('id', i),
                                       'problem': f'unknown transition {tr!r} (use {", ".join(TRANSITIONS)})'})
                tr = 'cut'
            if i > 0 and tr != 'cut':
                cam['tr'] = [tr, TRANSITIONS[tr]]
            if s.get('caption_style'):
                if s['caption_style'] not in CAPTION_STYLES:
                    anchors.misses.append({'anchor': None, 'element': s.get('id', i),
                                           'problem': f'unknown caption_style {s["caption_style"]!r}'})
                else:
                    cam['cap'] = s['caption_style']
            if s.get('_style'):
                cam['style'] = s['_style']
            if has_cut:
                # cut-out effects are decided per scene (no flicker between cut-out and fallback frame to frame):
                # the scene keeps them if at most 15% of its frames fall below the mask threshold
                f0, f1 = int(st * M['fps']), max(int(st * M['fps']) + 1, int(en * M['fps']))
                qs = (maskq + [0.0] * f1)[f0:f1]
                low = sum(1 for q in qs if q < spec.get('mask_min_quality', 0.62)) / max(1, len(qs))
                cam['cutok'] = low <= spec.get('mask_max_low', 0.15)
                uses = s.get('layout') == 'sticker' or s.get('parallax') or any(e.get('behind') for e in s.get('elements', []))
                if uses and not cam['cutok']:
                    notes.append(f'{s.get("id", i)}: {low:.0%} of frames have a weak speaker mask: cut-out effects fall '
                                 'back to a normal frame for the whole scene')
        scene_meta.append({'id': s.get('id', f's{i + 1}'), 'title': s.get('title', ''), 'start': round(st, 3),
                           'end': round(en, 3), 'card': card_pos if mode == 'B' else None,
                           'storyboard_t': round(max(st, sb), 3), **cam})
        scene_svg.append(f'<g class="scene" data-start="{st:.3f}" data-end="{en:.3f}">{"".join(els)}</g>')
        behind_svg.append(f'<g class="scene" data-start="{st:.3f}" data-end="{en:.3f}">{"".join(behind)}</g>')

    cap_cfg = cfg['captions'][mode]
    film = spec.get('film') or ({'grain': 0.07, 'letterbox': False} if spec.get('style') == 'cinematic' else None)
    film_html = ''
    if film and mode == 'B':
        if film.get('grain'):
            film_html += (f'<svg id="grain" width="{W}" height="{H}" style="position:absolute;left:0;top:0;pointer-events:none;'
                          f'mix-blend-mode:overlay;opacity:{float(film["grain"]):.3f}"><filter id="gr"><feTurbulence id="grt" '
                          f'type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="1"/><feColorMatrix type="saturate" values="0"/>'
                          f'</filter><rect width="100%" height="100%" filter="url(#gr)"/></svg>')
        if film.get('letterbox'):
            lb = int(film.get('letterbox_px', 150))
            film_html += (f'<div style="position:absolute;left:0;top:0;width:{W}px;height:{lb}px;background:#000"></div>'
                          f'<div style="position:absolute;left:0;bottom:0;width:{W}px;height:{lb}px;background:#000"></div>')
    captions = []
    if spec.get('captions', True) and words:
        captions = chunk_captions(words, cap_cfg['min_words'], cap_cfg['max_words'], max_chars=cap_cfg.get('max_chars', 26),
                                  orphan_slack=cap_cfg.get('orphan_slack', 1))
        kw = [norm(k) for k in spec.get('caption_keywords', []) if norm(k)]
        for c in captions:
            c['hl'] = [j for j, wd in enumerate(c['text'].split()) if kw and any(k in norm(wd) for k in kw)]

    brand = spec.get('brand', proj.get('brand', cfg.get('brand', '')))
    show_badge = spec.get('badge', mode == 'A') and brand

    cfi = card_frame_info(out_dir) if mode == 'B' else {'full': False}
    focus = spec.get('focus')
    if not focus:
        crop = (rj_safe(os.path.join(pdir, 'cuts.json')) or {}).get('crop')
        fy = 0.45
        if crop:
            cw, ch, cx, cy = [float(v) for v in crop.split(':')]
            fy = (cy + ch / 2) / 2560 if cw == 1440 else 0.45
        focus = [0.5, round(fy, 3)]
    caption_style = spec.get('caption_style') or brand_cfg.get('caption_style') or 'box'
    data = {'mode': mode, 'W': W, 'H': H, 'fps': M['fps'], 'duration': duration, 'card': CARD,
            'layouts': LAYOUTS, 'slide': CARD_SLIDE, 'cf': cfi, 'focus': focus, 'capStyle': caption_style,
            'hlColor': kits.B['yellow'], 'scenes': scene_meta, 'captions': captions, 'cap': cap_cfg,
            'cut': has_cut, 'maskq': maskq, 'maskMin': spec.get('mask_min_quality', 0.62),
            'film': bool(film and film.get('grain')), 'audio_peak_db': cfg.get('output', {}).get('audio_peak_db'),
            'look': look, 'capMute': CAP_MUTE}

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
                     '<img id="cardimg" style="position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;display:block" alt=""></div>')

    cut_html = behind_html = ''
    if mode == 'B' and has_cut:
        behind_html = (f'<svg id="behind" width="{W}" height="{H}" style="position:absolute;left:0;top:0" '
                       f'font-family="Cairo, sans-serif">{"".join(behind_svg)}</svg>')
        cut_html = ('<div id="cut" style="position:absolute;overflow:hidden;box-sizing:border-box;border:0 solid transparent;'
                    'pointer-events:none"><img id="cutimg" style="position:absolute;left:0;top:0;display:block" alt=""></div>')
    card_html += behind_html + cut_html
    fg = (f'<svg id="fg" width="{W}" height="{H}" style="position:absolute;left:0;top:0" '
          f'font-family="Cairo, sans-serif"><defs>'
          '<pattern id="hatch" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
          '<rect width="12" height="12" fill="rgba(34,34,34,.10)"/><line x1="0" y1="0" x2="0" y2="12" stroke="#222" stroke-width="3"/></pattern>'
          '<filter id="sepia"><feColorMatrix type="matrix" values=".39 .77 .19 0 0  .35 .69 .17 0 0  .27 .53 .13 0 0  0 0 0 1 0"/></filter>'
          f'</defs>{"".join(scene_svg)}</svg>')

    trs = {m['tr'][0] for m in scene_meta if m.get('tr')}
    main_html = card_html + fg
    if trs:
        main_html = (f'<div id="main" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;'
                     f'transform-origin:50% 45%">{main_html}</div>')
        if 'flash' in trs:
            main_html += f'<div id="flash" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;background:#fff;opacity:0"></div>'
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
<body><div id="stage">{bg}{main_html}{film_html}{badge}<div id="cap" style="{cap_style}"></div></div>
<script>window.D={json.dumps(data, ensure_ascii=False)};</script><script>{runtime}</script></body></html>'''

    with open(os.path.join(out_dir, 'page.html'), 'w', encoding='utf-8') as f:
        f.write(page)
    meta = dict(data)
    meta.update({'scale': M['scale'], 'audio': audio if os.path.exists(audio_path) else None,
                 'anchor_misses': anchors.misses, 'words': len(words), 'notes': notes})
    with open(os.path.join(out_dir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return meta


if __name__ == '__main__':
    m = build(sys.argv[1])
    print(json.dumps({'duration': m['duration'], 'scenes': len(m['scenes']), 'captions': len(m['captions']),
                      'anchor_misses': m['anchor_misses']}, ensure_ascii=False))
