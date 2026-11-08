"""Styles 02 (kinetic typography), 07 (split-screen battles), 08 (hand-drawn whiteboard).

Same contract as charts.py: TYPES, item_specs(el), check(el) -> (computed, problems), build(el, times).
Runtime classes used: .tl/.grow/.draw (charts), plus
  .kin  (kinetic phrase: runtime lays words out right-to-left, then animates each .kw at its spoken time)
  .dim  (fades to 40% at data-t0: the losing side of a comparison)
"""
import hashlib
import math

import kits
from kits import esc, fmt_num, text

TYPES = ('kinetic', 'versus', 'scorecard', 'beforeafter', 'circle_mark', 'underline', 'hand_arrow', 'flow', 'numbered')
WORDS = []          # set by build.py before scenes are expanded: [{'text','start','end'}] on the edited timeline


def col(name):
    return kits.B.get(name, name)


def t0(times, i, d=0.4, cls='tl', extra=''):
    return f'class="{cls}" data-t0="{times[i]:.3f}" data-d="{d}" {extra}'


def iso(s):
    return '⁦' + s + '⁩'


# ------------------------------------------------------------------ hand-drawn geometry (deterministic)
def _rng(seed):
    h = hashlib.md5(str(seed).encode()).digest()
    i = 0
    while True:
        yield (h[i % 16] / 255.0 - 0.5)
        i += 1
        if i % 16 == 0:
            h = hashlib.md5(h).digest()


def rough_rect(w, h, seed, j=6):
    r = _rng(seed)
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2), (-w / 2, -h / 2)]
    d = f'M {pts[0][0] + next(r) * j:.1f} {pts[0][1] + next(r) * j:.1f}'
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        mx, my = (x0 + x1) / 2 + next(r) * j * 1.5, (y0 + y1) / 2 + next(r) * j * 1.5
        d += f' Q {mx:.1f} {my:.1f} {x1 + next(r) * j:.1f} {y1 + next(r) * j:.1f}'
    return d


def rough_ellipse(rx, ry, seed, turns=1.15):
    r = _rng(seed)
    n = 28
    pts = []
    for i in range(int(n * turns) + 1):
        a = -math.pi * 0.6 + 2 * math.pi * i / n
        k = 1 + next(r) * 0.08
        pts.append((rx * k * math.cos(a), ry * k * math.sin(a)))
    return 'M ' + ' L '.join(f'{x:.1f} {y:.1f}' for x, y in pts)


def stroke(d, color, width, t, dur, extra=''):
    return (f'<path class="draw" data-t0="{t:.3f}" data-d="{dur}" d="{d}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" {extra}/>')


def arrow_path(x0, y0, x1, y1, bend=0.18):
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    cx, cy = mx - dy * bend, my + dx * bend
    ang = math.atan2(y1 - cy, x1 - cx)
    head = 30
    h1 = (x1 - head * math.cos(ang - 0.45), y1 - head * math.sin(ang - 0.45))
    h2 = (x1 - head * math.cos(ang + 0.45), y1 - head * math.sin(ang + 0.45))
    return (f'M {x0:.1f} {y0:.1f} Q {cx:.1f} {cy:.1f} {x1:.1f} {y1:.1f}',
            f'M {h1[0]:.1f} {h1[1]:.1f} L {x1:.1f} {y1:.1f} L {h2[0]:.1f} {h2[1]:.1f}')


# ------------------------------------------------------------------ specs / checks
def kinetic_words(el, anchors, s_start):
    """The exact spoken words for the phrase (never rewritten): from `from` up to `to` (inclusive) or `count`."""
    if not WORDS:
        return []
    t_from = anchors.resolve(el.get('from', el.get('in')), s_start, default=s_start)
    ws = [w for w in WORDS if w['start'] >= t_from - 0.02]
    if el.get('to'):
        t_to = anchors.resolve(el['to'], t_from, default=None)
        ws = [w for w in ws if t_to is not None and w['start'] <= t_to + 0.02]
    else:
        ws = ws[:el.get('count', 4)]
    return ws


def item_specs(el):
    t = el['type']
    if t == 'versus':
        a, b = el.get('a', {}), el.get('b', {})
        return [a] + list(a.get('items', [])) + [b] + list(b.get('items', [])) + [{'in': el.get('in_winner')}]
    if t == 'scorecard':
        return list(el.get('rows', [])) + [{'in': el.get('in_winner')}]
    if t == 'beforeafter':
        return [el.get('before', {}), el.get('after', {}), {'in': el.get('in_change')}]
    if t == 'flow':
        return list(el.get('nodes', []))
    if t == 'numbered':
        return list(el.get('steps', []))
    if t == 'hand_arrow':
        return [el]
    return [el]


def check(el):
    t = el['type']
    p = []
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)  # noqa: E731
    if t == 'kinetic':
        if not el.get('_words'):
            p.append('kinetic phrase found no spoken words in its range (check from/to anchors)')
        return None, p
    if t == 'versus':
        if el.get('winner') not in (None, 'a', 'b'):
            p.append('winner must be "a" (shown on the right) or "b"')
        return None, p
    if t == 'scorecard':
        rows = el.get('rows', [])
        if not rows:
            p.append('scorecard has no rows'); return None, p
        for i, r in enumerate(rows):
            if not (num(r.get('a')) and num(r.get('b'))):
                p.append(f'row {i + 1} ({r.get("label", "")!r}) needs numeric a and b')
        if p:
            return None, p
        ta, tb = sum(r['a'] for r in rows), sum(r['b'] for r in rows)
        lower = el.get('lower_is_better', False)
        win = None if ta == tb else (('a' if ta < tb else 'b') if lower else ('a' if ta > tb else 'b'))
        if el.get('winner') and el['winner'] != win:
            p.append(f'winner says {el["winner"]!r} but totals are a={fmt_num(ta)} b={fmt_num(tb)} → {win or "tie"}')
        return {'a': ta, 'b': tb, 'winner': win}, p
    if t == 'beforeafter':
        b, a = el.get('before', {}).get('value'), el.get('after', {}).get('value')
        if not (num(b) and num(a)):
            p.append('before and after need numeric values'); return None, p
        if b == 0:
            p.append('before is 0: percent change undefined'); return None, p
        ch = (a - b) / abs(b) * 100
        if num(el.get('change_pct')) and abs(el['change_pct'] - ch) > 0.5:
            p.append(f'change_pct says {el["change_pct"]}% but ({fmt_num(a)} − {fmt_num(b)}) / {fmt_num(b)} = {ch:.1f}%')
        better = el.get('better', 'higher')
        good = (ch > 0) == (better == 'higher') if ch else None
        return {'change': ch, 'good': good}, p
    if t == 'flow' and not el.get('nodes'):
        p.append('flow has no nodes')
    if t == 'numbered' and not el.get('steps'):
        p.append('numbered has no steps')
    return None, p


# ------------------------------------------------------------------ builders
def kinetic(el, times):
    """Words are emitted unpositioned; runtime measures and lays them out right-to-left (data-w wide)."""
    words = el.get('_words', [])
    emph = [kits_norm(e) for e in el.get('emphasis', [])]
    size = el.get('size', 86)
    inten = el.get('intensity', 'medium')
    color = col(el.get('color', 'ink'))
    hl = kits.B['yellow']
    out = f'<g class="kin" data-w="{el.get("w", 920)}" data-size="{size}" data-lh="{el.get("line_height", 1.25)}">'
    for i, w in enumerate(words):
        e = any(k and k in kits_norm(w['text']) for k in emph)
        s = size * (1.35 if e else 1)
        out += (f'<g class="kw" data-t0="{max(w["start"], times[0] if times else 0):.3f}" data-int="{inten}" data-emph="{int(e)}">'
                + (f'<rect class="kwbg" fill="{hl}" rx="10"/>' if e else '')
                + f'<text font-size="{s:.0f}" font-weight="900" fill="{color}" text-anchor="middle" '
                  f'dominant-baseline="central" direction="rtl">{esc(w["text"].rstrip(".،,؛!؟?") or w["text"])}</text></g>')
    return out + '</g>'


def kits_norm(s):
    from timing import norm
    return norm(s)


def panel(side, x, w, h, times, k0, color, winner_side, t_win):
    title = side.get('title', '')
    items = side.get('items', [])
    out = (f'<g {t0(times, k0, 0.45, "grow", chr(32) + "data-o=" + chr(39) + "50% 0%" + chr(39))}>'
           f'<rect x="{x - w / 2}" y="{-h / 2}" width="{w}" height="{h}" rx="28" fill="#fff" stroke="{kits.B["ink"]}" stroke-width="6"/>'
           f'<rect x="{x - w / 2}" y="{-h / 2}" width="{w}" height="110" rx="28" fill="{color}" stroke="{kits.B["ink"]}" stroke-width="6"/></g>')
    out += f'<g {t0(times, k0, 0.3)}>' + text(title, 50, '#fff', 900, x=x, y=-h / 2 + 55) + '</g>'
    for j, it in enumerate(items):
        y = -h / 2 + 175 + j * 92
        good = it.get('good', True)
        mark = (f'<circle cx="{x + w / 2 - 50}" cy="{y}" r="22" fill="{kits.B["green" if good else "red"]}"/>'
                + (f'<path d="M {x + w / 2 - 61} {y} l 8 9 l 15 -18" stroke="#fff" stroke-width="6" fill="none" stroke-linecap="round"/>'
                   if good else
                   f'<path d="M {x + w / 2 - 59} {y - 9} l 18 18 M {x + w / 2 - 41} {y - 9} l -18 18" stroke="#fff" stroke-width="6" stroke-linecap="round"/>'))
        out += (f'<g {t0(times, k0 + 1 + j, 0.3)}>' + mark +
                text(it.get('text', ''), 38, kits.B['ink'], 800, anchor='start', x=x + w / 2 - 90, y=y) + '</g>')
    if winner_side is not None:
        if winner_side:
            out += (f'<g class="tl" data-t0="{t_win:.3f}" data-d="0.3"><rect x="{x - w / 2 - 10}" y="{-h / 2 - 10}" width="{w + 20}" '
                    f'height="{h + 20}" rx="34" fill="none" stroke="{kits.B["green"]}" stroke-width="12"/>'
                    + kits.b_pill({'text': side.get('winner_label', 'الأفضل'), 'color': 'green', 'size': 40})
                    .replace('<g', f'<g transform="translate({x},{h / 2 + 10})"', 1) + '</g>')
    return out


def versus(el, times):
    a, b = el.get('a', {}), el.get('b', {})
    W, h = el.get('w', 980), el.get('h', 640)
    ratio = el.get('ratio', 0.5)
    gap = 36
    wa, wb = (W - gap) * ratio, (W - gap) * (1 - ratio)
    xa, xb = W / 2 - wa / 2, -W / 2 + wb / 2                      # a on the right (read first)
    na = len(a.get('items', []))
    kb = 2 + na
    tw = times[-1]
    win = el.get('winner')
    out = ''
    dim_a = f'class="dim" data-t0="{tw:.3f}"' if win == 'b' else ''
    dim_b = f'class="dim" data-t0="{tw:.3f}"' if win == 'a' else ''
    out += f'<g {dim_a}>' + panel(a, xa, wa, h, times, 0, col(a.get('color', 'blue')), (win == 'a') if win else None, tw) + '</g>'
    out += f'<g {dim_b}>' + panel(b, xb, wb, h, times, kb - 1, col(b.get('color', 'red')), (win == 'b') if win else None, tw) + '</g>'
    sx = W / 2 - wa - gap / 2
    out += stroke(f'M {sx} {-h / 2 - 30} L {sx} {h / 2 + 30}', kits.B['ink'], 6, times[kb - 1], 0.5, 'stroke-dasharray="0"')
    out += (f'<g {t0(times, kb - 1, 0.3)}><circle cx="{sx}" cy="0" r="46" fill="{kits.B["yellow"]}" stroke="{kits.B["ink"]}" stroke-width="6"/>'
            + text('VS', 38, kits.B['ink'], 900, x=sx, y=2) + '</g>')
    return out


def scorecard(el, times):
    res, _ = check(el)
    rows = el.get('rows', [])
    w = el.get('w', 940)
    heads = el.get('heads', {'a': 'A', 'b': 'B'})
    rh = 96
    xa, xb = -w / 2 + 290, -w / 2 + 110
    out = (text(heads.get('a', 'A'), 42, kits.B['blue'], 900, x=xa, y=-rh) + text(heads.get('b', 'B'), 42, kits.B['red'], 900, x=xb, y=-rh))
    out = f'<g class="tl" data-t0="{times[0]:.3f}" data-d="0.3">{out}</g>'
    for i, r in enumerate(rows):
        y = i * rh
        better_a = (r['a'] < r['b']) if el.get('lower_is_better') else (r['a'] > r['b'])
        out += (f'<g {t0(times, i, 0.3)}><line x1="{-w / 2}" y1="{y + rh / 2}" x2="{w / 2}" y2="{y + rh / 2}" stroke="{kits.B["grey"]}" stroke-width="2"/>'
                + text(r.get('label', ''), 40, kits.B['ink'], 800, anchor='start', x=w / 2 - 10, y=y)
                + text(fmt_num(r['a']) + r.get('unit', ''), 44, kits.B['green'] if better_a and r['a'] != r['b'] else kits.B['ink'], 900, x=xa, y=y)
                + text(fmt_num(r['b']) + r.get('unit', ''), 44, kits.B['green'] if not better_a and r['a'] != r['b'] else kits.B['ink'], 900, x=xb, y=y)
                + '</g>')
    if res and res['winner']:
        wx = xa if res['winner'] == 'a' else xb
        y = len(rows) * rh + 20
        out += (f'<g {t0(times, len(rows), 0.4)}>' + text(fmt_num(res['a']), 52, kits.B['ink'], 900, x=xa, y=y)
                + text(fmt_num(res['b']), 52, kits.B['ink'], 900, x=xb, y=y)
                + text(el.get('total_label', 'المجموع'), 42, kits.B['ink'], 900, anchor='start', x=w / 2 - 10, y=y)
                + stroke(rough_ellipse(80, 50, 'sc' + str(wx)), kits.B['green'], 7, times[len(rows)], 0.6).replace('d="M', f'transform="translate({wx},{y})" d="M', 1)
                + '</g>')
    return out


def beforeafter(el, times):
    res, _ = check(el)
    if not res:
        return ''
    b, a = el['before'], el['after']
    unit = el.get('unit', '')
    out = ''
    for k, (side, x, tone) in enumerate(((b, 250, 'neutral'), (a, -250, 'positive' if res['good'] else 'negative'))):
        out += f'<g {t0(times, k, 0.4)}>' + kits.b_statcard({'label': side.get('label', ''), 'value': side['value'], 'unit': unit,
                                                              'tone': tone, 'count': False, 'size': el.get('size', 76)}) \
            .replace('<g', f'<g transform="translate({x},0)"', 1) + '</g>'
    d1, d2 = arrow_path(110, 0, -110, 0, 0.0)
    out += stroke(d1, kits.B['ink'], 8, times[1], 0.4) + stroke(d2, kits.B['ink'], 8, times[1] + 0.3, 0.2)
    ch = res['change']
    sign = '+' if ch > 0 else ('−' if ch < 0 else '')
    out += (f'<g {t0(times, 2, 0.4)}>' + kits.b_pill({'text': iso(f'{sign}{abs(ch):.0f}%'), 'color': 'green' if res['good'] else 'red', 'size': 48})
            .replace('<g', '<g transform="translate(0,180)"', 1) + '</g>')
    return out


def circle_mark(el, times):
    rx, ry = el.get('rx', 160), el.get('ry', 70)
    return stroke(rough_ellipse(rx, ry, el.get('seed', f'{rx}{ry}')), col(el.get('color', 'red')), el.get('width', 8), times[0], el.get('dur', 0.6))


def underline(el, times):
    w = el.get('w', 400)
    r = _rng(el.get('seed', w))
    n = 6
    d = f'M {w / 2:.1f} {next(r) * 6:.1f}'
    for i in range(1, n + 1):
        x = w / 2 - w * i / n
        d += f' Q {x + w / n / 2:.1f} {next(r) * 14 + (8 if i % 2 else -8):.1f} {x:.1f} {next(r) * 6:.1f}'
    return stroke(d, col(el.get('color', 'red')), el.get('width', 9), times[0], el.get('dur', 0.5))


def hand_arrow(el, times):
    bend = max(-1.0, min(1.0, float(el.get('bend', 0.25))))      # a fraction of the arrow length
    d1, d2 = arrow_path(0, 0, el.get('dx', -200), el.get('dy', 120), bend)
    c = col(el.get('color', 'ink'))
    return stroke(d1, c, el.get('width', 8), times[0], 0.5) + stroke(d2, c, el.get('width', 8), times[0] + 0.45, 0.2)


def flow(el, times):
    nodes = el.get('nodes', [])
    direction = el.get('direction', 'down')
    bw, bh, gap = el.get('box_w', 520), el.get('box_h', 110), el.get('gap', 80)
    out = ''
    pos = []
    for i in range(len(nodes)):
        if direction == 'down':
            pos.append((0, i * (bh + gap)))
        else:                                                     # rtl: first node on the right
            pos.append((-(i * (bw + gap)) + (len(nodes) - 1) * (bw + gap) / 2, 0))
    for i, (nd, (x, y)) in enumerate(zip(nodes, pos)):
        c = col(nd.get('color', 'ink'))
        out += stroke(rough_rect(bw, bh, el.get('seed', 'flow') + str(i)), c, 7, times[i], 0.6, f'transform="translate({x},{y})"')
        out += f'<g {t0(times, i, 0.3)} data-dl="0.4">' + text(nd.get('label', ''), el.get('size', 44), kits.B['ink'], 900, x=x, y=y) + '</g>'
        if i:
            px, py = pos[i - 1]
            if direction == 'down':
                d1, d2 = arrow_path(px, py + bh / 2 + 8, x, y - bh / 2 - 8, 0.2)
            else:
                d1, d2 = arrow_path(px - bw / 2 - 8, py, x + bw / 2 + 8, y, 0.2)
            out += stroke(d1, kits.B['ink'], 6, times[i] - 0.05, 0.35) + stroke(d2, kits.B['ink'], 6, times[i] + 0.25, 0.15)
    return out


def numbered(el, times):
    steps = el.get('steps', [])
    gap, size = el.get('gap', 130), el.get('size', 46)
    w = el.get('w', 860)
    out = ''
    for i, st in enumerate(steps):
        y = i * gap
        cx = w / 2 - 50
        out += stroke(rough_ellipse(42, 40, f'n{i}', 1.08), col(el.get('color', 'red')), 6, times[i], 0.45, f'transform="translate({cx},{y})"')
        out += f'<g {t0(times, i, 0.3)}>' + text(str(i + 1), 46, kits.B['ink'], 900, x=cx, y=y + 2) \
            + text(st.get('text', ''), size, kits.B['ink'], 800, anchor='start', x=cx - 70, y=y) + '</g>'
    return out


def build(el, times):
    return {'kinetic': kinetic, 'versus': versus, 'scorecard': scorecard, 'beforeafter': beforeafter,
            'circle_mark': circle_mark, 'underline': underline, 'hand_arrow': hand_arrow, 'flow': flow,
            'numbered': numbered}[el['type']](el, times)
