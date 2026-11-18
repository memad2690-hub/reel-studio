"""CEOS Creative Breakdown kit: buying-motivation cards, sample ad mockups and the fictional jacket they share.

Brand: CEOS lime #D1FE17 with black and white. Everything here is a template drawn in SVG (no image generation):
the jacket is an original illustration of a fictional product, the ads are labelled samples ("إعلان تجريبي"),
and no card carries prices, discounts, delivery promises or performance numbers.
"""
import kits

LIME, BLACK, WHITE, GREY = '#D1FE17', '#0b0b0b', '#ffffff', '#8a8a84'


def t(s, size, color=BLACK, weight=900, y=0, x=0, anchor='middle', extra=''):
    return kits.text(s, size, color, weight, anchor=anchor, y=y, x=x, extra=extra, exact=True)


# ---------------------------------------------------------------- the fictional product
def jacket(scale=1.0, body='#2f3a2c', trim='#1c2219', zip_c='#c9c9c0'):
    """An original bomber-jacket drawing, centred on (0,0), ~340 wide × 330 tall at scale 1."""
    s = scale
    sleeve_l = 'M-92,-118 L-150,-78 L-172,118 L-128,128 L-108,-22 Z'
    sleeve_r = 'M92,-118 L150,-78 L172,118 L128,128 L108,-22 Z'
    torso = 'M-92,-118 L-38,-146 Q0,-122 38,-146 L92,-118 L110,138 L-110,138 Z'
    return (f'<g transform="scale({s:g})" stroke="{trim}" stroke-width="3" stroke-linejoin="round">'
            f'<path d="{sleeve_l}" fill="{body}"/><path d="{sleeve_r}" fill="{body}"/>'
            f'<path d="{torso}" fill="{body}"/>'
            # ribbed collar, cuffs and hem
            f'<path d="M-40,-146 Q0,-116 40,-146 L44,-132 Q0,-100 -44,-132 Z" fill="{trim}"/>'
            f'<path d="M-172,118 L-128,128 L-130,150 L-175,141 Z" fill="{trim}"/>'
            f'<path d="M172,118 L128,128 L130,150 L175,141 Z" fill="{trim}"/>'
            f'<rect x="-112" y="132" width="224" height="26" rx="6" fill="{trim}"/>'
            # zip, pull and welt pockets
            f'<line x1="0" y1="-118" x2="0" y2="132" stroke="{zip_c}" stroke-width="4"/>'
            f'<rect x="-6" y="-104" width="12" height="20" rx="3" fill="{zip_c}" stroke="none"/>'
            f'<line x1="-82" y1="40" x2="-46" y2="88" stroke="{trim}" stroke-width="5" stroke-linecap="round"/>'
            f'<line x1="82" y1="40" x2="46" y2="88" stroke="{trim}" stroke-width="5" stroke-linecap="round"/>'
            # sleeve pocket + a few seam lines for texture
            f'<rect x="-150" y="-50" width="30" height="40" rx="5" fill="none" stroke="{trim}" stroke-width="3" '
            f'transform="rotate(8 -135 -30)"/>'
            f'<path d="M-92,-118 L-104,40 M92,-118 L104,40" fill="none" stroke="{trim}" stroke-width="2" opacity=".55"/>'
            '</g>')


# ---------------------------------------------------------------- icons (black on lime, ~64px box centred on 0,0)
def icon(kind, c=BLACK):
    sw = f'stroke="{c}" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    if kind == 'price':
        return (f'<path d="M-24,-26 L10,-26 L30,0 L10,26 L-24,26 Z" {sw}/>'
                f'<circle cx="-10" cy="0" r="6" fill="{c}"/>')
    if kind == 'quality':
        return (f'<path d="M-28,-8 L-14,-26 L14,-26 L28,-8 L0,28 Z" {sw}/>'
                f'<path d="M-28,-8 L28,-8 M-8,-26 L0,-8 L8,-26 M0,-8 L0,28" {sw} stroke-width="4"/>')
    if kind == 'value':
        return (f'<path d="M0,-28 L0,26 M-22,26 L22,26 M-30,-16 L30,-16" {sw}/>'
                f'<path d="M-30,-16 L-40,8 L-20,8 Z M30,-16 L20,8 L40,8 Z" {sw} stroke-width="4"/>')
    if kind == 'statement':
        return (f'<path d="M0,-30 L9,-9 L31,-8 L14,7 L19,29 L0,17 L-19,29 L-14,7 L-31,-8 L-9,-9 Z" {sw}/>')
    if kind == 'delivery':
        return (f'<path d="M-34,-16 L8,-16 L8,14 L-34,14 Z M8,-6 L24,-6 L34,6 L34,14 L8,14" {sw}/>'
                f'<circle cx="-20" cy="20" r="7" fill="{c}"/><circle cx="22" cy="20" r="7" fill="{c}"/>')
    if kind == 'gift':
        return (f'<path d="M-28,-6 L28,-6 L28,28 L-28,28 Z M-32,-18 L32,-18 L32,-6 L-32,-6 Z M0,-18 L0,28" {sw}/>'
                f'<path d="M0,-18 C-10,-36 -26,-28 -14,-18 M0,-18 C10,-36 26,-28 14,-18" {sw} stroke-width="4"/>')
    if kind == 'comfort':
        return (f'<path d="M-26,18 C-40,18 -40,-4 -24,-4 C-22,-22 2,-26 8,-10 C22,-18 36,-4 28,10 C36,14 32,22 24,22 Z" {sw}/>')
    if kind == 'unique':
        return (f'<path d="M0,-30 L6,-6 L30,0 L6,6 L0,30 L-6,6 L-30,0 L-6,-6 Z" fill="{c}"/>')
    return f'<circle r="20" {sw}/>'


# ---------------------------------------------------------------- buying-motivation card
def motive(e):
    """Black pill card: lime icon disc on the right (RTL), Arabic label, small English tag."""
    w, h = e.get('w', 420), e.get('h', 128)
    size = e.get('size', 46)
    disc = h * 0.36
    tag = e.get('tag', '')
    x_text = w / 2 - h + 6                      # right-aligned text, left of the icon disc
    return (f'<g>'
            f'<rect x="{-w/2+8}" y="{-h/2+10}" width="{w}" height="{h}" rx="{h/2}" fill="rgba(0,0,0,.18)"/>'
            f'<rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" rx="{h/2}" fill="{BLACK}"/>'
            f'<circle cx="{w/2 - h/2}" cy="0" r="{disc}" fill="{LIME}"/>'
            f'<g transform="translate({w/2 - h/2},0) scale({disc/34:.3f})">{icon(e.get("icon", "price"))}</g>'
            + t(e.get('text', ''), size, WHITE, 900, y=(-14 if tag else 0), x=x_text, anchor='start')
            + (f'<g data-deco="1">' + t(tag, 24, LIME, 800, y=34, x=x_text, anchor='start', extra='letter-spacing="2"') + '</g>'
               if tag else '')
            + '</g>')


# ---------------------------------------------------------------- sample ad mockup
SCENES = {   # angle → (image background, prop drawn behind/next to the jacket)
    'price':     ('#efeee6', 'tag'),
    'quality':   ('#e7e2d6', 'loupe'),
    'statement': ('#111111', 'spot'),
    'comfort':   ('#e3edf2', 'cloud'),
    'value':     ('#eef3dc', 'scale'),
    'delivery':  ('#f1ece2', 'truck'),
    'gift':      ('#f4e6e6', 'gift'),
    'base':      ('#ecebe4', ''),
}


def admock(e):
    """A sample social ad for the fictional jacket: header, image, headline, angle chip. Centred on (0,0)."""
    w, h = e.get('w', 440), e.get('h', 600)
    angle = e.get('angle', 'base')
    bg, prop = SCENES.get(angle, SCENES['base'])
    k = w / 440                                   # everything scales with the card width
    pad = 18 * k
    head_h = 64 * k
    img_h = h * 0.56
    img_y = -h / 2 + head_h
    out = [f'<rect x="{-w/2+10*k}" y="{-h/2+14*k}" width="{w}" height="{h}" rx="{26*k}" fill="rgba(0,0,0,.22)"/>',
           f'<rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" rx="{26*k}" fill="{WHITE}" stroke="{BLACK}" '
           f'stroke-width="{max(2, 4*k):.1f}"/>']
    # header: brand avatar + name (right, RTL) and the sample label (left)
    ay = -h / 2 + head_h / 2
    out.append(f'<circle cx="{w/2 - pad - 18*k}" cy="{ay}" r="{18*k}" fill="{BLACK}"/>')
    out.append('<g data-deco="1">' + t('ب', 22 * k, LIME, 900, y=ay - 2 * k, x=w / 2 - pad - 18 * k)
               + t('براندك', 24 * k, BLACK, 900, y=ay, x=w / 2 - pad - 44 * k, anchor='start')
               + t(e.get('label', 'مثال · منتج تخيّلي'), 18 * k, GREY, 700, y=ay, x=-w / 2 + pad, anchor='end') + '</g>')
    # image area
    ix, iw = -w / 2 + pad, w - 2 * pad
    clip = f'adclip{abs(hash((angle, w, h))) % 10**6}'
    out.append(f'<clipPath id="{clip}"><rect x="{ix}" y="{img_y}" width="{iw}" height="{img_h}" rx="{14*k}"/></clipPath>')
    g = [f'<rect x="{ix}" y="{img_y}" width="{iw}" height="{img_h}" fill="{bg}"/>']
    cy = img_y + img_h / 2 + 6 * k
    js = img_h / 360 * (0.86 if prop else 0.92)
    if prop == 'spot':
        g.append(f'<ellipse cx="0" cy="{cy+img_h*0.36}" rx="{iw*0.42}" ry="{img_h*0.08}" fill="{LIME}" opacity=".35"/>')
        g.append(f'<circle cx="0" cy="{cy-10*k}" r="{img_h*0.47}" fill="#e9e9e2" opacity=".92"/>')
        g.append(f'<circle cx="0" cy="{cy-10*k}" r="{img_h*0.47}" fill="none" stroke="{LIME}" stroke-width="{6*k}"/>')
    if prop == 'cloud':
        for cx_, cy_, r in ((-0.30, -0.30, 0.10), (-0.20, -0.33, 0.12), (0.28, -0.25, 0.09)):
            g.append(f'<circle cx="{iw*cx_}" cy="{cy+img_h*cy_}" r="{img_h*r}" fill="#ffffff" opacity=".9"/>')
    if prop == 'loupe':                           # magnified fabric texture beside the jacket
        lc = f'loupe{abs(hash((w, h))) % 10**6}'
        g.append(f'<g transform="translate({iw*0.27},{cy-img_h*0.22})">'
                 f'<clipPath id="{lc}"><circle r="{img_h*0.17}"/></clipPath>'
                 f'<circle r="{img_h*0.17}" fill="#3a4636"/><g clip-path="url(#{lc})">'
                 + ''.join(f'<line x1="{-img_h*0.17}" y1="{d*k}" x2="{img_h*0.17}" y2="{d*k+img_h*0.08}" '
                           f'stroke="#56634f" stroke-width="{3*k}"/>' for d in range(-60, 61, 12))
                 + f'</g><circle r="{img_h*0.17}" fill="none" stroke="{BLACK}" stroke-width="{5*k}"/>'
                 + f'<line x1="{img_h*0.12}" y1="{img_h*0.12}" x2="{img_h*0.24}" y2="{img_h*0.24}" '
                   f'stroke="{BLACK}" stroke-width="{9*k}" stroke-linecap="round"/></g>')
    jx = -iw * 0.08 if prop in ('loupe', 'tag', 'scale', 'truck', 'gift') else 0
    g.append(f'<g transform="translate({jx},{cy})">{jacket(js)}</g>')
    if prop in ('tag', 'scale', 'truck', 'gift'):
        ic = {'tag': 'price', 'scale': 'value', 'truck': 'delivery', 'gift': 'gift'}[prop]
        r = img_h * 0.15
        g.append(f'<g transform="translate({iw*0.30},{cy-img_h*0.22})"><circle r="{r}" fill="{LIME}" stroke="{BLACK}" '
                 f'stroke-width="{4*k}"/><g transform="scale({r/38:.3f})">{icon(ic)}</g></g>')
    out.append(f'<g clip-path="url(#{clip})">{"".join(g)}</g>')
    # headline (1–2 lines) and angle chip
    lines = e.get('lines') or [e.get('headline', '')]
    hs = e.get('size', 32) * k
    hy = img_y + img_h + 18 * k + hs * 0.62
    for i, ln in enumerate(lines[:2]):
        out.append(t(ln, hs, BLACK, 900, y=hy + i * hs * 1.25, x=w / 2 - pad, anchor='start'))
    chip = e.get('chip', '')
    if chip:
        cw = max(120 * k, len(chip) * 17 * k + 44 * k)
        cy2 = img_y + img_h - 30 * k
        out.append(f'<rect x="{w/2 - pad - cw}" y="{cy2 - 22*k}" width="{cw}" height="{44*k}" rx="{22*k}" fill="{LIME}" '
                   f'stroke="{BLACK}" stroke-width="{3*k}"/>')
        out.append('<g data-deco="1">' + t(chip, 22 * k, BLACK, 900, y=cy2, x=w / 2 - pad - cw / 2) + '</g>')
    deco = ' data-deco="1"' if (w < 300 or e.get('deco')) else ''
    return f'<g{deco}>' + ''.join(out) + '</g>'


def product(e):
    """The jacket alone on a lime disc (the 'one product' moment)."""
    r = e.get('r', 230)
    return (f'<g><circle r="{r}" fill="{LIME}"/><circle r="{r}" fill="none" stroke="{BLACK}" stroke-width="6"/>'
            f'<g transform="translate(0,10)">{jacket(r / 215)}</g>'
            + (t(e['label'], 30, BLACK, 900, y=r + 46) if e.get('label') else '') + '</g>')


def banner(e):
    """Black bar with lime text: section labels like "منتج واحد → إعلانات كتير"."""
    w, h = e.get('w', 760), e.get('h', 92)
    return (f'<g><rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" rx="{h/2}" fill="{BLACK}"/>'
            + t(e.get('text', ''), e.get('size', 44), e.get('color') == 'white' and WHITE or LIME, 900) + '</g>')


def crowd(e):
    """n people (2 rows), black; optional per-person lime question marks: 'same product, different reasons'."""
    n, cols = e.get('n', 10), e.get('cols', 5)
    gap = e.get('gap', 150)
    out = []
    rows = (n + cols - 1) // cols
    for i in range(n):
        r, c = divmod(i, cols)
        x = (c - (cols - 1) / 2) * gap
        y = (r - (rows - 1) / 2) * gap * 1.25
        out.append(f'<g transform="translate({x},{y})"><circle cy="-34" r="22" fill="{BLACK}"/>'
                   f'<path d="M-34,40 Q-34,-6 0,-6 Q34,-6 34,40 Z" fill="{BLACK}"/>'
                   + (f'<g data-deco="1"><circle cx="26" cy="-66" r="17" fill="{LIME}" stroke="{BLACK}" stroke-width="3"/>'
                      + t('?', 24, BLACK, 900, y=-66, x=26) + '</g>' if e.get('ask') else '') + '</g>')
    return '<g>' + ''.join(out) + '</g>'


BUILDERS = {'crowd': crowd, 'motive': motive, 'admock': admock, 'product': product, 'banner': banner}
