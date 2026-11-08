"""SVG element kits.

Every builder takes the element dict from scenes.json and returns SVG markup drawn
around a local origin (0,0). The page builder wraps it in a positioned group and an
animation group. Mode A (cut-out) coordinates are 720x1280; Mode B (doodle) are
1080 wide inside the graphics half.

RTL note: text uses direction:rtl. text-anchor="start" is the RIGHT edge.
"""
import html
import math
import random

INK = '#1b1b1b'
A = {'ink': '#1b1b1b', 'navy': '#2c4a7c', 'teal': '#3f7a72', 'mustard': '#c99a2e',
     'red': '#b8322a', 'cream': '#f3efe4', 'olive': '#5b6b3a', 'white': '#ffffff', 'grey': '#8a857a'}
B = {'ink': '#222222', 'red': '#d64541', 'blue': '#2f5d8a', 'yellow': '#f2cf4a', 'paper': '#f4eddd',
     'white': '#ffffff', 'green': '#3f8a5a', 'grey': '#8d8676'}
_DEFAULTS = {'A': dict(A), 'B': dict(B)}


def reset_palettes():
    """Brand presets mutate B in place (builders read it at call time); reset before every build."""
    A.clear(); A.update(_DEFAULTS['A'])
    B.clear(); B.update(_DEFAULTS['B'])


def fmt_num(v):
    v = float(v)
    return f'{v:,.0f}' if abs(v - round(v)) < 1e-9 else f'{v:,.2f}'


TONES = {'positive': 'green', 'negative': 'red', 'neutral': 'ink'}


def esc(s):
    return html.escape(str(s), quote=True)


def col(c, pal):
    return pal.get(c, c) if c else None


def text(s, size=40, color=INK, weight=800, anchor='middle', y=0, x=0, extra=''):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" '
            f'text-anchor="{anchor}" dominant-baseline="central" direction="rtl" {extra}>{esc(s)}</text>')


# ---------------------------------------------------------------- Mode A: cut-out

def torn_path(w, h, seed=1, jag=7):
    rnd = random.Random(seed)
    pts, x = [], -w / 2
    while x < w / 2:
        pts.append((x, -h / 2 + rnd.uniform(-jag, jag))); x += rnd.uniform(10, 22)
    pts.append((w / 2, -h / 2))
    y = -h / 2
    while y < h / 2:
        pts.append((w / 2 + rnd.uniform(-jag / 2, jag / 2), y)); y += rnd.uniform(14, 26)
    x = w / 2
    while x > -w / 2:
        pts.append((x, h / 2 + rnd.uniform(-jag, jag))); x -= rnd.uniform(10, 22)
    y = h / 2
    while y > -h / 2:
        pts.append((-w / 2 + rnd.uniform(-jag / 2, jag / 2), y)); y -= rnd.uniform(14, 26)
    return 'M' + ' L'.join(f'{px:.1f},{py:.1f}' for px, py in pts) + ' Z'


def a_torn(e):
    w, h = e.get('w', 560), e.get('h', 130)
    fill = col(e.get('color', 'cream'), A)
    tc = col(e.get('text_color', 'ink'), A)
    out = (f'<path d="{torn_path(w, h, e.get("seed", 3))}" fill="rgba(0,0,0,.18)" transform="translate(6,8)"/>'
           f'<path d="{torn_path(w, h, e.get("seed", 3))}" fill="{fill}"/>')
    if e.get('text'):
        out += text(e['text'], e.get('size', 52), tc, 900)
    return out


def a_label(e):
    fill = col(e.get('color', 'cream'), A)
    tc = col(e.get('text_color', 'ink'), A)
    pad = e.get('pad', 22)
    return (f'<g data-fit="{pad}">'
            f'<rect class="fitbox" rx="6" fill="rgba(0,0,0,.18)" transform="translate(5,7)"/>'
            f'<rect class="fitbox" rx="6" fill="{fill}" stroke="rgba(0,0,0,.08)"/>'
            f'<rect class="tapeL" width="54" height="22" fill="rgba(240,226,170,.85)" transform="rotate(-8)"/>'
            f'<rect class="tapeR" width="54" height="22" fill="rgba(240,226,170,.85)" transform="rotate(7)"/>'
            + text(e.get('text', ''), e.get('size', 38), tc, 800) + '</g>')


def a_person(e):
    c = col(e.get('color', 'navy'), A)
    s = e.get('h', 260) / 260
    return (f'<g transform="scale({s})">'
            f'<ellipse cx="0" cy="128" rx="78" ry="10" fill="rgba(0,0,0,.15)"/>'
            f'<circle cx="0" cy="-92" r="38" fill="{c}"/>'
            f'<path d="M-70,128 L-70,10 Q-70,-44 -20,-48 L20,-48 Q70,-44 70,10 L70,128 Z" fill="{c}"/>'
            '</g>')


def a_chair(e):
    c = col(e.get('color', 'mustard'), A)
    return (f'<path d="M-50,-90 h100 v80 h-100z" fill="{c}"/><path d="M-60,-10 h120 v22 h-120z" fill="{c}"/>'
            f'<path d="M-52,12 v70 M52,12 v70" stroke="{c}" stroke-width="12"/>')


def a_building(e):
    c = col(e.get('color', 'navy'), A)
    floors = e.get('floors', 5)
    h = floors * 46 + 30
    out = f'<rect x="-90" y="{-h}" width="180" height="{h}" fill="{c}"/>'
    out += f'<path d="M-104,{-h} L0,{-h - 60} L104,{-h} Z" fill="{c}"/>'
    for f in range(floors):
        for k in (-55, 0, 55):
            out += f'<rect x="{k - 16}" y="{-h + 30 + f * 46}" width="32" height="26" fill="{A["cream"]}" opacity=".85"/>'
    return out


def a_money(e):
    n = e.get('stacks', 3)
    out = ''
    for i in range(n):
        x = (i - (n - 1) / 2) * 92
        for j in range(e.get('height', 4)):
            y = -j * 18
            out += (f'<rect x="{x - 40}" y="{y - 14}" width="80" height="16" rx="3" fill="{A["olive"]}" stroke="#2f3a1e" stroke-width="2"/>'
                    f'<circle cx="{x}" cy="{y - 6}" r="5" fill="#d9e2b8"/>')
    return out


def a_ballot(e):
    c = col(e.get('color', 'navy'), A)
    return (f'<rect x="-80" y="-60" width="160" height="130" rx="6" fill="{c}"/>'
            f'<rect x="-40" y="-66" width="80" height="12" fill="{INK}"/>'
            f'<rect x="-30" y="-120" width="60" height="70" fill="{A["cream"]}" transform="rotate(-6)"/>')


def a_siren(e):
    return (f'<path d="M-50,40 L-40,-20 Q0,-70 40,-20 L50,40 Z" fill="{A["red"]}"/>'
            f'<rect x="-64" y="40" width="128" height="22" rx="4" fill="{INK}"/>'
            f'<path d="M-90,-50 l-24,-14 M90,-50 l24,-14 M0,-90 v-26" stroke="{A["red"]}" stroke-width="8" stroke-linecap="round"/>')


def a_calendar(e):
    return (f'<rect x="-90" y="-90" width="180" height="180" rx="12" fill="{A["cream"]}" stroke="{INK}" stroke-width="5"/>'
            f'<rect x="-90" y="-90" width="180" height="50" rx="10" fill="{A["red"]}"/>'
            + text(e.get('top', ''), 28, '#fff', 800, y=-65) + text(e.get('text', ''), e.get('size', 64), INK, 900, y=22))


def x_mark(e, pal):
    c = col(e.get('color', 'red'), pal); s = e.get('size', 80)
    return f'<path d="M{-s},{-s} L{s},{s} M{s},{-s} L{-s},{s}" stroke="{c}" stroke-width="{s / 4}" stroke-linecap="round"/>'


def check(e, pal):
    c = col(e.get('color', 'teal' if pal is A else 'green'), pal); s = e.get('size', 80)
    return f'<path d="M{-s},0 L{-s / 3},{s * .7} L{s},{-s * .7}" fill="none" stroke="{c}" stroke-width="{s / 4}" stroke-linecap="round" stroke-linejoin="round"/>'


def a_card(e):
    w, h = e.get('w', 300), e.get('h', 200)
    acc = col(e.get('accent', 'navy'), A)
    out = (f'<rect x="{-w / 2 + 6}" y="{-h / 2 + 8}" width="{w}" height="{h}" rx="10" fill="rgba(0,0,0,.18)"/>'
           f'<rect x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}" rx="10" fill="{A["cream"]}"/>'
           f'<rect x="{-w / 2}" y="{-h / 2}" width="{w}" height="56" rx="10" fill="{acc}"/>'
           + text(e.get('title', ''), e.get('title_size', 32), '#fff', 900, y=-h / 2 + 28))
    for i, line in enumerate(e.get('lines', [])):
        out += text(line, e.get('size', 30), INK, 700, y=-h / 2 + 96 + i * 44)
    return out


def a_stamp(e):
    c = col(e.get('color', 'red'), A)
    return (f'<g transform="rotate({e.get("rot", -8)})"><rect data-fitpad="1" class="fitbox" rx="8" fill="none" stroke="{c}" stroke-width="7"/>'
            + text(e.get('text', ''), e.get('size', 48), c, 900) + '</g>').replace('<g transform', '<g data-fit="18" transform', 1)


# ---------------------------------------------------------------- Mode B: notebook doodle

def shadowed(shape_attrs, tag='rect'):
    """Hatched offset shadow + white shape with ink stroke."""
    return (f'<{tag} {shape_attrs} fill="url(#hatch)" transform="translate(12,14)"/>'
            f'<{tag} {shape_attrs} fill="#fff" stroke="{B["ink"]}" stroke-width="6"/>')


ICONS = {
    'megaphone': 'M-34,-14 L10,-34 L10,34 L-34,14 Z M-34,-14 v28 M10,-34 q30,34 0,68 M-26,14 l8,26',
    'cart': 'M-42,-30 h14 l12,44 h44 l10,-32 h-60 M-12,30 a6,6 0 1 0 0.1,0 M24,30 a6,6 0 1 0 0.1,0',
    'box': 'M-34,-14 L0,-32 L34,-14 L34,24 L0,40 L-34,24 Z M-34,-14 L0,4 L34,-14 M0,4 V40',
    'truck': 'M-44,-20 h52 v40 h-52 Z M8,-6 h22 l14,14 v12 h-36 M-28,28 a8,8 0 1 0 0.1,0 M26,28 a8,8 0 1 0 0.1,0',
    'return': 'M30,-10 a30,30 0 1 0 -6,30 M30,-34 v24 h-24',
    'receipt': 'M-26,-38 h52 v76 l-9,-7 l-9,7 l-9,-7 l-8,7 l-8,-7 l-9,7 Z M-14,-18 h28 M-14,-2 h28 M-14,14 h18',
    'calculator': 'M-28,-40 h56 v80 h-56 Z M-18,-30 h36 v16 h-36 Z M-16,2 h6 M-2,2 h6 M12,2 h6 M-16,18 h6 M-2,18 h6 M12,18 h6',
    'chart': 'M-38,34 h76 M-38,34 v-70 M-28,20 l18,-18 l14,10 l26,-30 M22,-20 h10 v10',
    'scale': 'M0,-38 v76 M-24,38 h48 M-40,-24 h80 M-40,-24 l-14,30 h28 Z M40,-24 l-14,30 h28 Z',
    'chat': 'M-38,-30 h76 v50 h-44 l-18,16 v-16 h-14 Z M-22,-6 h44',
    'check': 'M-26,0 l16,18 l34,-36',
    'money': 'M-40,-22 h80 v44 h-80 Z M0,0 a12,12 0 1 0 0.1,0 M-30,-12 v24 M30,-12 v24',
    'phone': 'M-20,-40 h40 v80 h-40 Z M-6,30 h12',
    'clock': 'M0,0 m-34,0 a34,34 0 1 0 68,0 a34,34 0 1 0 -68,0 M0,-20 V0 l14,10',
    'warning': 'M0,-38 L40,32 H-40 Z M0,-14 v22 M0,18 v2',
    'users': 'M-16,-16 a12,12 0 1 0 0.1,0 M-40,30 q0,-30 24,-30 q24,0 24,30 M20,-20 a10,10 0 1 0 0.1,0 M14,0 q26,-4 28,28',
}


def b_icon(e):
    r = e.get('r', 74)
    s = r / 74
    stroke = col(e.get('color', 'ink'), B)
    path = ICONS.get(e.get('name', 'check'), ICONS['check'])
    return (shadowed(f'cx="0" cy="0" r="{r}"', 'circle') +
            f'<path d="{path}" transform="scale({s * 1.25})" fill="none" stroke="{stroke}" stroke-width="{6 / s / 1.25:.2f}" '
            'stroke-linecap="round" stroke-linejoin="round"/>')


def b_wcard(e):
    lines = e.get('lines') or [e.get('text', '')]
    size = e.get('size', 48)
    tc = col(e.get('text_color', 'ink'), B)
    inner = ''.join(text(l, size, tc, e.get('weight', 800), y=(i - (len(lines) - 1) / 2) * size * 1.35)
                    for i, l in enumerate(lines))
    return (f'<g data-fit="{e.get("pad", 30)}">'
            f'<rect class="fitbox" rx="26" fill="url(#hatch)" transform="translate(12,14)"/>'
            f'<rect class="fitbox" rx="26" fill="#fff" stroke="{B["ink"]}" stroke-width="6"/>{inner}</g>')


def b_pill(e):
    c = col(e.get('color', 'red'), B)
    return (f'<g data-fit="{e.get("pad", 22)}" data-fitround="1">'
            f'<rect class="fitbox" fill="{c}"/>' + text(e.get('text', ''), e.get('size', 40), '#fff', 900) + '</g>')


def arrow(e, pal):
    c = col(e.get('color', 'ink'), pal)
    dx, dy = e.get('dx', 0), e.get('dy', 120)
    dash = 'stroke-dasharray="18 14"' if e.get('dashed', True) else ''
    ang = math.atan2(dy, dx)
    hx, hy = dx - 26 * math.cos(ang - .5), dy - 26 * math.sin(ang - .5)
    kx, ky = dx - 26 * math.cos(ang + .5), dy - 26 * math.sin(ang + .5)
    return (f'<path d="M0,0 L{dx},{dy}" stroke="{c}" stroke-width="7" stroke-linecap="round" {dash} fill="none"/>'
            f'<path d="M{hx:.1f},{hy:.1f} L{dx},{dy} L{kx:.1f},{ky:.1f}" stroke="{c}" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')


def b_headline(e):
    """Three parts laid out right-to-left by JS (pre | highlight | post) with a yellow highlighter."""
    size = e.get('size', 88)
    parts = ''.join(f'<text class="hp hp{i}" font-size="{size}" font-weight="900" fill="{B["ink"]}" '
                    f'dominant-baseline="central" direction="rtl" text-anchor="start">{esc(e.get(k, ""))}</text>'
                    for i, k in enumerate(('pre', 'hl', 'post')))
    return (f'<g class="headline" data-size="{size}">'
            f'<rect class="hl-rect" fill="{B["yellow"]}" rx="6"/>{parts}</g>')


def b_cta(e):
    kw = e.get('keyword', 'AUDIT')
    out = b_wcard({'lines': [e.get('prompt', 'اكتب في الكومنتات')], 'size': 50})
    out += f'<g transform="translate(0,150)">' + text(kw, e.get('size', 120), B['red'], 900) + '</g>'
    if e.get('magnet'):
        out += f'<g transform="translate(0,290)">' + b_pill({'text': e['magnet'], 'color': 'blue', 'size': 38}) + '</g>'
    return out


def b_statcard(e):
    """Financial stat card: small label on top, big value below, colored by tone (positive green /
    negative red / neutral ink). value is a number; it counts up from count_from (default 0) if count is set.
    Negative amounts are shown as their absolute value with a word label (never a leading minus)."""
    tone = e.get('tone', 'neutral')
    c = col(TONES.get(tone, 'ink'), B)
    size = e.get('size', 76)
    v = e.get('value', 0)
    unit = e.get('unit', 'ج')
    attrs = ''
    if e.get('count', True) and isinstance(v, (int, float)):
        attrs = (f'class="count" data-from="{e.get("count_from", 0)}" data-to="{abs(v)}" data-prefix="" '
                 f'data-suffix="{esc(" " + unit if unit else "")}" data-dur="{e.get("count_dur", 0.9)}"')
    val = (fmt_num(abs(v)) if isinstance(v, (int, float)) else str(v)) + (f' {unit}' if unit else '')
    inner = text(e.get('label', ''), size * 0.48, col('ink', B), 800, y=-size * 0.62)
    inner += text(val, size, c, 900, y=size * 0.32, extra=attrs)
    return (f'<g data-fit="{e.get("pad", 34)}">'
            f'<rect class="fitbox" rx="26" fill="url(#hatch)" transform="translate(12,14)"/>'
            f'<rect class="fitbox" rx="26" fill="#fff" stroke="{B["ink"]}" stroke-width="6"/>{inner}</g>')


def b_chapter(e):
    """Cinematic chapter title: small number, big title, thin rules (minimal editorial typography)."""
    size = e.get('size', 96)
    num = e.get('number', '')
    c = col(e.get('color', 'ink'), B)
    out = ''
    if e.get('backdrop'):
        out += f'<rect x="-600" y="-1100" width="1200" height="2200" fill="#0d0d0d" opacity="{e.get("backdrop_opacity", 0.82)}"/>'
        c = '#f4eddd'
    w = e.get('w', 760)
    out += f'<line x1="{-w / 2}" y1="{-size * 1.05}" x2="{w / 2}" y2="{-size * 1.05}" stroke="{c}" stroke-width="3"/>'
    if num:
        out += text(str(num), size * 0.42, B['red'] if not e.get('backdrop') else '#f2cf4a', 900, y=-size * 0.62)
    out += text(e.get('text', ''), size, c, 800, y=size * 0.12)
    if e.get('sub'):
        out += text(e['sub'], size * 0.36, c, 600, y=size * 0.82)
    out += f'<line x1="{-w / 2}" y1="{size * 1.2}" x2="{w / 2}" y2="{size * 1.2}" stroke="{c}" stroke-width="3"/>'
    return out


def photo_svg(e, href, uid):
    """User photo with a frame: plain | polaroid | archival | tape. Optional slow Ken Burns zoom (kb)."""
    w, h = e.get('w', 640), e.get('h', 480)
    frame = e.get('frame', 'plain')
    kb = e.get('kenburns')
    img = (f'<image href="{esc(href)}" x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice"'
           + (' filter="url(#sepia)"' if frame == 'archival' else '') + '/>')
    if kb:
        img = (f'<g class="kb" data-z="{float(kb if not isinstance(kb, bool) else 1.08):.3f}" data-d="{e.get("kb_dur", 6)}">'
               f'{img}</g>')
    clip = f'<clipPath id="pc{uid}"><rect x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}"/></clipPath>'
    body = f'{clip}<g clip-path="url(#pc{uid})">{img}</g>'
    ink = B['ink']
    if frame == 'polaroid':
        pad, bot = 24, 96
        out = (f'<rect x="{-w / 2 - pad + 12}" y="{-h / 2 - pad + 14}" width="{w + 2 * pad}" height="{h + pad + bot}" fill="rgba(0,0,0,.18)"/>'
               f'<rect x="{-w / 2 - pad}" y="{-h / 2 - pad}" width="{w + 2 * pad}" height="{h + pad + bot}" fill="#fff" stroke="#ddd"/>'
               + body + (text(e['caption'], 40, ink, 700, y=h / 2 + bot / 2) if e.get('caption') else ''))
    elif frame == 'archival':
        pad = 18
        out = (f'<rect x="{-w / 2 - pad}" y="{-h / 2 - pad}" width="{w + 2 * pad}" height="{h + 2 * pad + 50}" fill="#efe3c6" stroke="#b9a27a" stroke-width="3"/>'
               + body + (text(e['caption'], 34, '#5b4a2e', 700, y=h / 2 + 34) if e.get('caption') else ''))
    elif frame == 'tape':
        out = (f'<rect x="{-w / 2 + 10}" y="{-h / 2 + 12}" width="{w}" height="{h}" fill="rgba(0,0,0,.18)"/>' + body +
               f'<rect x="{-w / 2 - 30}" y="{-h / 2 - 22}" width="140" height="44" fill="#f2cf4a" opacity=".75" transform="rotate(-24 {-w / 2 + 40} {-h / 2})"/>'
               f'<rect x="{w / 2 - 110}" y="{-h / 2 - 22}" width="140" height="44" fill="#f2cf4a" opacity=".75" transform="rotate(22 {w / 2 - 40} {-h / 2})"/>')
    else:
        out = body + f'<rect x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}" fill="none" stroke="{ink}" stroke-width="6"/>'
    return out


def eq_row(r, i, size, w, mode):
    """One equation row: label (right, RTL) ... value (left), operator in its own circle at the far left."""
    pal = B if mode == 'B' else A
    tone = r.get('tone', 'positive' if i == 0 else 'negative')
    c = col(TONES.get(tone, 'ink'), pal)
    out = text(r.get('label', ''), size * 0.82, col('ink', pal), 800, anchor='start', x=w / 2 - 10)
    out += text(fmt_num(r['value']) + ' ' + r.get('unit', 'ج'), size, c, 900, anchor='end', x=-w / 2 + 110)
    if i:
        op = r.get('op', '+')
        cx = -w / 2 + 40
        # operator drawn as shapes, not a glyph: fonts lack U+2212 and RTL can move a '-' character
        bar = f'<rect x="{cx - 15}" y="-4.5" width="30" height="9" rx="4" fill="#fff"/>'
        if op == '+':
            bar += f'<rect x="{cx - 4.5}" y="-15" width="9" height="30" rx="4" fill="#fff"/>'
        out += f'<circle cx="{cx}" cy="0" r="30" fill="{col("ink", pal)}"/>' + bar
    return out


def eq_result(res, total, size, w, mode):
    """Result row under a rule: label + absolute value, red with 'خسارة' wording when negative."""
    pal = B if mode == 'B' else A
    neg = total < 0
    c = col('red' if neg else 'green', pal)
    label = res.get('label_negative' if neg else 'label', res.get('label', 'الصافي'))
    out = f'<line x1="{-w / 2}" y1="-58" x2="{w / 2}" y2="-58" stroke="{col("ink", pal)}" stroke-width="6" stroke-linecap="round"/>'
    out += text(label, size * 0.9, c, 900, anchor='start', x=w / 2 - 10)
    out += text(fmt_num(abs(total)) + ' ' + res.get('unit', 'ج'), size * 1.15, c, 900, anchor='end', x=-w / 2 + 110)
    return out


# ---------------------------------------------------------------- shared

def plain_text(e, pal):
    return text(e.get('text', ''), e.get('size', 48), col(e.get('color', 'ink'), pal), e.get('weight', 900),
                anchor={'right': 'start', 'left': 'end'}.get(e.get('align'), 'middle'))


def number(e, pal):
    c = col(e.get('color', 'ink'), pal)
    attrs = ''
    if 'count_to' in e:
        attrs = (f'class="count" data-from="{e.get("count_from", 0)}" data-to="{e["count_to"]}" '
                 f'data-prefix="{esc(e.get("prefix", ""))}" data-suffix="{esc(e.get("suffix", ""))}" '
                 f'data-dur="{e.get("count_dur", 1.0)}"')
    return text(e.get('text', ''), e.get('size', 120), c, 900, extra=attrs)


def raw_svg(e, pal):
    return e.get('svg', '')


BUILDERS = {
    'A': {'torn': a_torn, 'label': a_label, 'person': a_person, 'chair': a_chair, 'building': a_building,
          'money': a_money, 'ballot': a_ballot, 'siren': a_siren, 'calendar': a_calendar, 'card': a_card,
          'stamp': a_stamp},
    'B': {'icon': b_icon, 'wcard': b_wcard, 'pill': b_pill, 'headline': b_headline, 'cta': b_cta,
          'statcard': b_statcard, 'chapter': b_chapter},
}
SHARED = {'xmark': x_mark, 'check': check, 'arrow': arrow, 'text': plain_text, 'number': number, 'svg': raw_svg}


def build(e, mode):
    t = e['type']
    pal = A if mode == 'A' else B
    if t in BUILDERS[mode]:
        return BUILDERS[mode][t](e)
    if t in SHARED:
        return SHARED[t](e, pal)
    other = 'B' if mode == 'A' else 'A'
    if t in BUILDERS[other]:
        return BUILDERS[other][t](e)
    raise ValueError(f'unknown element type {t!r} (mode {mode})')


def element_types():
    return sorted(set(BUILDERS['A']) | set(BUILDERS['B']) | set(SHARED) | {'seats', 'steps', 'equation', 'photo'})
