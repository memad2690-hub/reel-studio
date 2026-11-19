"""Style frames for "الرحلة | CEOS Journey": three code-drawn stills (exterior, cabin, Chamber 135 glimpse).
Black, lime #D1FE17, white; amber only for الغرفة 135. Run: python3 frames.py → frame_*.html (rendered by shot.js)."""
import math
import os
import random

LIME, AMBER, W, H = '#D1FE17', '#FFB547', 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, '..', '..', '..', 'fonts', 'Cairo-Variable.ttf')


def defs():
    return f'''<defs>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="10" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="bigglow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="40"/></filter>
<filter id="soft"><feGaussianBlur stdDeviation="4"/></filter>
<linearGradient id="hullTop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3c37"/><stop offset="1" stop-color="#1c1d1a"/></linearGradient>
<linearGradient id="hullSide" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#262724"/><stop offset="1" stop-color="#0d0d0c"/></linearGradient>
<linearGradient id="nose" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b3d38"/><stop offset="1" stop-color="#151613"/></linearGradient>
<linearGradient id="pod" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a4c47"/><stop offset=".55" stop-color="#2a2b28"/><stop offset="1" stop-color="#121311"/></linearGradient>
<linearGradient id="floor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a0a09"/><stop offset="1" stop-color="#181916"/></linearGradient>
<radialGradient id="limeGlow"><stop offset="0" stop-color="{LIME}" stop-opacity=".9"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></radialGradient>
<radialGradient id="amberGlow"><stop offset="0" stop-color="{AMBER}" stop-opacity=".95"/><stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></radialGradient>
<radialGradient id="planet" cx=".3" cy=".2" r=".9"><stop offset="0" stop-color="#2c3a12"/><stop offset=".6" stop-color="#11160a"/><stop offset="1" stop-color="#050604"/></radialGradient>
<radialGradient id="vig" cx=".5" cy=".5" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".8"/></radialGradient>
</defs>'''


def stars(n=220, seed=3, y1=H):
    r = random.Random(seed)
    return ''.join(f'<circle cx="{r.uniform(0, W):.0f}" cy="{r.uniform(0, y1):.0f}" r="{r.choice([1, 1, 1.4, 2]):g}" '
                   f'fill="#fff" opacity="{r.uniform(.2, .8):.2f}"/>' for _ in range(n))


def text(s, x, y, size, fill='#fff', weight=900, anchor='middle', extra='', d='ltr'):
    """On-screen text is English (LTR); only captions are Arabic."""
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{2 if d == "ltr" else 0}" '
            f'direction="{d}" font-family="Cairo" {extra}>{s}</text>')


def caption(words, y=1440):
    """Sample caption: [(word, is_key)], laid right-to-left as one RTL line."""
    spans = ''.join(f'<tspan fill="{LIME if k else "#fff"}">{w} </tspan>' for w, k in words)
    return (f'<text x="{W/2}" y="{y}" font-size="70" font-weight="900" text-anchor="middle" direction="rtl" font-family="Cairo" '
            f'stroke="#000" stroke-width="12" paint-order="stroke" stroke-linejoin="round">{spans}</text>')


def hud(value, total, label, y=230, icon='people'):
    ic = ('<g transform="translate(-300,0)" fill="#fff"><circle cx="0" cy="-14" r="9"/><path d="M-16,12 q16,-24 32,0 z"/>'
          '<circle cx="-20" cy="-8" r="7" opacity=".7"/><circle cx="20" cy="-8" r="7" opacity=".7"/></g>')
    return f'''<g transform="translate({W/2},{y})">
<rect x="-400" y="-62" width="800" height="124" rx="40" fill="#000" fill-opacity=".72" stroke="#fff" stroke-opacity=".5" stroke-width="2"/>
<path d="M-430,-70 h40 M-430,-70 v30 M430,-70 h-40 M430,-70 v30 M-430,70 h40 M-430,70 v-30 M430,70 h-40 M430,70 v-30" stroke="{LIME}" stroke-width="6" fill="none"/>
{ic}<line x1="-250" y1="-34" x2="-250" y2="34" stroke="#fff" stroke-opacity=".4" stroke-width="2"/>
<text x="-215" y="20" font-size="64" font-weight="900" fill="{LIME}" direction="ltr" font-family="Cairo">{value}<tspan fill="#fff"> / {total}</tspan></text>
<g transform="translate(120,6)">{''.join(f'<rect x="{i*11}" y="-14" width="6" height="28" rx="3" fill="{LIME if i < 1 else "#3a3b36"}"/>' for i in range(22))}</g>
<text x="0" y="104" font-size="30" font-weight="800" fill="#fff" fill-opacity=".8" text-anchor="middle" letter-spacing="4" direction="ltr" font-family="Cairo">{label}</text></g>'''


def tracker(active=0, y=1700):
    labels = ['BOARD YOUR BRAND', 'THE JOURNEY', 'THE NEW WORLD']
    xs = [200, 540, 880]                                  # LTR: the first stage on the left
    out = [f'<line x1="{xs[0]}" y1="{y}" x2="{xs[2]}" y2="{y}" stroke="#fff" stroke-opacity=".6" stroke-width="3"/>']
    for i, (x, l) in enumerate(zip(xs, labels)):
        on = i <= active
        out.append(f'<circle cx="{x}" cy="{y}" r="20" fill="{LIME if on else "#000"}" stroke="{LIME if on else "#fff"}" stroke-width="4"'
                   + (' filter="url(#glow)"' if on else '') + '/>')
        out.append(text(l, x, y + 62, 28, '#fff' if on else '#bdbdb5', 800))
    return ''.join(out)


# ---------------------------------------------------------------- 1. the ship, outside
def lerp(a, b, t):
    return a + (b - a) * t


def exterior():
    out = [stars(260, 3), stars(60, 9)]
    # planet edge, bottom right (no destination shown yet)
    out.append(f'<circle cx="1180" cy="2380" r="1000" fill="url(#planet)"/><circle cx="1180" cy="2380" r="1000" fill="none" stroke="{LIME}" stroke-width="5" opacity=".75" filter="url(#glow)"/>')
    out.append(f'<path d="M150,1500 Q700,1250 1080,1330" fill="none" stroke="{LIME}" stroke-opacity=".25" stroke-width="2"/>')
    # hull: nose (hexagon, facing the viewer at left) + side receding to the right
    N = [(100, 900), (220, 740), (520, 740), (610, 900), (570, 1300), (140, 1300)]   # nose outline
    vpx, vpy = 1180, 780                                 # vanishing point
    top0, top1 = (520, 740), (vpx - 40, vpy - 60)
    bot0, bot1 = (570, 1300), (vpx - 40, vpy + 190)
    mid0 = (610, 900)
    # side face (lit by the destination glow on the far end)
    side = [mid0, (lerp(mid0[0], vpx, .82), lerp(mid0[1], vpy + 10, .82)), (lerp(bot0[0], bot1[0], .82), lerp(bot0[1], bot1[1], .82)), bot0]
    out.append(f'<polygon points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in side)}" fill="url(#hullSide)" stroke="#000" stroke-width="2"/>')
    roof = [top0, (lerp(top0[0], vpx, .82), lerp(top0[1], vpy - 30, .82)), (lerp(mid0[0], vpx, .82), lerp(mid0[1], vpy + 10, .82)), mid0]
    out.append(f'<polygon points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in roof)}" fill="url(#hullTop)" stroke="#000" stroke-width="2"/>')
    # windows on the side face: rows × columns in perspective; all dark (empty ship) except Chamber 135
    rows, cols = 5, 22
    a0, a1, b0, b1 = side[0], side[1], side[3], side[2]
    for c in range(cols):
        t0 = (1 - (1 - c / cols) ** 1.0) ** 1.35
        t1 = (1 - (1 - (c + .7) / cols) ** 1.0) ** 1.35
        for r in range(rows):
            v0, v1 = .1 + r * .165, .1 + r * .165 + .115
            def P(t, v):
                top = (lerp(a0[0], a1[0], t), lerp(a0[1], a1[1], t)); bot = (lerp(b0[0], b1[0], t), lerp(b0[1], b1[1], t))
                return lerp(top[0], bot[0], v), lerp(top[1], bot[1], v)
            q = [P(t0, v0), P(t1, v0), P(t1, v1), P(t0, v1)]
            amber = (c, r) == (6, 2)
            fill = AMBER if amber else '#1a1d0c'
            out.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in q)}" fill="{fill}" stroke="{LIME}" '
                       f'stroke-opacity="{0 if amber else .55}" stroke-width="2"/>')
            if amber:
                cx, cy = (q[0][0] + q[2][0]) / 2, (q[0][1] + q[2][1]) / 2
                out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="60" fill="url(#amberGlow)" opacity=".8"/>')
                out.append(f'<path d="M{cx:.0f},{cy-16:.0f} L{cx+60:.0f},{cy-250:.0f} h40" stroke="{AMBER}" stroke-width="3" fill="none"/>'
                           f'<g transform="translate({cx+170:.0f},{cy-250:.0f})"><rect x="-70" y="-30" width="140" height="58" rx="12" fill="#000" stroke="{AMBER}" stroke-width="3"/>'
                           + text('135', 0, 12, 34, AMBER) + '</g>')
    # lime light strips along the hull
    for v in (.03, .96):
        p0 = (lerp(a0[0], b0[0], v), lerp(a0[1], b0[1], v)); p1 = (lerp(a1[0], b1[0], v), lerp(a1[1], b1[1], v))
        out.append(f'<line x1="{p0[0]:.0f}" y1="{p0[1]:.0f}" x2="{p1[0]:.0f}" y2="{p1[1]:.0f}" stroke="{LIME}" stroke-width="5" opacity=".8" filter="url(#glow)"/>')
    # superstructure blocks on the roof
    for i, (t, h, w) in enumerate([(.06, 70, .1), (.22, 46, .08), (.36, 58, .07), (.5, 34, .06), (.62, 40, .05)]):
        p = (lerp(top0[0], vpx, t), lerp(top0[1], vpy - 30, t) + 18)
        p2 = (lerp(top0[0], vpx, t + w), lerp(top0[1], vpy - 30, t + w) + 18)
        s = 1 - t * .8
        out.append(f'<polygon points="{p[0]:.0f},{p[1]:.0f} {p[0]:.0f},{p[1]-h*s:.0f} {p2[0]:.0f},{p2[1]-h*s*.9:.0f} {p2[0]:.0f},{p2[1]:.0f}" fill="#2c2d29" stroke="#000"/>'
                   f'<line x1="{p[0]+4:.0f}" y1="{p[1]-h*s*.55:.0f}" x2="{p2[0]-4:.0f}" y2="{p2[1]-h*s*.5:.0f}" stroke="{LIME}" stroke-width="{4*s:.1f}" opacity=".85"/>')
        if i in (0, 2):
            out.append(f'<line x1="{p[0]+12:.0f}" y1="{p[1]-h*s:.0f}" x2="{p[0]+12:.0f}" y2="{p[1]-h*s-60*s:.0f}" stroke="#bbb" stroke-width="3"/>'
                       f'<circle cx="{p[0]+12:.0f}" cy="{p[1]-h*s-60*s:.0f}" r="4" fill="{LIME}" filter="url(#glow)"/>')
    # nose with the 10,000 plate
    out.append(f'<polygon points="{" ".join(f"{x},{y}" for x, y in N)}" fill="url(#nose)" stroke="#000" stroke-width="3"/>')
    out.append(f'<polygon points="160,915 245,800 495,800 560,915 530,1100 190,1100" fill="#0a0b09" stroke="{LIME}" stroke-width="5" filter="url(#glow)"/>')
    out.append(text('10,000', 375, 980, 100, LIME, 900))
    out.append(text('مكان للبراندات', 375, 1050, 40, '#fff', 800))
    # boarding door + ramp
    out.append(f'<rect x="300" y="1170" width="160" height="130" rx="6" fill="{LIME}" opacity=".95" filter="url(#glow)"/>'
               f'<rect x="318" y="1186" width="124" height="114" rx="4" fill="#e9ff7a"/>'
               f'<line x1="380" y1="1186" x2="380" y2="1300" stroke="#bccc34" stroke-width="3"/>')
    out.append(f'<polygon points="300,1300 460,1300 120,1640 -160,1640" fill="#1b1c19" stroke="#000" stroke-width="2"/>')
    for i in range(7):
        t0, t1 = i / 7, i / 7 + .06
        out.append(f'<line x1="{lerp(380, -20, t0):.0f}" y1="{lerp(1300, 1640, t0):.0f}" x2="{lerp(380, -20, t1):.0f}" y2="{lerp(1300, 1640, t1):.0f}" stroke="{LIME}" stroke-width="{4 + i*2}" stroke-linecap="round"/>')
    out.append(f'<ellipse cx="380" cy="1310" rx="140" ry="26" fill="url(#limeGlow)" opacity=".7"/>')
    out.append(hud('0', '10,000', 'BRANDS ON BOARD'))
    out.append(caption([('فيها', False), ('عشرة', True), ('آلاف', True), ('مكان.', False)], y=1530))
    out.append(tracker(0, 1710))
    return ''.join(out)


# ---------------------------------------------------------------- 2. the cabin, one seat lit
def cabin():
    vpx, vpy = 540, 800
    out = [f'<rect width="{W}" height="{H}" fill="#050505"/>']
    # end window with planet curve
    out.append(f'<path d="M330,820 L330,640 A210,210 0 0 1 750,640 L750,820 Z" fill="#000" stroke="#d9d9d4" stroke-width="6"/>')
    out.append(f'<clipPath id="win"><path d="M330,820 L330,640 A210,210 0 0 1 750,640 L750,820 Z"/></clipPath>'
               f'<g clip-path="url(#win)">{stars(40, 5, 900)}<circle cx="540" cy="1620" r="860" fill="url(#planet)"/>'
               f'<circle cx="540" cy="1620" r="860" fill="none" stroke="#e8e8e2" stroke-width="3" opacity=".7"/></g>'
               f'<line x1="470" y1="460" x2="470" y2="820" stroke="#d9d9d4" stroke-width="3"/><line x1="610" y1="460" x2="610" y2="820" stroke="#d9d9d4" stroke-width="3"/>')
    # ceiling ribs (arches toward the vanishing point)
    for k in range(6):
        s = 1 / (1 + k * .55)
        rx, top = 900 * s, vpy - 820 * s
        col = LIME if k in (1, 3) else '#e6e6e0'
        out.append(f'<path d="M{vpx - rx:.0f},{vpy + 40*s:.0f} L{vpx - rx:.0f},{vpy - 300*s:.0f} Q{vpx - rx:.0f},{top:.0f} {vpx - rx*.45:.0f},{top:.0f} '
                   f'L{vpx + rx*.45:.0f},{top:.0f} Q{vpx + rx:.0f},{top:.0f} {vpx + rx:.0f},{vpy - 300*s:.0f} L{vpx + rx:.0f},{vpy + 40*s:.0f}" '
                   f'fill="none" stroke="#2a2b28" stroke-width="{60*s:.0f}"/>')
        for side in (-1, 1):
            out.append(f'<line x1="{vpx + side*rx*.98:.0f}" y1="{vpy - 340*s:.0f}" x2="{vpx + side*rx*.8:.0f}" y2="{top + 60*s:.0f}" stroke="{col}" '
                       f'stroke-width="{10*s:.1f}" stroke-linecap="round" opacity=".9" filter="url(#glow)"/>')
    # floor + aisle lines
    out.append(f'<polygon points="0,{vpy+60} {W},{vpy+60} {W},{H} 0,{H}" fill="url(#floor)"/>')
    for x in (-150, 150):
        out.append(f'<line x1="{vpx + x*.12:.0f}" y1="{vpy+60}" x2="{vpx + x*3.4:.0f}" y2="{H}" stroke="#fff" stroke-width="3" opacity=".7"/>')
    for i in range(14):
        t = (i / 14) ** 1.8
        y = vpy + 60 + (H - vpy - 60) * t
        out.append(f'<circle cx="{vpx - 150*(.12 + 3.28*t) + 18:.0f}" cy="{y:.0f}" r="{1 + 3*t:.1f}" fill="#fff" opacity=".8"/>'
                   f'<circle cx="{vpx + 150*(.12 + 3.28*t) - 18:.0f}" cy="{y:.0f}" r="{1 + 3*t:.1f}" fill="#fff" opacity=".8"/>')
    # wall portholes on the left (the window side) + engine vents on the right
    for k in range(5):
        s = 1 / (1 + k * .6)
        out.append(f'<ellipse cx="{vpx - 560*s - 20:.0f}" cy="{vpy - 120*s:.0f}" rx="{38*s:.0f}" ry="{56*s:.0f}" fill="#0c1006" stroke="{LIME}" stroke-width="{4*s:.1f}" opacity=".9"/>')
        out.append(f'<rect x="{vpx + 520*s:.0f}" y="{vpy - 170*s:.0f}" width="{60*s:.0f}" height="{120*s:.0f}" rx="{8*s:.0f}" fill="#111" stroke="{LIME}" stroke-width="{3*s:.1f}" opacity=".7"/>'
                   + ''.join(f'<line x1="{vpx + 528*s:.0f}" y1="{vpy - 150*s + j*22*s:.0f}" x2="{vpx + 572*s:.0f}" y2="{vpy - 150*s + j*22*s:.0f}" stroke="{LIME}" stroke-width="{3*s:.1f}" opacity=".6"/>' for j in range(5)))
    # far-end door: الغرفة 135 (amber), small
    out.append(f'<rect x="508" y="742" width="64" height="76" rx="6" fill="#1a1106" stroke="{AMBER}" stroke-width="3"/>'
               f'<circle cx="540" cy="780" r="70" fill="url(#amberGlow)" opacity=".45"/>' + text('135', 540, 790, 22, AMBER))
    # pod seats: rows both sides of the aisle, far → near
    def pod(x, y, s, lit=False):
        w, h = 230 * s, 300 * s
        sh = f'<ellipse cx="{x:.0f}" cy="{y + h*.5:.0f}" rx="{w*.55:.0f}" ry="{18*s:.0f}" fill="#000" opacity=".7"/>'
        if lit:
            sh += f'<ellipse cx="{x:.0f}" cy="{y + h*.48:.0f}" rx="{w*.8:.0f}" ry="{60*s:.0f}" fill="url(#limeGlow)" opacity=".8"/>'
        shell = (f'<rect x="{x - w/2:.0f}" y="{y - h/2:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{w*.32:.0f}" '
                 f'fill="{"#9fbf0f" if lit else "url(#pod)"}" stroke="{LIME if lit else "#6b6d66"}" stroke-width="{max(1, 5*s):.1f}"/>')
        inner = (f'<rect x="{x - w*.38:.0f}" y="{y - h*.38:.0f}" width="{w*.76:.0f}" height="{h*.7:.0f}" rx="{w*.22:.0f}" fill="{"#c8f20f" if lit else "#0d0e0c"}"/>'
                 f'<rect x="{x - w*.26:.0f}" y="{y - h*.28:.0f}" width="{w*.52:.0f}" height="{h*.42:.0f}" rx="{w*.08:.0f}" fill="{"#e5ff6b" if lit else "#1b1c19"}"/>'
                 f'<rect x="{x - w*.34:.0f}" y="{y + h*.12:.0f}" width="{w*.68:.0f}" height="{h*.14:.0f}" rx="{w*.06:.0f}" fill="{"#d7ff2c" if lit else "#232421"}"/>')
        rim = f'<line x1="{x - w*.4:.0f}" y1="{y + h*.46:.0f}" x2="{x + w*.4:.0f}" y2="{y + h*.46:.0f}" stroke="{LIME if lit else "#ddd"}" stroke-width="{max(1, 5*s):.1f}" opacity=".9"/>'
        plus = (f'<path d="M{x:.0f},{y - h*.16:.0f} v{h*.2:.0f} M{x - h*.1:.0f},{y - h*.06:.0f} h{h*.2:.0f}" stroke="#fff" stroke-width="{8*s:.1f}" stroke-linecap="round"/>' if lit else '')
        return sh + shell + inner + rim + plus
    pods = []
    for k in range(9, -1, -1):
        s = 1 / (1 + k * .42)
        y = vpy + 60 + (1350 - vpy - 60) * s
        for col in range(3):
            for side in (-1, 1):
                x = vpx + side * (170 + col * 240) * s
                if k == 0 and col == 0 and side == 1:
                    continue
                pods.append(pod(x, y, s))
    out += pods
    out.append(f'<rect x="{vpx-150}" y="1440" width="300" height="60" rx="14" fill="none" stroke="{LIME}" stroke-width="5" filter="url(#glow)" transform="translate(0,-20)"/>')
    out.append(pod(vpx, 1300, .95, lit=True))
    out.append(f'<g transform="translate({vpx},1050)"><rect x="-150" y="-38" width="300" height="70" rx="35" fill="#000" stroke="{LIME}" stroke-width="4"/>'
               + text('YOUR BRAND', 0, 12, 34) + f'<line x1="0" y1="32" x2="0" y2="80" stroke="{LIME}" stroke-width="3"/></g>')
    # seat zones (the comment choices)
    def zone(t, x, y, col=LIME):
        return (f'<g transform="translate({x},{y})"><rect x="-150" y="-30" width="300" height="56" rx="28" fill="#000" fill-opacity=".8" stroke="{col}" stroke-width="3"/>'
                + text(t, 0, 10, 26, '#fff', 800) + '</g>')
    out += [zone('BY THE WINDOW', 190, 560), zone('BY THE ENGINE', 890, 560), zone('BY ROOM 135', 540, 900, AMBER)]
    out.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    out.append(hud('0', '10,000', 'BRANDS ON BOARD'))
    out.append(caption([('براندات', False), ('مين؟…', False), ('براندك', True), ('إنت.', False)], y=1640))
    return ''.join(out)


# ---------------------------------------------------------------- 3. the corridor of units, Chamber 135 glimpse
def chamber():
    vpx, vpy = 540, 860
    out = [f'<rect width="{W}" height="{H}" fill="#040404"/>']
    # walls of units (134 lime), perspective on both sides
    n = 0
    for side in (-1, 1):
        for k in range(12):
            s0, s1 = 1 / (1 + k * .38), 1 / (1 + (k + .8) * .38)
            x0, x1 = vpx + side * 980 * s0, vpx + side * 980 * s1
            for r in range(6):
                y0a, y1a = vpy + (-560 + r * 170) * s0, vpy + (-560 + r * 170 + 130) * s0
                y0b, y1b = vpy + (-560 + r * 170) * s1, vpy + (-560 + r * 170 + 130) * s1
                n += 1
                out.append(f'<polygon points="{x0:.0f},{y0a:.0f} {x1:.0f},{y0b:.0f} {x1:.0f},{y1b:.0f} {x0:.0f},{y1a:.0f}" fill="#141a05" stroke="{LIME}" '
                           f'stroke-width="{3*s0:.1f}"/>'
                           f'<line x1="{lerp(x0, x1, .2):.0f}" y1="{lerp(y1a, y1b, .2) - 18*s0:.0f}" x2="{lerp(x0, x1, .8):.0f}" y2="{lerp(y1a, y1b, .8) - 18*s1:.0f}" '
                           f'stroke="{LIME}" stroke-width="{10*s0:.1f}" stroke-linecap="round" opacity=".9" filter="url(#glow)"/>')
    # floor + light lines
    out.append(f'<polygon points="{vpx-180},{vpy+260} {vpx+180},{vpy+260} {W+300},{H} -300,{H}" fill="#0b0b0a"/>')
    for i in range(6):
        t0, t1 = (i / 6) ** 1.6, (i / 6) ** 1.6 + .05
        for side in (-1, 1):
            out.append(f'<line x1="{vpx + side*lerp(60, 330, t0):.0f}" y1="{lerp(vpy+260, H, t0):.0f}" x2="{vpx + side*lerp(60, 330, t1):.0f}" y2="{lerp(vpy+260, H, t1):.0f}" '
                       f'stroke="{LIME}" stroke-width="{4 + 10*t0:.0f}" stroke-linecap="round"/>')
    # the sealed amber chamber at the end
    out.append(f'<circle cx="{vpx}" cy="{vpy}" r="330" fill="url(#amberGlow)" opacity=".55"/>')
    out.append(f'<rect x="{vpx-110}" y="{vpy-190}" width="220" height="400" rx="20" fill="#0d0904" stroke="{AMBER}" stroke-width="6" filter="url(#glow)"/>'
               f'<line x1="{vpx}" y1="{vpy-190}" x2="{vpx}" y2="{vpy+210}" stroke="{AMBER}" stroke-width="3" opacity=".7"/>'
               f'<circle cx="{vpx}" cy="{vpy+40}" r="18" fill="{AMBER}" filter="url(#glow)"/>'
               + text('135', vpx, vpy - 100, 64, AMBER))
    out.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    out.append(hud('134', '134', 'UNITS ONLINE'))
    out.append(caption([('محدش', False), ('عارف', False), ('وراها', False), ('إيه.', True)], y=1560))
    return ''.join(out)


def page(body):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>@font-face{{font-family:Cairo;src:url("file://{os.path.abspath(FONT)}");'
            f'font-weight:200 1000}}html,body{{margin:0;background:#000}}</style></head><body>'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Cairo">'
            f'<rect width="{W}" height="{H}" fill="#000"/>{defs()}{body}</svg></body></html>')


if __name__ == '__main__':
    for name, fn in (('exterior', exterior), ('cabin', cabin), ('chamber', chamber)):
        open(os.path.join(HERE, f'frame_{name}.html'), 'w', encoding='utf-8').write(page(fn()))
    print('ok')
