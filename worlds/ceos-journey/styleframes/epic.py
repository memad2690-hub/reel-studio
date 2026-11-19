"""Two epic ship options for the exterior frame: A = launch-pad rocket (low angle), B = starship in flight.
Reuses the helpers in frames.py. Run: python3 epic.py → frame_rocket.html, frame_starship.html."""
import math, os, random
from frames import LIME, AMBER, W, H, HERE, defs, stars, text, caption, hud, tracker, page, lerp

EXTRA = f'''<defs>
<linearGradient id="cyl" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0b0b0a"/><stop offset=".28" stop-color="#3d3f3a"/>
<stop offset=".42" stop-color="#5a5c55"/><stop offset=".7" stop-color="#22231f"/><stop offset="1" stop-color="#070707"/></linearGradient>
<linearGradient id="beam" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{LIME}" stop-opacity=".28"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></linearGradient>
<linearGradient id="upper" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#55574f"/><stop offset="1" stop-color="#25261f"/></linearGradient>
<linearGradient id="belly" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#161714"/><stop offset="1" stop-color="#050505"/></linearGradient>
<linearGradient id="trail" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#f4ffc4"/><stop offset=".25" stop-color="{LIME}" stop-opacity=".8"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></linearGradient>
<radialGradient id="smoke"><stop offset="0" stop-color="#d8dbd0" stop-opacity=".55"/><stop offset="1" stop-color="#d8dbd0" stop-opacity="0"/></radialGradient>
<filter id="blur20"><feGaussianBlur stdDeviation="20"/></filter>
</defs>'''


# ------------------------------------------------------------------ A. the rocket on the launch pad
def rocket():
    r = random.Random(7)
    out = [stars(300, 11, 1300), EXTRA]
    cx = 600
    # searchlight beams from the ground
    for x0, x1 in ((120, -250), (1000, 1350), (300, 700), (900, 450)):
        out.append(f'<polygon points="{x0-14},1600 {x0+14},1600 {x1+120},0 {x1-120},0" fill="url(#beam)"/>')

    def half(y):                       # body half-width: wider at the bottom (low camera)
        return lerp(150, 205, (y - 640) / (1430 - 640))
    # side boosters (behind)
    for s in (-1, 1):
        bx = cx + s * 250
        out.append(f'<path d="M{bx-62},1440 L{bx-52},900 Q{bx},790 {bx+52},900 L{bx+62},1440 Z" fill="url(#cyl)" stroke="#000" stroke-width="3"/>')
        for y in range(960, 1420, 110):
            out.append(f'<line x1="{bx-58}" y1="{y}" x2="{bx+58}" y2="{y}" stroke="#000" stroke-width="3" opacity=".7"/>')
        out.append(f'<line x1="{bx+s*0}" y1="920" x2="{bx}" y2="1420" stroke="{LIME}" stroke-width="5" opacity=".8" filter="url(#glow)"/>')
    # core body + ogive nose
    top, base = 640, 1430
    body = (f'M{cx-half(top)},{top} L{cx-half(base)},{base} L{cx+half(base)},{base} L{cx+half(top)},{top} '
            f'C{cx+half(top)},{top-170} {cx+40},{top-250} {cx},{top-300} C{cx-40},{top-250} {cx-half(top)},{top-170} {cx-half(top)},{top} Z')
    out.append(f'<path d="{body}" fill="url(#cyl)" stroke="#000" stroke-width="4"/>')
    out.append(f'<circle cx="{cx}" cy="{top-298}" r="8" fill="{LIME}" filter="url(#glow)"/>')
    # stage rings
    for y in (top, 860, 1110, base - 40):
        hw = half(y)
        out.append(f'<path d="M{cx-hw},{y} Q{cx},{y+22} {cx+hw},{y}" stroke="{LIME}" stroke-width="5" fill="none" opacity=".85" filter="url(#glow)"/>')
    # the 10,000 band
    hw = half(720)
    out.append(f'<path d="M{cx-hw+6},680 Q{cx},700 {cx+hw-6},680 L{cx+hw-4},800 Q{cx},822 {cx-hw+4},800 Z" fill="#0a0b09" stroke="{LIME}" stroke-width="4"/>')
    out.append(text('10,000', cx, 755, 74, LIME, 900, extra='direction="ltr"'))
    out.append(text('مكان للبراندات', cx, 797, 30, '#fff', 800))
    # windows wrapped around the cylinder: rows × visible columns, squeezed toward the edges
    rows, cols = 15, 11
    for i in range(rows):
        y = 735 + i * 22.5 if i < 15 else 0
        y = 890 + i * 36 if y else y
        if 1090 < y < 1135 or y > 1380:
            continue
        hw = half(y)
        for j in range(cols):
            a = -1.25 + 2.5 * j / (cols - 1)
            x = cx + hw * .93 * math.sin(a)
            w = 20 * math.cos(a)
            amber = (i, j) == (5, 7)
            col = AMBER if amber else ('#d6f75a' if r.random() < .05 else '#1d210c')
            out.append(f'<rect x="{x-w/2:.1f}" y="{y+ 6*math.cos(a)*0:.0f}" width="{w:.1f}" height="22" rx="3" fill="{col}" stroke="{LIME}" stroke-opacity="{0 if amber else .5*math.cos(a):.2f}" stroke-width="1.6"/>')
            if amber:
                out.append(f'<circle cx="{x:.0f}" cy="{y+11}" r="55" fill="url(#amberGlow)" opacity=".8"/>'
                           f'<path d="M{x+8:.0f},{y+4} L{x+150:.0f},{y-120} h30" stroke="{AMBER}" stroke-width="3" fill="none"/>'
                           f'<g transform="translate({x+245:.0f},{y-120})"><rect x="-68" y="-30" width="136" height="58" rx="12" fill="#000" stroke="{AMBER}" stroke-width="3"/>'
                           + text('135', 0, 12, 34, AMBER) + '</g>')
    # fins
    for s in (-1, 1):
        out.append(f'<polygon points="{cx+s*half(1260)},1260 {cx+s*(half(1430)+120)},1440 {cx+s*(half(1430)+120)},1500 {cx+s*half(1430)},1440" fill="#1e1f1b" stroke="{LIME}" stroke-width="3"/>')
    # launch tower (left) with the boarding arm
    tx = 175
    out.append(f'<rect x="{tx-55}" y="500" width="110" height="1120" fill="none" stroke="#3a3c36" stroke-width="8"/>')
    for y in range(500, 1620, 62):
        out.append(f'<line x1="{tx-55}" y1="{y}" x2="{tx+55}" y2="{y+62}" stroke="#30322d" stroke-width="5"/>'
                   f'<line x1="{tx+55}" y1="{y}" x2="{tx-55}" y2="{y+62}" stroke="#30322d" stroke-width="5"/>')
    for y in (520, 760, 1000, 1240):
        out.append(f'<circle cx="{tx-55}" cy="{y}" r="7" fill="{LIME}" filter="url(#glow)"/><circle cx="{tx+55}" cy="{y}" r="7" fill="{LIME}" filter="url(#glow)"/>')
    ay = 1250
    out.append(f'<polygon points="{tx+55},{ay-30} {cx-half(ay)},{ay-22} {cx-half(ay)},{ay+22} {tx+55},{ay+30}" fill="#191a17" stroke="{LIME}" stroke-width="4" filter="url(#glow)"/>')
    out.append(f'<rect x="{cx-half(ay)-4}" y="{ay-34}" width="44" height="68" rx="6" fill="{LIME}" filter="url(#glow)"/>')
    for k in range(6):
        x = lerp(tx + 80, cx - half(ay) - 30, k / 5)
        out.append(f'<circle cx="{x:.0f}" cy="{ay}" r="5" fill="#fff" opacity=".9"/>')
    # engine glow + steam rolling out at the base
    out.append(f'<ellipse cx="{cx}" cy="1500" rx="330" ry="90" fill="url(#limeGlow)" opacity=".9"/>')
    for _ in range(26):
        x, y, rr = r.uniform(-60, W + 60), r.uniform(1460, 1640), r.uniform(90, 200)
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rr:.0f}" fill="url(#smoke)" opacity="{r.uniform(.6, 1):.2f}"/>')
    out.append('<linearGradient id="gnd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#030303" stop-opacity="0"/><stop offset=".3" stop-color="#030303" stop-opacity=".9"/><stop offset="1" stop-color="#030303"/></linearGradient>'
               f'<rect x="0" y="1520" width="{W}" height="{H-1520}" fill="url(#gnd)"/>')
    out.append(hud('0', '10,000', 'براندات على السفينة'))
    out.append(caption([('فيها', False), ('عشرة', True), ('آلاف', True), ('مكان.', False)], y=1560))
    out.append(tracker(0, 1730))
    return ''.join(out)


# ------------------------------------------------------------------ B. the starship in flight
def starship():
    r = random.Random(4)
    out = [stars(320, 21), stars(40, 22), EXTRA]
    out.append(f'<circle cx="190" cy="520" r="60" fill="url(#planet)"/><circle cx="190" cy="520" r="60" fill="none" stroke="{LIME}" stroke-opacity=".5" stroke-width="2"/>')
    # small brand shuttles converging on the ship's boarding bay
    for x, y, L in ((930, 1420, 130), (1000, 1270, 90), (820, 1560, 160), (1040, 1500, 80), (700, 1660, 120)):
        out.append(f'<line x1="{x}" y1="{y}" x2="{x+L*.85:.0f}" y2="{y+L*.4:.0f}" stroke="{LIME}" stroke-width="3" opacity=".5"/>'
                   f'<circle cx="{x}" cy="{y}" r="6" fill="{LIME}" filter="url(#glow)"/>')
    g = []
    L = 1120
    top = [(0, -250), (260, -275), (780, -160), (L, 0)]
    bot = [(0, 250), (260, 280), (780, 160), (L, 0)]
    mid = [(0, 30), (260, 28), (780, 14), (L, 0)]
    pts = lambda a: ' '.join(f'{x},{y}' for x, y in a)
    # engine plumes
    for y, w in ((-150, 90), (30, 120), (190, 90)):
        g.append(f'<polygon points="0,{y-w/2} 0,{y+w/2} -620,{y+w*1.4} -620,{y-w*1.4}" fill="url(#trail)" filter="url(#soft)"/>')
    g.append(f'<ellipse cx="-40" cy="30" rx="200" ry="330" fill="url(#limeGlow)" opacity=".75"/>')
    # swept fins (behind the hull)
    g.append(f'<polygon points="120,200 520,150 260,470 60,470" fill="#1a1b18" stroke="{LIME}" stroke-width="4"/>')
    g.append(f'<polygon points="120,-200 470,-170 230,-420 60,-420" fill="#2a2c27" stroke="{LIME}" stroke-width="4"/>')
    g.append(f'<polygon points="{pts(top)} {pts(mid[::-1])}" fill="url(#upper)" stroke="#000" stroke-width="3"/>')
    g.append(f'<polygon points="{pts(mid)} {pts(bot[::-1])}" fill="url(#belly)" stroke="#000" stroke-width="3"/>')
    g.append(f'<clipPath id="upf"><polygon points="{pts(top)} {pts(mid[::-1])}"/></clipPath>')
    # nozzles
    for y in (-150, 30, 190):
        g.append(f'<rect x="-34" y="{y-48}" width="40" height="96" rx="10" fill="#111" stroke="{LIME}" stroke-width="4"/>'
                 f'<ellipse cx="-30" cy="{y}" rx="26" ry="42" fill="#f4ffc4" filter="url(#glow)"/>')
    # upper face: panel lines + many small windows (scale) clipped to the hull
    u = []
    for x in range(80, 900, 90):
        u.append(f'<line x1="{x}" y1="-300" x2="{x}" y2="30" stroke="#000" stroke-width="2" opacity=".45"/>')
    amber_xy = None
    for row in range(8):
        y = -225 + row * 30
        for c in range(60):
            x = 40 + c * 16
            if 560 < x < 800 and -200 < y < -40:       # room for the plate
                continue
            amber = (row, c) == (3, 13)
            col = AMBER if amber else ('#d6f75a' if r.random() < .035 else '#1d210c')
            u.append(f'<rect x="{x}" y="{y}" width="10" height="18" rx="2" fill="{col}" stroke="{LIME}" stroke-opacity="{0 if amber else .45}" stroke-width="1.2"/>')
            if amber:
                u.append(f'<circle cx="{x+5}" cy="{y+9}" r="44" fill="url(#amberGlow)" opacity=".85"/>')
                amber_xy = (x + 5, y + 9)
    g.append(f'<g clip-path="url(#upf)">{"".join(u)}</g>')
    # bridge tower
    g.append(f'<polygon points="120,-262 170,-380 380,-380 440,-268" fill="#3a3c36" stroke="#000" stroke-width="3"/>'
             f'<rect x="190" y="-355" width="170" height="20" rx="4" fill="{LIME}" opacity=".9" filter="url(#glow)"/>'
             f'<line x1="230" y1="-380" x2="230" y2="-480" stroke="#bbb" stroke-width="4"/><circle cx="230" cy="-482" r="7" fill="{LIME}" filter="url(#glow)"/>')
    # light strips
    g.append(f'<polyline points="{pts(mid)}" fill="none" stroke="{LIME}" stroke-width="7" filter="url(#glow)"/>')
    g.append(f'<polyline points="{pts(top)}" fill="none" stroke="{LIME}" stroke-width="3" opacity=".6"/>')
    g.append(f'<polyline points="{pts(bot)}" fill="none" stroke="{LIME}" stroke-width="3" opacity=".35"/>')
    for x in range(40, 1000, 55):
        g.append(f'<circle cx="{x}" cy="{max(30, 230 - x*.21):.0f}" r="4" fill="#fff" opacity=".7"/>')
    # the 10,000 plate
    g.append(f'<polygon points="570,-150 600,-182 780,-150 790,-120 770,-40 580,-40" fill="#0a0b09" stroke="{LIME}" stroke-width="5" filter="url(#glow)"/>')
    g.append(text('10,000', 680, -92, 60, LIME, 900, extra='direction="ltr"'))
    g.append(text('مكان للبراندات', 680, -54, 26, '#fff', 800))
    # boarding bay on the belly, open and lit
    g.append(f'<rect x="440" y="80" width="150" height="60" rx="8" fill="{LIME}" filter="url(#glow)"/><rect x="452" y="90" width="126" height="50" rx="6" fill="#e9ff7a"/>')
    ang, ox, oy = -30, 75, 1310
    out.append(f'<g transform="translate({ox},{oy}) rotate({ang})">{"".join(g)}</g>')
    a = math.radians(ang)
    sx = ox + amber_xy[0] * math.cos(a) - amber_xy[1] * math.sin(a)
    sy = oy + amber_xy[0] * math.sin(a) + amber_xy[1] * math.cos(a)
    out.append(f'<path d="M{sx:.0f},{sy-12:.0f} L{sx+20:.0f},{sy-200:.0f} h40" stroke="{AMBER}" stroke-width="3" fill="none"/>'
               f'<g transform="translate({sx+128:.0f},{sy-200:.0f})"><rect x="-68" y="-30" width="136" height="58" rx="12" fill="#000" stroke="{AMBER}" stroke-width="3"/>'
               + text('135', 0, 12, 34, AMBER) + '</g>')
    out.append(f'<rect width="{W}" height="{H}" fill="url(#vig)" opacity=".7"/>')
    out.append(hud('0', '10,000', 'براندات على السفينة'))
    out.append(caption([('فيها', False), ('عشرة', True), ('آلاف', True), ('مكان.', False)], y=1580))
    out.append(tracker(0, 1740))
    return ''.join(out)


if __name__ == '__main__':
    for name, fn in (('rocket', rocket), ('starship', starship)):
        open(os.path.join(HERE, f'frame_{name}.html'), 'w', encoding='utf-8').write(page(fn()))
    print('ok')
