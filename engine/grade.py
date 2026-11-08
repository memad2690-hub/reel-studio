"""Colour grading for footage only (never the overlays): preset → 3D LUT (+ sharpen, vignette) → FFmpeg filter.

A preset (grades/<id>.json) keeps the original slider values ("source") and the calibration that maps them to visual
equivalents. make_lut() builds a 33³ .cube in Python (numpy) so tone curve, white balance, HSL bands and skin
protection are exact and identical on every FFmpeg; intensity 0–1 blends identity → full grade inside the LUT.
Per-clip corrections (exposure EV, temperature, tint) are applied before the look, per cut segment.

Project grade file: projects/<slug>/grade.json
  {"preset": "RC_Warm_Cinematic_v1", "intensity": 0.85,
   "correction": {"exposure": 0.0, "temperature": 0, "tint": 0},      # whole reel (EV / slider-like units)
   "clips": {"3": {"exposure": 0.15}}}                                   # per cut segment index
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADES = os.path.join(ROOT, 'grades')
DEFAULT_STYLE09 = 'RC_Warm_Cinematic_v1'
BANDS = {'red': (0, 26), 'orange': (30, 18), 'yellow': (60, 24), 'green': (120, 40), 'cyan': (180, 32), 'blue': (235, 40)}


def load_preset(pid):
    for p in (os.path.join(GRADES, f'{pid}.json'), os.path.join(GRADES, 'custom', f'{pid}.json')):
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f)
    raise FileNotFoundError(f'grade preset {pid!r} not found in grades/ or grades/custom/')


def project_grade(pdir):
    """grade.json if present; else the Style 09 default when scenes.json says style "cinematic"; else None."""
    p = os.path.join(pdir, 'grade.json')
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            g = json.load(f)
        return g if g.get('preset') and g.get('intensity', 1) > 0 else None
    sp = os.path.join(pdir, 'scenes.json')
    if os.path.exists(sp):
        with open(sp, encoding='utf-8') as f:
            if json.load(f).get('style') == 'cinematic':
                return {'preset': DEFAULT_STYLE09, 'intensity': 1.0, 'default_for': 'style 09'}
    return None


# ------------------------------------------------------------------ colour math (all on 0..1 gamma-encoded RGB)
def _lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def _srgb(x):
    x = np.clip(x, 0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def _luma(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def _hsv(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    nz = d > 1e-6
    rm = nz & (mx == r); gm = nz & (mx == g) & ~rm; bm = nz & ~rm & ~gm
    h[rm] = ((g - b)[rm] / d[rm]) % 6
    h[gm] = (b - r)[gm] / d[gm] + 2
    h[bm] = (r - g)[bm] / d[bm] + 4
    return h * 60, np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0), mx


def _rgb_from_hsv(h, s, v):
    h = (h % 360) / 60
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    out = np.stack([np.choose(i, [v, q, p, p, t, v]), np.choose(i, [t, v, v, q, p, p]), np.choose(i, [p, p, t, v, v, q])], -1)
    return out


def correct(rgb, exposure=0.0, temperature=0.0, tint=0.0):
    """Per-clip correction before the look: exposure in EV (linear light), white balance in slider-like units."""
    x = rgb
    if exposure:
        x = _srgb(_lin(x) * 2 ** exposure)
    if temperature or tint:
        x = x * np.array([1 + 0.004 * temperature, 1 - 0.002 * tint, 1 - 0.004 * temperature])
    return np.clip(x, 0, 1)


def look(rgb, pre):
    """The preset look. Order: exposure → contrast → highlights roll-off → shadows lift → saturation → warmth → HSL → fade."""
    s, c = pre['source'], pre['calibration']
    b = s['basic']
    x = _srgb(_lin(rgb) * 2 ** (b['exposure'] * c['exposure_ev_per_unit']))
    piv = c['contrast_pivot']
    x = (x - piv) * (1 + b['contrast'] * c['contrast_per_unit']) + piv
    # highlight roll-off on luminance (soft knee; keeps hue), negative slider = compress
    L = np.clip(_luma(x), 1e-6, None)
    k = c['highlights_knee']
    st = max(0.0, -b['highlights']) * c['highlights_strength_per_unit']
    over = np.clip((L - k) / (1 - k), 0, None)
    L2 = np.where(L > k, k + (L - k) * (1 - st * over / (1 + over)), L)
    # shadows: smooth lift that fades out by shadows_range
    r = c['shadows_range']
    u = np.clip(L2 / r, 0, 1)
    L3 = L2 + b['shadows'] * c['shadows_lift_per_unit'] * (1 - u) ** 2 * (u * 4)
    x = x * (L3 / L)[..., None]
    x = np.clip(x, 0, 1)
    # global saturation (luma-preserving), with skin protection applied below through the HSL stage
    h, sat, v = _hsv(x)
    skin = np.exp(-((((h + 180) % 360 - 180) - 22) / 16) ** 2) * np.clip((sat - 0.12) / 0.15, 0, 1) * np.clip((0.75 - sat) / 0.2, 0, 1)
    protect = 1 - c['skin_protect'] * skin
    gs = 1 + b['saturation'] * c['saturation_per_unit'] * protect
    # HSL bands: triangular weights around each band centre
    dh = np.zeros_like(h); ds = np.ones_like(h); dl = np.zeros_like(h)
    for name, (ctr, wid) in BANDS.items():
        adj = s['hsl'].get(name, {})
        if not adj:
            continue
        dist = np.abs(((h - ctr) + 180) % 360 - 180)
        w = np.clip(1 - dist / wid, 0, 1) * np.clip(sat / 0.12, 0, 1)
        prot = protect if name in ('red', 'orange', 'yellow') else 1
        dh += w * adj.get('hue', 0) * c['hsl_hue_deg_per_unit'] * (1 - 0.6 * skin)
        ds *= 1 + w * adj.get('saturation', 0) * c['hsl_sat_per_unit'] * prot
        dl += w * adj.get('lightness', 0) * c['hsl_light_per_unit'] * (1 - 0.5 * skin)
    x = _rgb_from_hsv(h + dh, np.clip(sat * gs * ds, 0, 1), np.clip(v * (1 + dl), 0, 1))
    # warmth/tint (small), then fade (lifted blacks, never crushed)
    x = x * np.array([1 + b['temperature'] * c['temperature_per_unit'],
                      1 - b['tint'] * c['tint_per_unit'],           # CapCut tint −: slightly towards green
                      1 - b['temperature'] * c['temperature_per_unit']])
    f = b['fade'] * c['fade_black_per_unit']
    x = x * (1 - f) + f
    return np.clip(x, 0, 1)


def apply(rgb, pre, intensity=1.0, corr=None):
    base = correct(rgb, **(corr or {}))
    return np.clip(base + (look(base, pre) - base) * intensity, 0, 1)


def make_lut(path, pre, intensity=1.0, corr=None, n=33):
    g = np.linspace(0, 1, n)
    b, gg, r = np.meshgrid(g, g, g, indexing='ij')          # .cube order: red fastest
    rgb = np.stack([r, gg, b], -1).reshape(-1, 3)
    out = apply(rgb, pre, intensity, corr)
    with open(path, 'w') as f:
        f.write(f'TITLE "{pre["id"]} i={intensity:.2f}"\nLUT_3D_SIZE {n}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        f.writelines(f'{a:.6f} {bb:.6f} {cc:.6f}\n' for a, bb, cc in out)
    return path


def vf(pre, lut_path, intensity=1.0):
    """FFmpeg filter chain for the footage: LUT, restrained sharpen, soft vignette (all scaled by intensity)."""
    b, c = pre['source']['basic'], pre['calibration']
    chain = [f"lut3d=file='{lut_path}':interp=tetrahedral"]
    amt = b.get('sharpen', 0) * c['sharpen_amount_per_unit'] * intensity
    if amt > 0.01:
        chain.append(f'unsharp=lx=5:ly=5:la={amt:.3f}:cx=5:cy=5:ca=0')
    ang = b.get('vignette', 0) * c['vignette_angle_per_unit'] * intensity
    if ang > 0.01:
        chain.append(f'vignette=angle={min(ang, 0.9):.3f}:mode=forward')
    return ','.join(chain)


def segment_vfs(g, out_dir, n_segments):
    """One filter chain per cut segment (per-clip corrections differ); LUT files are cached by content."""
    pre = load_preset(g['preset'])
    os.makedirs(out_dir, exist_ok=True)
    base = g.get('correction', {})
    chains, cache = [], {}
    for i in range(n_segments):
        corr = dict(base)
        for k2, v2 in g.get('clips', {}).get(str(i), {}).items():
            corr[k2] = corr.get(k2, 0) + v2
        corr = {k2: float(v2) for k2, v2 in corr.items() if k2 in ('exposure', 'temperature', 'tint') and v2}
        key = json.dumps([g['preset'], round(g.get('intensity', 1), 3), sorted(corr.items())])
        if key not in cache:
            lut = os.path.join(out_dir, f'grade_{len(cache):02d}.cube')
            make_lut(lut, pre, g.get('intensity', 1.0), corr)
            cache[key] = vf(pre, lut, g.get('intensity', 1.0))
        chains.append(cache[key])
    return chains


# ------------------------------------------------------------------ checks
def metrics(before, after, face_box=None):
    """before/after: HxWx3 float arrays (0..1). Returns clipping, crushed shadows, skin shift, neutral drift."""
    out = {}
    out['clip_before'] = float((before.max(-1) >= 0.995).mean() * 100)
    out['clip_after'] = float((after.max(-1) >= 0.995).mean() * 100)
    out['crushed_after'] = float((_luma(after) <= 0.02).mean() * 100)
    out['black_point_after'] = float(np.percentile(_luma(after), 0.5))
    H, W = before.shape[:2]
    y0, y1, x0, x1 = face_box or (int(H * 0.28), int(H * 0.55), int(W * 0.3), int(W * 0.7))
    fb, fa = before[y0:y1, x0:x1].reshape(-1, 3), after[y0:y1, x0:x1].reshape(-1, 3)
    R, G, B = fb[:, 0] * 255, fb[:, 1] * 255, fb[:, 2] * 255
    cb = 128 - 0.168736 * R - 0.331264 * G + 0.5 * B
    cr = 128 + 0.5 * R - 0.418688 * G - 0.081312 * B
    m = (cb > 77) & (cb < 127) & (cr > 133) & (cr < 173) & (fb.max(1) > 0.2)
    out['skin_pixels'] = int(m.sum())
    if m.sum() > 200:
        hb, sb, vb = _hsv(fb[m]); ha, sa, va = _hsv(fa[m])
        out['skin_hue_shift_deg'] = float(np.mean(((ha - hb) + 180) % 360 - 180))
        out['skin_sat_change_pct'] = float((sa.mean() / max(sb.mean(), 1e-6) - 1) * 100)
        out['skin_value_change_pct'] = float((va.mean() / max(vb.mean(), 1e-6) - 1) * 100)
    hb, sb, vb = _hsv(before.reshape(-1, 3))
    neutral = (sb < 0.08) & (vb > 0.6)
    if neutral.sum() > 200:
        na = after.reshape(-1, 3)[neutral]
        out['neutral_cast_after'] = float((na.max(1) - na.min(1)).mean())
    out['mean_luma_after'] = float(_luma(after).mean())
    return out


LIMITS = {'clip_after': 0.5, 'crushed_after': 1.0, 'skin_hue_shift_deg': 4.0, 'skin_sat_change_pct': -25.0,
          'neutral_cast_after': 0.06}


def problems(m):
    p = []
    if m['clip_after'] > LIMITS['clip_after'] and m['clip_after'] > m['clip_before']:
        p.append(f'highlight clipping {m["clip_after"]:.2f}% of pixels')
    if m['crushed_after'] > LIMITS['crushed_after']:
        p.append(f'crushed shadows {m["crushed_after"]:.2f}% of pixels')
    if abs(m.get('skin_hue_shift_deg', 0)) > LIMITS['skin_hue_shift_deg']:
        p.append(f'skin hue shifted {m["skin_hue_shift_deg"]:+.1f}°')
    if m.get('skin_sat_change_pct', 0) < LIMITS['skin_sat_change_pct']:
        p.append(f'skin saturation dropped {m["skin_sat_change_pct"]:.0f}%')
    if m.get('neutral_cast_after', 0) > LIMITS['neutral_cast_after']:
        p.append(f'whites carry a colour cast ({m["neutral_cast_after"]:.3f})')
    return p
