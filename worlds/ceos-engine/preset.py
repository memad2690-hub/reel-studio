"""World preset "ceos-engine": المحرّك. Everything is drawn here as SVG, once, in world coordinates.

Isometric projection: world (x, y, z) → screen ((x − y)·cos30, (x + y)·sin30 − z). One world unit = 1 px at zoom 1.
Components carry ids/classes the runtime (world.js) drives: core, grid (dim/lit/single), module, tray, corridor,
drawer 135. Camera shots are named points (cx, cy, zoom) in the same coordinates.
"""
import math

LIME, AMBER, WHITE = '#D1FE17', '#FFB547', '#FFFFFF'
C30, S30 = math.cos(math.pi / 6), 0.5

# geometry (world units)
EX, EY, EH = 1000, 300, 1100          # engine footprint (x, y) and height
GRID_Z0, GRID_Z1 = 160, 1080           # slot grid band on the front face (y = EY)
COLS, ROWS = 100, 100                  # 10,000 slots
MOD = (1230, 40, 300, 240, 520)        # experiment module: x, y, w(x), d(y), h
TRAY = (330, EY, 340, 380)             # tray: x, y, w, depth
COR_Y, COR_X0, COR_STEP = 1650, 1500, 76   # corridor wall plane, first drawer x, spacing
NDRAW = 134


def iso(x, y, z=0):
    return ((x - y) * C30, (x + y) * S30 - z)


def pts(*p):
    return ' '.join(f'{a:.1f},{b:.1f}' for a, b in (iso(*q) for q in p))


def face_matrix(axis, ox, oy, oz):
    """Local (u right, v down) → screen, for a vertical face. axis 'x': face along x (plane y = const)."""
    sx, sy = iso(ox, oy, oz)
    if axis == 'x':
        return f'matrix({C30:.5f},{S30:.5f},0,1,{sx:.2f},{sy:.2f})'
    return f'matrix({-C30:.5f},{S30:.5f},0,1,{sx:.2f},{sy:.2f})'     # along y (plane x = const)


def slot_center(col, row):
    """Screen point of a slot (col 0..99 along x, row 0..99 from the top)."""
    cw = EX / COLS
    rh = (GRID_Z1 - GRID_Z0) / ROWS
    return iso(col * cw + cw / 2, EY, GRID_Z1 - row * rh - rh / 2)


def drawer_center(i):
    """Screen point of drawer i (1..135) on the corridor wall."""
    x = COR_X0 + (i - 1) * COR_STEP + (40 if i == 135 else 0)
    return iso(x + 30, COR_Y, 70 if i < 135 else 95)


YOU_SLOT = (47, 52)                    # the "براندك" slot (col, row)


def defs():
    cw, rh = EX / COLS, (GRID_Z1 - GRID_Z0) / ROWS
    return f'''<defs>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14" result="b"/>
 <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="glow2" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="30"/></filter>
<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3"/></filter>
<pattern id="slotsDim" width="{cw}" height="{rh}" patternUnits="userSpaceOnUse">
 <rect x="1.3" y="1.3" width="{cw-2.6:.2f}" height="{rh-2.6:.2f}" rx="1.2" fill="#1d1f17"/></pattern>
<pattern id="slotsLit" width="{cw}" height="{rh}" patternUnits="userSpaceOnUse">
 <rect x="1.3" y="1.3" width="{cw-2.6:.2f}" height="{rh-2.6:.2f}" rx="1.2" fill="{LIME}"/></pattern>
<radialGradient id="coreGrad"><stop offset="0" stop-color="{LIME}" stop-opacity="1"/><stop offset=".55" stop-color="{LIME}" stop-opacity=".35"/>
 <stop offset="1" stop-color="{LIME}" stop-opacity="0"/></radialGradient>
<radialGradient id="amberGrad"><stop offset="0" stop-color="{AMBER}" stop-opacity=".9"/><stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></radialGradient>
<radialGradient id="vignette" cx=".5" cy=".5" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".85"/></radialGradient>
<clipPath id="gridClip"><rect x="0" y="0" width="{EX}" height="{GRID_Z1-GRID_Z0}"/></clipPath>
</defs>'''


def floor():
    """A faint isometric floor grid so the world has depth."""
    out = []
    for k in range(-6, 40):
        a, b = iso(k * 400, -2400), iso(k * 400, 3600)
        out.append(f'<line x1="{a[0]:.0f}" y1="{a[1]:.0f}" x2="{b[0]:.0f}" y2="{b[1]:.0f}"/>')
    for k in range(-6, 16):
        a, b = iso(-2400, k * 400), iso(16000, k * 400)
        out.append(f'<line x1="{a[0]:.0f}" y1="{a[1]:.0f}" x2="{b[0]:.0f}" y2="{b[1]:.0f}"/>')
    return f'<g stroke="#121410" stroke-width="2">{"".join(out)}</g>'


def box(x, y, w, d, h, fills=('#0d0e0b', '#121410', '#181a14'), edge=LIME, edge_op=.28, cls=''):
    """An isometric box: front (y = y+d), side (x = x+w) and top faces, thin lime edges."""
    f, s, t = fills
    front = pts((x, y + d, 0), (x + w, y + d, 0), (x + w, y + d, h), (x, y + d, h))
    side = pts((x + w, y + d, 0), (x + w, y, 0), (x + w, y, h), (x + w, y + d, h))
    top = pts((x, y, h), (x + w, y, h), (x + w, y + d, h), (x, y + d, h))
    st = f'stroke="{edge}" stroke-opacity="{edge_op}" stroke-width="2" stroke-linejoin="round"'
    return (f'<g class="{cls}"><polygon points="{front}" fill="{f}" {st}/><polygon points="{side}" fill="{s}" {st}/>'
            f'<polygon points="{top}" fill="{t}" {st}/></g>')


def engine():
    out = [box(0, 0, EX, EY, EH, cls='engine')]
    # slot grid on the front face
    m = face_matrix('x', 0, EY, GRID_Z1)
    gh = GRID_Z1 - GRID_Z0
    out.append(f'<g transform="{m}"><rect width="{EX}" height="{gh}" fill="url(#slotsDim)"/>'
               f'<g id="gridLit" opacity="0"><rect id="gridLitRect" width="{EX}" height="{gh}" fill="url(#slotsLit)"/></g>'
               f'<g id="queueSlots"></g>'
               f'<rect x="-6" y="-6" width="{EX+12}" height="{gh+12}" fill="none" stroke="{LIME}" stroke-opacity=".35" stroke-width="3"/></g>')
    # output slot (where ad cards come out) under the grid
    m2 = face_matrix('x', 0, EY, 120)
    out.append(f'<g transform="{m2}"><rect x="{TRAY[0]+20}" y="30" width="{TRAY[2]-40}" height="26" rx="6" fill="#000" '
               f'stroke="{LIME}" stroke-opacity=".6" stroke-width="3"/><rect id="slotGlow" x="{TRAY[0]+20}" y="30" width="{TRAY[2]-40}" '
               f'height="26" rx="6" fill="{LIME}" opacity="0"/></g>')
    # side face: vents + pipe towards the module
    m3 = face_matrix('y', EX, EY, EH - 120)
    vents = ''.join(f'<rect x="{30 + 0}" y="{i*46}" width="{EY-60}" height="16" rx="6" fill="#0a0b08" stroke="{LIME}" stroke-opacity=".18" stroke-width="2"/>'
                    for i in range(12))
    out.append(f'<g transform="{m3}">{vents}</g>')
    # label plate on the front face
    m4 = face_matrix('x', 0, EY, 150)
    out.append(f'<g transform="{m4}"><text x="{EX-20}" y="-8" text-anchor="end" font-size="34" font-weight="900" fill="{LIME}" '
               f'fill-opacity=".75" direction="rtl" font-family="Cairo">المحرّك</text></g>')
    # the core on top (always running)
    cx, cy = iso(EX / 2, EY / 2, EH)
    out.append(f'''<g id="core" transform="translate({cx:.1f},{cy:.1f})">
 <ellipse rx="300" ry="150" fill="url(#coreGrad)" id="coreHalo" opacity=".55"/>
 <ellipse rx="150" ry="75" fill="#0b0c09" stroke="{LIME}" stroke-width="5"/>
 <ellipse id="coreRing" rx="118" ry="59" fill="none" stroke="{LIME}" stroke-width="10" stroke-dasharray="30 22" opacity=".8"/>
 <ellipse id="coreEye" rx="62" ry="31" fill="{LIME}" opacity=".85" filter="url(#glow)"/>
 <ellipse rx="26" ry="13" fill="#fff" opacity=".9"/></g>''')
    return ''.join(out)


def module():
    x, y, w, d, h = MOD
    out = [f'<g id="module">', f'<g id="moduleGlow" opacity="0">'
           f'<ellipse cx="{iso(x+w/2, y+d/2, h/2)[0]:.0f}" cy="{iso(x+w/2, y+d/2, h/2)[1]:.0f}" rx="420" ry="420" fill="url(#coreGrad)"/></g>',
           box(x, y, w, d, h, fills=('#0b0b0a', '#101010', '#151513'), edge_op=.22)]
    # chamber window on the front face
    m = face_matrix('x', x, y + d, h - 90)
    out.append(f'<g transform="{m}"><rect x="40" y="0" width="{w-80}" height="{h-200}" rx="18" fill="#050505" stroke="{LIME}" '
               f'stroke-opacity=".3" stroke-width="3"/><g id="moduleFire" opacity="0">'
               f'<rect x="40" y="0" width="{w-80}" height="{h-200}" rx="18" fill="{LIME}" opacity=".18"/>'
               + ''.join(f'<path d="M{70+k*40},{h-210} q 14,-{90+k%3*40} 0,-{180+k%2*90}" fill="none" stroke="{LIME}" stroke-width="7" '
                         f'stroke-linecap="round" class="flame" style="--k:{k}"/>' for k in range(5)) + '</g></g>')
    # pipe from the engine side to the module
    a, b = iso(EX, EY / 2, 520), iso(x, y + d / 2, 300)
    out.append(f'<path d="M{a[0]:.0f},{a[1]:.0f} L{b[0]:.0f},{b[1]:.0f}" stroke="#1d1f17" stroke-width="26"/>'
               f'<path id="pipeFlow" d="M{a[0]:.0f},{a[1]:.0f} L{b[0]:.0f},{b[1]:.0f}" stroke="{LIME}" stroke-width="6" '
               f'stroke-dasharray="18 26" opacity=".25"/></g>')
    return ''.join(out)


def module_label():
    x, y, w, d, h = MOD
    out = []
    lx, ly = iso(x + w / 2, y + d, h + 40)
    out.append(f'<g id="moduleLabel" transform="translate({lx:.0f},{ly:.0f})"><rect x="-170" y="-58" width="340" height="100" rx="50" '
               f'fill="#0b0b0a" stroke="{LIME}" stroke-opacity=".5" stroke-width="4"/><text y="-6" text-anchor="middle" font-size="60" '
               f'font-weight="900" fill="{WHITE}" direction="rtl" font-family="Cairo" dominant-baseline="middle">التجربة</text></g>')
    return ''.join(out)


def tray():
    x, y, w, dpt = TRAY
    top = pts((x, y, 26), (x + w, y, 26), (x + w, y + dpt, 26), (x, y + dpt, 26))
    front = pts((x, y + dpt, 0), (x + w, y + dpt, 0), (x + w, y + dpt, 26), (x, y + dpt, 26))
    side = pts((x + w, y + dpt, 0), (x + w, y, 0), (x + w, y, 26), (x + w, y + dpt, 26))
    return (f'<g id="tray"><polygon points="{top}" fill="#15170f" stroke="{LIME}" stroke-opacity=".4" stroke-width="2"/>'
            f'<polygon points="{front}" fill="#0c0d09"/><polygon points="{side}" fill="#101109"/><g id="cards"></g></g>')


def corridor():
    out = ['<g id="corridor">']
    # wall + floor strip
    x0, x1 = COR_X0 - 120, COR_X0 + (NDRAW + 2) * COR_STEP + 160
    out.append(f'<polygon points="{pts((x0, COR_Y, 0), (x1, COR_Y, 0), (x1, COR_Y, 260), (x0, COR_Y, 260))}" fill="#0b0c09" '
               f'stroke="{LIME}" stroke-opacity=".18" stroke-width="2"/>')
    out.append(f'<polygon points="{pts((x0, COR_Y, 0), (x1, COR_Y, 0), (x1, COR_Y + 260, 0), (x0, COR_Y + 260, 0))}" fill="#090a07"/>')
    for i in range(1, NDRAW + 1):
        x = COR_X0 + (i - 1) * COR_STEP
        m = face_matrix('x', x, COR_Y, 150)
        out.append(f'<g class="drawer" data-i="{i}" transform="{m}"><rect width="62" height="118" rx="6" fill="#121410" '
                   f'class="dbody"/><rect width="62" height="118" rx="6" fill="none" stroke="{LIME}" stroke-width="3" class="dedge" opacity=".25"/>'
                   f'<rect x="20" y="78" width="22" height="7" rx="3" fill="{LIME}" class="dhandle" opacity=".3"/></g>')
        cx, cy = iso(x + 31, COR_Y, 100)
        out.append(f'<text class="dnum" data-i="{i}" x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" font-size="21" font-weight="800" '
                   f'fill="{LIME}" opacity=".3" font-family="Cairo">{i:03d}</text>')
    # drawer 135: larger, sealed, the only dark one
    x = COR_X0 + NDRAW * COR_STEP + 40
    m = face_matrix('x', x, COR_Y, 210)
    cx, cy = iso(x + 50, COR_Y, 110)
    out.append(f'''<g id="d135">
 <ellipse id="d135Glow" cx="{cx:.0f}" cy="{cy:.0f}" rx="230" ry="230" fill="url(#amberGrad)" opacity="0"/>
 <g transform="{m}"><rect width="100" height="190" rx="8" fill="#050504" stroke="#2a2a22" stroke-width="4"/>
  <rect id="d135Edge" width="100" height="190" rx="8" fill="none" stroke="{AMBER}" stroke-width="4" opacity="0"/>
  <rect x="30" y="120" width="40" height="9" rx="4" fill="#3a3a30"/>
  <g id="d135Lines"></g></g>
 <text x="{cx:.0f}" y="{cy - 30:.0f}" text-anchor="middle" font-size="30" font-weight="900" fill="{AMBER}" opacity=".85" font-family="Cairo">135</text>
 <g id="d135Label" opacity="0" transform="translate({cx:.0f},{cy + 150:.0f})"><rect x="-150" y="-30" width="300" height="56" rx="28" fill="#0b0b0a"
  stroke="{AMBER}" stroke-opacity=".6" stroke-width="2"/><text y="2" text-anchor="middle" dominant-baseline="middle" font-size="26"
  font-weight="800" fill="{WHITE}" direction="rtl" font-family="Cairo"><tspan id="d135LabelText">سطور مكتوبة: 0</tspan></text></g>
</g>''')
    out.append('</g>')
    return ''.join(out)


def svg():
    return defs() + floor() + corridor() + module() + engine() + tray() + module_label()


def shots():
    """Named camera shots: (centre x, centre y, zoom) in screen-world coordinates."""
    ex0, ey0 = iso(0, EY, 0)
    mid = iso(EX / 2, EY / 2, EH / 2)
    you = slot_center(*YOU_SLOT)
    mx = iso(MOD[0] + MOD[2] / 2, MOD[1] + MOD[3], MOD[4] / 2)
    tr = iso(TRAY[0] + TRAY[2] / 2, TRAY[1] + TRAY[3] / 2, 0)
    c0 = drawer_center(1)
    c134 = drawer_center(134)
    d = drawer_center(135)
    return {
        'wide': [500, -190, 0.64],
        'wide_far': [470, -170, 0.58],
        'module': [mx[0] - 60, mx[1] - 80, 1.05],
        'slot': [you[0], you[1], 5.2],
        'slot_tray': [(you[0] + tr[0]) / 2 + 20, you[1] + 300, 1.1],      # slot high-centre, tray above the captions
        'tray': [tr[0] + 60, tr[1] - 160, 1.3],
        'engine_module': [540, -170, 0.62],
        'grid_corridor': [(mid[0] + c0[0]) / 2 + 200, (mid[1] + c0[1]) / 2, 0.55],
        'corridor_start': [c0[0] + 160, c0[1] - 60, 1.25],
        'corridor_end': [c134[0] + 40, c134[1] - 40, 1.25],
        'drawer': [d[0], d[1] + 20, 2.2],
        'drawer_close': [d[0], d[1] + 30, 3.0],
        'drawer_up': [d[0], d[1] + 280 / 2.2, 2.2],                  # drawer high in frame, room for comments below
    }


def anchors():
    """Screen points the runtime needs (bubble targets, card emit point, drawer positions)."""
    sx, sy = iso(TRAY[0] + TRAY[2] / 2, EY, 90)
    return {'you': slot_center(*YOU_SLOT), 'emit': (sx, sy),
            'tray0': iso(TRAY[0] + 60, TRAY[1] + 80, 26), 'tray_dx': iso(40, 0, 0)[0] - iso(0, 0, 0)[0],
            'drawers': {i: drawer_center(i) for i in range(1, 136)},
            'slot_px': [EX / COLS * C30, (GRID_Z1 - GRID_Z0) / ROWS],
            'grid_cols': COLS, 'grid_rows': ROWS}


def slot_rect(col, row):
    """A single slot in face-local coordinates of the grid face (for queue/highlight overlays)."""
    cw, rh = EX / COLS, (GRID_Z1 - GRID_Z0) / ROWS
    return col * cw, row * rh, cw, rh
