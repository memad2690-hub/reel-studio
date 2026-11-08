"""Person segmentation for parallax / text-behind-speaker / collage cut-outs (optional dependency).

Model: U²-Net human segmentation (rembg release on GitHub), run with onnxruntime on CPU.
    python3 reel.py segment <slug>          # masks for every card frame → build/mask/00001.png …
Masks are 8-bit alpha PNGs at card-frame resolution, temporally smoothed (EMA) to avoid flicker.
quality() scores a mask so callers can fall back (no parallax / no behind-text) when segmentation is poor.
"""
import os
import urllib.request

import numpy as np
from PIL import Image

MODEL_URL = 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx'
MODEL = os.path.join(os.path.expanduser('~'), '.cache', 'reel-studio', 'models', 'u2net_human_seg.onnx')
_sess = None


def available():
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False, 'onnxruntime not installed (pip install onnxruntime)'
    if not os.path.exists(MODEL):
        return False, f'model missing: {MODEL} (reel.py segment downloads it from {MODEL_URL})'
    return True, ''


def ensure_model():
    if not os.path.exists(MODEL):
        os.makedirs(os.path.dirname(MODEL), exist_ok=True)
        tmp = MODEL + '.part'
        urllib.request.urlretrieve(MODEL_URL, tmp)
        os.replace(tmp, MODEL)
    return MODEL


def session():
    global _sess
    if _sess is None:
        import onnxruntime as ort
        o = ort.SessionOptions()
        o.intra_op_num_threads = max(1, os.cpu_count() or 1)
        _sess = ort.InferenceSession(ensure_model(), o, providers=['CPUExecutionProvider'])
    return _sess


def mask(img):
    """PIL RGB image → float mask 0..1 at the image size."""
    s = session()
    w, h = img.size
    x = np.asarray(img.convert('RGB').resize((320, 320), Image.BILINEAR), dtype=np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    out = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    out = (out - out.min()) / max(1e-6, out.max() - out.min())
    m = Image.fromarray((out * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    return np.asarray(m, dtype=np.float32) / 255.0


def refine(m, lo=0.25, hi=0.75, exclude=None):
    """Clean the soft U²-Net output: keep the largest body touching the bottom edge (drops seat/headrest blobs),
    fill enclosed holes (white shirt stripes read as background), then a short soft edge."""
    from scipy import ndimage as ndi
    hard = m > 0.5
    H, W = m.shape
    for x0, y0, x1, y1 in exclude or []:                        # footage-specific zones (e.g. a headrest by the shoulder)
        hard[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)] = False
    # cut thin bridges (e.g. a seat headrest touching the shoulder) before choosing the body
    opened = ndi.binary_opening(hard, structure=np.ones((3, 3)), iterations=7)
    hard = opened if opened.sum() > 0.6 * hard.sum() else hard
    lab, n = ndi.label(hard)
    if n > 1:
        sizes = ndi.sum(hard, lab, range(1, n + 1))
        bottom = set(np.unique(lab[-3:][lab[-3:] > 0]))
        cand = [i + 1 for i in range(n) if (i + 1) in bottom] or list(range(1, n + 1))
        keep = max(cand, key=lambda i: sizes[i - 1])
        hard = lab == keep
    hard = ndi.binary_closing(hard, iterations=6)
    hard = ndi.binary_fill_holes(hard)
    # holes that open only to the bottom edge (torso): fill by closing each row inside the body's span
    soft = np.clip((m - lo) / (hi - lo), 0, 1)
    alpha = np.where(hard, np.maximum(soft, ndi.uniform_filter(hard.astype(np.float32), 9)), soft * 0)
    for x0, y0, x1, y1 in exclude or []:
        alpha[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)] = 0
    return np.clip(ndi.gaussian_filter(alpha, 1.2), 0, 1)


def quality(raw, refined=None):
    """0..1 score from the *raw* model output: how much of the final silhouette the model itself was sure about
    (holes the cleanup had to fill, stray blobs it dropped and unsure edge pixels all lower it). < 0.8 → fall back."""
    from scipy import ndimage as ndi
    refined = refine(raw) if refined is None else refined
    body = refined > 0.5
    area = float(body.mean())
    if area < 0.05:
        return 0.0, {'person_area': round(area, 3)}
    sure = float(((raw > 0.75) & body).sum() / max(1, body.sum()))
    stray = float(((raw > 0.5) & ~body).sum() / max(1, body.sum()))
    edge = body ^ ndi.binary_erosion(body, iterations=3)
    unsure_edge = float(((raw > 0.2) & (raw < 0.8) & edge).sum() / max(1, edge.sum()))
    q = max(0.0, sure - stray - 0.3 * unsure_edge) * (1.0 if 0.08 <= area <= 0.85 else 0.4)
    return round(q, 3), {'sure': round(sure, 3), 'stray': round(stray, 3), 'unsure_edge': round(unsure_edge, 3),
                         'person_area': round(area, 3)}


def cutouts(frame_path, m, cut_path, sticker_path, outline=16):
    """Write the person-only RGBA frame (cut/) and a paper-sticker version with a white outline + soft shadow (sticker/)."""
    from scipy import ndimage as ndi
    im = Image.open(frame_path).convert('RGB')
    a = (m * 255).astype(np.uint8)
    rgba = im.copy(); rgba.putalpha(Image.fromarray(a))
    rgba.save(cut_path, compress_level=1)
    grown = ndi.binary_dilation(m > 0.5, iterations=outline)
    edge = np.clip(ndi.gaussian_filter(grown.astype(np.float32), 1.5), 0, 1)
    shifted = np.zeros_like(grown)
    shifted[14:, 10:] = grown[:-14, :-10]                      # offset without wrap-around (np.roll leaked the bottom edge to the top)
    shadow = np.clip(ndi.gaussian_filter(shifted.astype(np.float32), 8), 0, 1) * 0.35
    H, W = m.shape
    out = np.zeros((H, W, 4), np.float32)
    out[..., 3] = shadow                                       # shadow (black)
    white_a = edge
    out[..., :3] = out[..., :3] * (1 - white_a[..., None]) + white_a[..., None]
    out[..., 3] = np.maximum(out[..., 3], white_a)
    px = np.asarray(im, np.float32) / 255
    out[..., :3] = out[..., :3] * (1 - m[..., None]) + px * m[..., None]
    out[..., 3] = np.maximum(out[..., 3], m)
    Image.fromarray((out * 255).astype(np.uint8), 'RGBA').save(sticker_path, compress_level=1)


def masks_for_frames(frame_dir, build_dir, every=2, ema=0.6, first=1, last=None, progress=None, exclude=None):
    """Mask card frames first..last (1-based), every Nth computed and smoothed (EMA) in between; writes mask/, cut/,
    sticker/ and mask/quality.json {"per_frame": [...]} (frames outside the range get no cut-out → effects fall back)."""
    frames = sorted(f for f in os.listdir(frame_dir) if f.endswith('.png'))
    last = min(last or len(frames), len(frames))
    dirs = {k: os.path.join(build_dir, k) for k in ('mask', 'cut', 'sticker')}
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    qpath = os.path.join(dirs['mask'], 'quality.json')
    try:
        import json
        with open(qpath) as f:
            per = json.load(f)['per_frame']
    except Exception:
        per = []
    per = (per + [0.0] * len(frames))[:len(frames)]
    prev, q = None, 0.0
    for i in range(first - 1, last):
        f = frames[i]
        if (i - first + 1) % every == 0 or prev is None:
            raw = mask(Image.open(os.path.join(frame_dir, f)))
            m = refine(raw, exclude=exclude)
            q = quality(raw, m)[0]
            m = m if prev is None else ema * m + (1 - ema) * prev
        else:
            m = prev
        prev = m
        per[i] = q
        Image.fromarray((m * 255).astype(np.uint8)).save(os.path.join(dirs['mask'], f), compress_level=1)
        cutouts(os.path.join(frame_dir, f), m, os.path.join(dirs['cut'], f), os.path.join(dirs['sticker'], f))
        if progress and (i - first + 1) % 50 == 0:
            progress(i + 1, last)
    import json
    with open(qpath, 'w') as f:
        json.dump({'per_frame': [round(x, 3) for x in per], 'model': os.path.basename(MODEL)}, f)
    done = [x for x in per[first - 1:last]]
    return {'frames': f'{first}-{last}', 'quality_mean': round(float(np.mean(done)), 3) if done else 0,
            'quality_min': round(float(np.min(done)), 3) if done else 0,
            'below_0.62': sum(1 for x in done if x < 0.62)}
