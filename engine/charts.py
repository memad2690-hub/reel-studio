"""Data-storytelling components (Mode B): bars, waterfall, donut, line, funnel, breakeven.

Every chart is drawn around (0,0) in the graphics region. Per-item animation times come from build.py
(`times`, one per bar/segment/stage/point); the runtime animates classes:
  .grow  (scale from 0, data-o = transform origin)     .draw (stroke draws on)
  .arc   (donut segment sweeps)                         .tl   (fades in at data-t0)
check(el) returns (computed, problems): build turns problems into finance errors that block render.
"""
import math

import kits
from kits import esc, fmt_num, text

TYPES = ('bars', 'waterfall', 'donut', 'line', 'funnel', 'breakeven')
TONES = {'positive': 'green', 'negative': 'red', 'neutral': 'ink', 'blue': 'blue', 'grey': 'grey', 'yellow': 'yellow'}


def C(tone):
    return kits.B[TONES.get(tone, tone if tone in kits.B else 'ink')]


def short(v, unit=''):
    a = abs(v)
    s = f'{a / 1e6:.1f}'.rstrip('0').rstrip('.') + 'M' if a >= 1e6 else \
        f'{a / 1e3:.1f}'.rstrip('0').rstrip('.') + 'K' if a >= 1e4 else fmt_num(a)
    return s + (f' {unit}' if unit else '')


def t0(times, i, d=0.6, cls='tl', extra=''):
    return f'class="{cls}" data-t0="{times[i]:.3f}" data-d="{d}" {extra}'


ISO = lambda s: '\u2066' + s + '\u2069'  # noqa: E731  left-to-right isolate: '20%' never flips to '%20' in Arabic text


def pct(v):
    return ISO(f'{v:.0f}%' if abs(v - round(v)) < 0.05 else f'{v:.1f}%')


def label_lines(s, size, y, color=None, maxc=11, x=0):
    """Axis label, split onto two lines when long (never splits inside a word)."""
    words = s.split()
    c = color or kits.B['ink']
    if len(s) <= maxc or len(words) < 2:
        return text(s, size, c, 800, x=x, y=y)
    mid = max(1, len(words) // 2)
    return (text(' '.join(words[:mid]), size, c, 800, x=x, y=y) +
            text(' '.join(words[mid:]), size, c, 800, x=x, y=y + kits.readable(size) * 1.15))


def item_count(el):
    t = el['type']
    if t == 'bars':
        return len(el.get('items', []))
    if t == 'waterfall':
        return len(el.get('rows', [])) + 1
    if t == 'donut':
        return len(el.get('segments', []))
    if t == 'line':
        return len(el.get('points', []))
    if t == 'funnel':
        return len(el.get('stages', []))
    return 3 if t == 'breakeven' else 1


def item_specs(el):
    """The sub-items that carry their own `in` anchors, in order."""
    t = el['type']
    key = {'bars': 'items', 'waterfall': 'rows', 'donut': 'segments', 'line': 'points', 'funnel': 'stages'}.get(t)
    items = list(el.get(key, [])) if key else [el]
    if t == 'breakeven':
        items = [el, {'in': el.get('in_be')}, {'in': el.get('in_actual')}]
    if t == 'waterfall':
        items.append(el.get('result', {}))
    return items


# ------------------------------------------------------------------ checks
def check(el):
    t = el['type']
    p = []
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)  # noqa: E731
    if t == 'bars':
        for i, it in enumerate(el.get('items', [])):
            if not num(it.get('value')):
                p.append(f'bar {i + 1} ({it.get("label", "")!r}) has no numeric value')
        return None, p
    if t == 'waterfall':
        rows = el.get('rows', [])
        total = 0.0
        for i, r in enumerate(rows):
            if not num(r.get('value')):
                p.append(f'row {i + 1} ({r.get("label", "")!r}) has no numeric value'); continue
            op = r.get('op', '=' if i == 0 else '-')
            if i and op not in ('+', '-'):
                p.append(f'row {i + 1}: op must be "+" or "-"')
            total = r['value'] if i == 0 else total + (r['value'] if op == '+' else -r['value'])
        res = el.get('result', {})
        if 'value' in res and abs(res['value'] - total) > 1e-6:
            p.append(f'result says {res["value"]:,} but the rows add up to {total:,}')
        return total, p
    if t == 'donut':
        segs = el.get('segments', [])
        vals = [s.get('value') for s in segs]
        if not segs or not all(num(v) and v >= 0 for v in vals):
            p.append('every donut segment needs a value >= 0'); return None, p
        tot = sum(vals)
        if 'total' in el and abs(el['total'] - tot) > 1e-6:
            p.append(f'segments add up to {tot:,}, not the stated total {el["total"]:,}')
        if tot <= 0:
            p.append('donut total is 0')
        return tot, p
    if t == 'line':
        for i, pt in enumerate(el.get('points', [])):
            if not num(pt.get('value')):
                p.append(f'point {i + 1} has no numeric value')
        return None, p
    if t == 'funnel':
        st = el.get('stages', [])
        rates = []
        for i, s in enumerate(st):
            if not num(s.get('value')) or s['value'] < 0:
                p.append(f'stage {i + 1} ({s.get("label", "")!r}) needs a value >= 0'); return None, p
            if i:
                prev = st[i - 1]['value']
                if s['value'] > prev:
                    p.append(f'stage {i + 1} ({s["value"]:,}) is larger than the stage before it ({prev:,})')
                r = s['value'] / prev * 100 if prev else 0
                rates.append(r)
                if 'rate' in s and abs(s['rate'] - r) > 0.5:
                    p.append(f'stage {i + 1} says {s["rate"]}% but {s["value"]:,}/{prev:,} = {r:.1f}%')
        return rates, p
    if t == 'breakeven':
        if num(el.get('margin_pct')):
            m = el['margin_pct'] / 100
        elif num(el.get('revenue')) and num(el.get('variable_costs')) and el['revenue'] > 0:
            m = (el['revenue'] - el['variable_costs']) / el['revenue']
        else:
            p.append('breakeven needs margin_pct, or revenue + variable_costs'); return None, p
        if m <= 0:
            p.append(f'contribution margin is {m * 100:.1f}%: there is no break-even ROAS (every sale loses money)')
            return None, p
        be = 1 / m
        if num(el.get('expect')) and abs(el['expect'] - be) > 0.01:
            p.append(f'expected break-even ROAS {el["expect"]} but 1 / {m * 100:.1f}% = {be:.2f}')
        return {'margin': m, 'be': be}, p
    return None, p


# ------------------------------------------------------------------ builders
def bars(el, times):
    items = el.get('items', [])
    n = max(1, len(items))
    w, h = el.get('w', 880), el.get('h', 460)
    unit = el.get('unit', '')
    ref = el.get('ref')
    top = max([abs(it.get('value', 0)) for it in items] + [ref['value'] if ref else 0]) * 1.12 or 1
    slot = w / n
    bw = min(150, slot * 0.58)
    base = h / 2
    out = f'<line x1="{-w / 2}" y1="{base}" x2="{w / 2}" y2="{base}" stroke="{kits.B["ink"]}" stroke-width="6" stroke-linecap="round"/>'
    for i, it in enumerate(items):
        cx = w / 2 - slot * (i + 0.5)                      # RTL: first item on the right
        bh = abs(it['value']) / top * h
        col = C(it.get('tone', 'blue'))
        out += (f'<g {t0(times, i, 0.7, "grow", "data-o=\'50% 100%\'")}>'
                f'<rect x="{cx - bw / 2}" y="{base - bh}" width="{bw}" height="{bh}" rx="14" fill="{col}" '
                f'stroke="{kits.B["ink"]}" stroke-width="5"/></g>')
        out += f'<g {t0(times, i, 0.4)} data-dl="0.45">' + text(short(it['value'], unit), 44, col, 900, x=cx, y=base - bh - 36) + '</g>'
        out += f'<g {t0(times, i, 0.3)}>' + label_lines(it.get('label', ''), 34, base + 48, x=cx) + '</g>'
    if ref:
        ry = base - ref['value'] / top * h
        out += (f'<g {t0([ref.get("_t", times[-1] if times else 0)], 0, 0.3)}>'
                f'<line class="draw" data-t0="{ref.get("_t", times[-1] if times else 0):.3f}" data-d="0.6" x1="{w / 2}" y1="{ry}" '
                f'x2="{-w / 2}" y2="{ry}" stroke="{C(ref.get("tone", "red"))}" stroke-width="6" stroke-dasharray="18 12"/>'
                + text(f'{ref.get("label", "")} {short(ref["value"], unit)}'.strip(), 32, C(ref.get('tone', 'red')), 900,
                       anchor='start', x=w / 2 - 6, y=ry - 30) + '</g>')
    return out


def waterfall(el, times):
    rows = el.get('rows', [])
    res = el.get('result', {})
    unit = el.get('unit', 'ج')
    w, h = el.get('w', 920), el.get('h', 480)
    run, spans = 0.0, []
    for i, r in enumerate(rows):
        v = r['value']
        if i == 0:
            spans.append((0, v, r.get('tone', 'positive'))); run = v
        else:
            new = run + v if r.get('op', '-') == '+' else run - v
            spans.append((run, new, r.get('tone', 'positive' if r.get('op') == '+' else 'negative'))); run = new
    total = run
    spans.append((0, total, 'negative' if total < 0 else 'positive'))
    labels = [r.get('label', '') for r in rows] + [res.get('label_negative' if total < 0 else 'label', 'الصافي')]
    hi = max(max(a, b) for a, b, _ in spans)
    lo = min(0, min(min(a, b) for a, b, _ in spans))
    rng = (hi - lo) * 1.1 or 1
    base = h / 2 - (0 - lo) / rng * h                      # y of the zero line
    ys = lambda v: base - v / rng * h                       # noqa: E731
    n = len(spans)
    slot = w / n
    bw = min(140, slot * 0.6)
    out = f'<line x1="{-w / 2}" y1="{base}" x2="{w / 2}" y2="{base}" stroke="{kits.B["ink"]}" stroke-width="6" stroke-linecap="round"/>'
    for i, (a, b, tone) in enumerate(spans):
        cx = w / 2 - slot * (i + 0.5)
        y1, y2 = ys(max(a, b)), ys(min(a, b))
        col = C(tone)
        down = b < a
        origin = '50% 0%' if down else '50% 100%'
        out += (f'<g {t0(times, i, 0.6, "grow", f"data-o={chr(39)}{origin}{chr(39)}")}>'
                f'<rect x="{cx - bw / 2}" y="{y1}" width="{bw}" height="{max(2, y2 - y1)}" rx="10" fill="{col}" '
                f'stroke="{kits.B["ink"]}" stroke-width="5"/></g>')
        if 0 < i < n - 1:                                  # connector from the previous bar's end
            out += (f'<g {t0(times, i, 0.3)}><line x1="{cx + slot - bw / 2}" y1="{ys(a)}" x2="{cx + bw / 2}" y2="{ys(a)}" '
                    f'stroke="{kits.B["ink"]}" stroke-width="3" stroke-dasharray="8 8"/></g>')
        amount = abs(b - a) if 0 < i < n - 1 else abs(b)
        vy = (y2 + 40) if (down or (i == n - 1 and b < 0)) else (y1 - 34)
        out += f'<g {t0(times, i, 0.3)}>' + text(short(amount, unit), 36, col, 900, x=cx, y=vy) + '</g>'
        ly = max(base, h / 2) + 46
        if vy > base and vy + 50 > ly:                      # value hangs below a falling/negative bar: label goes under it
            ly = vy + 56
        out += f'<g {t0(times, i, 0.3)}>' + label_lines(labels[i], 30, ly, x=cx) + '</g>'
    return out


def donut(el, times):
    segs = el.get('segments', [])
    tot = sum(s['value'] for s in segs) or 1
    r, th = el.get('r', 170), el.get('thickness', 64)
    circ = 2 * math.pi * r
    cx = el.get('cx', 220)                                 # donut on the right, legend on the left (RTL)
    out = f'<circle cx="{cx}" cy="0" r="{r}" fill="none" stroke="{kits.B["paper"]}" stroke-width="{th + 10}"/>'
    acc = 0.0
    legend_x = cx - r - 70
    for i, s in enumerate(segs):
        ln = s['value'] / tot * circ
        out += (f'<circle class="arc" data-t0="{times[i]:.3f}" data-d="0.7" data-len="{ln:.2f}" data-circ="{circ:.2f}" '
                f'cx="{cx}" cy="0" r="{r}" fill="none" stroke="{C(s.get("tone", "blue"))}" stroke-width="{th}" '
                f'stroke-dasharray="0 {circ:.2f}" stroke-dashoffset="{-acc:.2f}" transform="rotate(-90 {cx} 0)"/>')
        acc += ln
        pct_s = pct(s['value'] / tot * 100)
        ly = -len(segs) * 50 + 50 + i * 100
        out += (f'<g {t0(times, i, 0.3)}><rect x="{legend_x - 34}" y="{ly - 17}" width="34" height="34" rx="8" '
                f'fill="{C(s.get("tone", "blue"))}" stroke="{kits.B["ink"]}" stroke-width="4"/>'
                + text(f'{s.get("label", "")} {pct_s}', 38, kits.B['ink'], 800, anchor='start', x=legend_x - 50, y=ly)
                + '</g>')
    if el.get('center'):
        out += f'<g {t0(times, len(segs) - 1, 0.3)}>' + text(el['center'], 44, kits.B['ink'], 900, x=cx) + '</g>'
    return out


def line(el, times):
    pts = el.get('points', [])
    n = len(pts)
    w, h = el.get('w', 860), el.get('h', 420)
    unit = el.get('unit', '')
    vals = [p['value'] for p in pts]
    lo, hi = min(vals + [0]), max(vals) or 1
    rng = (hi - lo) * 1.15 or 1
    xs = [w / 2 - (w / max(1, n - 1)) * i if n > 1 else 0 for i in range(n)]      # RTL: first point on the right
    ys = [h / 2 - (v - lo) / rng * h for v in vals]
    d = 'M ' + ' L '.join(f'{x:.1f} {y:.1f}' for x, y in zip(xs, ys))
    col = C(el.get('tone', 'blue'))
    dur = max(0.6, (times[-1] - times[0]) + 0.4) if times else 1
    out = f'<line x1="{-w / 2}" y1="{h / 2}" x2="{w / 2}" y2="{h / 2}" stroke="{kits.B["ink"]}" stroke-width="5"/>'
    out += (f'<path class="draw" data-t0="{times[0] if times else 0:.3f}" data-d="{dur:.2f}" d="{d}" fill="none" '
            f'stroke="{col}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>')
    for i, (x, y, p) in enumerate(zip(xs, ys, pts)):
        out += (f'<g {t0(times, i, 0.3)}><circle cx="{x}" cy="{y}" r="14" fill="#fff" stroke="{col}" stroke-width="7"/>'
                + text(short(p['value'], unit), 32, kits.B['ink'], 900, x=x, y=y - 42)
                + text(p.get('label', ''), 28, kits.B['ink'], 800, x=x, y=h / 2 + 40) + '</g>')
    return out


def funnel(el, times):
    st = el.get('stages', [])
    rates, _ = check(el)
    rates = rates or []
    w, sh, gap = el.get('w', 860), el.get('stage_h', 96), el.get('gap', 58)
    out = ''
    y = -((sh + gap) * len(st) - gap) / 2
    for i, s in enumerate(st):
        # stepped widths (not proportional): every stage stays wide enough for its label; numbers carry the scale
        step = 0.6 / max(1, len(st) - 1) if len(st) > 1 else 0
        ww = (1 - step * i) * w
        nw = (1 - step * (i + 1)) * w if i + 1 < len(st) else ww * 0.92
        col = C(s.get('tone', ['blue', 'blue', 'green', 'green', 'green'][min(i, 4)]))
        pts = f'{-ww / 2},{y} {ww / 2},{y} {nw / 2},{y + sh} {-nw / 2},{y + sh}'
        out += (f'<g {t0(times, i, 0.5, "grow", "data-o=\'50% 0%\'")}><polygon points="{pts}" fill="{col}" '
                f'stroke="{kits.B["ink"]}" stroke-width="5" stroke-linejoin="round"/></g>')
        out += (f'<g {t0(times, i, 0.3)}>' + text(f'{s.get("label", "")}  {fmt_num(s["value"])}', 38, '#fff', 900, y=y + sh / 2)
                + '</g>')
        if i and i - 1 < len(rates):
            out += (f'<g {t0(times, i, 0.3)}>' + kits.b_pill({'text': pct(rates[i - 1]), 'color': 'ink', 'size': 32})
                    .replace('<g', f'<g transform="translate({-w / 2 - 10},{y - gap / 2})"', 1) + '</g>')
        y += sh + gap
    return out


def breakeven(el, times):
    r, _ = check(el)
    if not r:
        return ''
    m, be = r['margin'], r['be']
    be_s = f'{be:.2f}'.rstrip('0').rstrip('.')
    formula = f'1 ÷ {m * 100:.0f}% = {be_s}'
    if 'revenue' in el and 'variable_costs' in el:
        formula = f'{fmt_num(el["revenue"])} ÷ {fmt_num(el["revenue"] - el["variable_costs"])} = {be_s}'
    out = (f'<g {t0(times, 0, 0.3)}>' + text(f'هامش المساهمة {pct(m * 100)}', 44, kits.B['ink'], 800, y=-150) + '</g>'
           f'<g {t0(times, 1, 0.3)}><text x="0" y="-60" font-size="52" font-weight="900" fill="{kits.B["ink"]}" '
           f'text-anchor="middle" dominant-baseline="central" direction="ltr" style="unicode-bidi:isolate">{esc(formula)}</text></g>'
           f'<g {t0(times, 1, 0.4)} data-dl="0.3">' + kits.b_statcard({'label': 'Break-even ROAS', 'value': float(be_s), 'unit': '',
                                                                     'count': False, 'size': 140 if kits.LOOK[0] >= 2 else 84})
           .replace('<g', f'<g transform="translate(0,{140 if kits.LOOK[0] >= 2 else 90})"', 1)
           + '</g>')
    if 'actual' in el:
        win = el['actual'] >= be
        txt = el.get('verdict_win', 'فوق الـ break-even: كسبان') if win else el.get('verdict_lose', 'تحت الـ break-even: خسران')
        out += (f'<g {t0(times, 2, 0.3)}>' + kits.b_pill({'text': f'ROAS {fmt_num(el["actual"])} — {txt}',
                                                                        'color': 'green' if win else 'red', 'size': 40})
                .replace('<g', f'<g transform="translate(0,{400 if kits.LOOK[0] >= 2 else 300})"', 1) + '</g>')
    return out


def build(el, times):
    return {'bars': bars, 'waterfall': waterfall, 'donut': donut, 'line': line, 'funnel': funnel,
            'breakeven': breakeven}[el['type']](el, times)
