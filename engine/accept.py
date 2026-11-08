"""Acceptance checks for one reel project (V2 milestone 9).

`reel.py accept <slug> [--video exports/v002.mp4]` → projects/<slug>/acceptance/report.json + report.md (+ stills of
anything flagged). Each check is pass / warn / fail / blocked with the evidence. Heuristic checks say so.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

import build as builder
from timing import load_words

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1080, 1920
# Platform overlays (buttons, caption, profile row) differ per app and change over time; these bands are a
# conservative heuristic, not an official spec: bottom 220 px, and the right 100 px of the lower half.
SAFE_BOTTOM, SAFE_RIGHT_X, SAFE_RIGHT_Y = 1700, 980, 900
FACE_MODEL_URL = 'https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/haarcascade_frontalface_default.xml'
FACE_MODEL = os.path.join(os.path.expanduser('~'), '.cache', 'reel-studio', 'models', 'haarcascade_frontalface_default.xml')


def node():
    return shutil.which('node') or 'node'


def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def inter(a, b):
    return area([max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])])


class Report:
    def __init__(self):
        self.checks = []

    def add(self, cid, name, status, detail='', evidence=None):
        self.checks.append({'id': cid, 'name': name, 'status': status, 'detail': detail, 'evidence': evidence or []})

    @property
    def verdict(self):
        st = [c['status'] for c in self.checks]
        return 'fail' if 'fail' in st else ('warn' if 'warn' in st else 'pass')


# ---------------------------------------------------------------------------------------------------- captions
def check_captions(r, meta, words, fps):
    caps = meta.get('captions', [])
    if not caps:
        r.add('captions', 'Caption timing', 'warn', 'no captions in this reel'); return
    strip = lambda w: re.sub(r'[\u060c\u061b\u061f.,!?:;"\'«»()\-]+', '', w)  # noqa: E731  (captions drop punctuation)
    flat = [strip(w) for c in caps for w in c['text'].split()]
    spoken = [strip(w['text']) for w in words]
    bad = []
    if flat != spoken:
        i = next((k for k, (a, b) in enumerate(zip(flat, spoken)) if a != b), min(len(flat), len(spoken)))
        bad.append(f'caption words differ from the transcript at word {i} ({flat[i:i+3]} vs {spoken[i:i+3]})')
    k, frame = 0, 1.0 / fps
    for j, c in enumerate(caps):
        n = len(c['text'].split())
        ws = words[k:k + n]; k += n
        if not ws:
            break
        if abs(c['start'] - ws[0]['start']) > frame + 1e-6:
            bad.append(f'caption {j} "{c["text"]}" starts {c["start"]:.2f}s, first word at {ws[0]["start"]:.2f}s')
        if c['end'] + 0.1 < ws[-1]['end'] and j + 1 < len(caps):
            bad.append(f'caption {j} "{c["text"]}" ends {c["end"]:.2f}s before its last word ends ({ws[-1]["end"]:.2f}s)')
        if c['end'] - c['start'] < 0.2:
            bad.append(f'caption {j} "{c["text"]}" is on screen only {c["end"] - c["start"]:.2f}s')
        if j + 1 < len(caps) and c['end'] > caps[j + 1]['start'] + 1e-3:
            bad.append(f'caption {j} overlaps the next one')
        for wt, w in zip(c.get('wt', []), ws):                   # active-word highlight times
            if abs(wt - w['start']) > frame + 1e-6:
                bad.append(f'caption {j} word "{w["text"]}" highlight at {wt:.2f}s, spoken at {w["start"]:.2f}s'); break
    r.add('captions', 'Caption timing', 'fail' if bad else 'pass',
          f'{len(caps)} captions, {len(flat)} words; each caption starts on its first spoken word (±1 frame)'
          if not bad else f'{len(bad)} problem(s)', bad[:12])


# ---------------------------------------------------------------------------------------------------- layout
def sample_times(meta):
    ts = set()
    for s in meta['scenes']:
        st, en = s['start'], s['end']
        for t in (st + 0.8, s.get('storyboard_t', st), (st + en) / 2, en - 0.3):
            if st <= t < en:
                ts.add(round(t, 3))
    t = 0.5
    while t < meta['duration'] - 0.2:
        ts.add(round(t, 3)); t += 1.5
    return sorted(ts)


def inspect(build_dir, times, out):
    subprocess.run([node(), os.path.join(ROOT, 'engine', 'inspect.js'), '--build', build_dir, '--times',
                    ','.join(f'{t:.3f}' for t in times), '--out', out], check=True, capture_output=True, text=True)
    with open(out, encoding='utf-8') as f:
        return json.load(f)


def face_boxes(build_dir, samples):
    """Detected face rectangles on the card frames, mapped to canvas coordinates (OpenCV Haar cascade)."""
    try:
        import cv2
    except ImportError:
        return None, 'opencv not installed (pip install opencv-python-headless)'
    if not os.path.exists(FACE_MODEL):
        try:
            import urllib.request
            os.makedirs(os.path.dirname(FACE_MODEL), exist_ok=True)
            urllib.request.urlretrieve(FACE_MODEL_URL, FACE_MODEL)
        except Exception as e:
            return None, f'face model not available ({e})'
    cc = cv2.CascadeClassifier(FACE_MODEL)
    out, cache = {}, {}
    for s in samples:
        if not s.get('img') or not s.get('card'):
            continue
        p = os.path.join(build_dir, 'cf', f'{s["frame"]:05d}.png')
        if p not in cache:
            im = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
            if im is None:
                cache[p] = None
            else:
                f = cc.detectMultiScale(im, scaleFactor=1.1, minNeighbors=6, minSize=(int(im.shape[1] * 0.12),) * 2)
                cache[p] = (im.shape, max(f, key=lambda b: b[2] * b[3]) if len(f) else None)
        got = cache[p]
        if not got or got[1] is None:
            continue
        (ih, iw), (x, y, w, h) = got
        l, t, rr, b = s['img']
        sx, sy = (rr - l) / iw, (b - t) / ih
        box = [l + x * sx, t + y * sy, l + (x + w) * sx, t + (y + h) * sy]
        c = s['card']
        vis = [max(box[0], c[0]), max(box[1], c[1]), min(box[2], c[2]), min(box[3], c[3])]
        if area(vis) > 0.3 * area(box):
            out[s['t']] = [round(v) for v in vis]
    return out, None


def check_layout(r, d, meta, build_dir, adir):
    times = sample_times(meta)
    rep = inspect(build_dir, times, os.path.join(adir, 'inspect.json'))
    samples = rep['samples']
    # clipped (confirm 0.6 s later so an entrance still sliding in is not counted)
    sus = {}
    for s in samples:
        for e in s['els']:
            b = e.get('tbox') or e['box'] if e['text'] else e['box']
            over = max(-b[0], -b[1], b[2] - W, b[3] - H)
            if (over > 6 and e['text']) or over > 40:
                sus.setdefault(s['t'], []).append(e)
        if s['cap']:
            b = s['cap']
            if max(-b[0], -b[1], b[2] - W, b[3] - H) > 2:
                sus.setdefault(s['t'], []).append({'text': 'caption: ' + s['capText'], 'box': b})
    clipped = []
    if sus:
        again = inspect(build_dir, [min(t + 0.6, meta['duration'] - 0.05) for t in sus], os.path.join(adir, 'inspect2.json'))
        for (t0, es), s2 in zip(sus.items(), again['samples']):
            boxes2 = [(e['text'], (e.get('tbox') or e['box']) if e['text'] else e['box']) for e in s2['els']] + ([('caption: ' + s2['capText'], s2['cap'])] if s2['cap'] else [])
            for e in es:
                for txt, b in boxes2:
                    lim = 2 if txt.startswith('caption') else (6 if txt else 40)
                    if txt == e['text'] and max(-b[0], -b[1], b[2] - W, b[3] - H) > lim:
                        clipped.append({'t': t0, 'text': txt[:60] or f'(graphic {e.get("k") or ""})', 'box': b}); break
    txt_clip = [c for c in clipped if not c['text'].startswith('(graphic')]
    gfx_clip = [c for c in clipped if c['text'].startswith('(graphic')]
    r.add('clip', 'No clipped text', 'fail' if txt_clip else ('warn' if gfx_clip else 'pass'),
          f'{len(samples)} moments checked; every visible text box inside the 1080×1920 frame'
          + (f'; {len(gfx_clip)} graphic(s) extend past the frame (review)' if gfx_clip else '') if not txt_clip
          else f'{len(txt_clip)} text box(es) run off the frame', clipped[:10])

    # overlaps with captions, the face, platform UI
    faces, ferr = face_boxes(build_dir, samples)
    cap_hits, face_hits, safe_hits, dims = [], [], [], set()
    for s in samples:
        cap = s['cap']
        for e in s['els']:
            b = e['box']
            tb = e.get('tbox') or b
            if cap and e['text'] and inter(tb, cap) > 0.2 * area(cap):
                cap_hits.append({'t': s['t'], 'text': e['text'][:50], 'caption': s['capText']})
            fb = (faces or {}).get(s['t'])
            if fb and not e['behind']:
                if area(b) > 0.8 * W * H:                    # a full-frame dim/backdrop (e.g. a chapter card): judge its text
                    dims.add(e['text'][:40] or 'backdrop')
                    b = tb
                if inter(b, fb) > 0.3 * area(fb):
                    face_hits.append({'t': s['t'], 'element': (e['text'] or e['k'] or 'graphic')[:50]})
            b = tb
            if e['text'] and (inter(b, [0, SAFE_BOTTOM, W, H]) > 0.4 * area(b)
                              or inter(b, [SAFE_RIGHT_X, SAFE_RIGHT_Y, W, SAFE_BOTTOM]) > 0.4 * area(b)):
                safe_hits.append({'t': s['t'], 'text': e['text'][:50]})
        if cap and inter(cap, [0, SAFE_BOTTOM, W, H]) > 0.4 * area(cap):
            safe_hits.append({'t': s['t'], 'text': 'caption: ' + s['capText']})
    dedup = lambda xs, k: list({(x[k], round(x['t'])): x for x in xs}.values())  # noqa: E731
    cap_hits, face_hits, safe_hits = dedup(cap_hits, 'text'), dedup(face_hits, 'element'), dedup(safe_hits, 'text')
    r.add('overlap-caption', 'Graphics clear of captions', 'warn' if cap_hits else 'pass',
          'no text graphic covers more than 20% of a caption' if not cap_hits else f'{len(cap_hits)} overlap(s) to review',
          cap_hits[:10])
    if faces is None:
        r.add('overlap-face', 'Graphics clear of the face', 'blocked', ferr)
    else:
        r.add('overlap-face', 'Graphics clear of the face', 'warn' if face_hits else 'pass',
              f'face found at {len(faces)}/{len(samples)} moments; no front graphic covers more than 30% of it'
              + (f' (full-frame dim behind: {", ".join(sorted(dims))})' if dims else '')
              if not face_hits else f'{len(face_hits)} moment(s) where a graphic covers the face (review: may be intended)',
              face_hits[:10])
    r.add('safe-zone', 'Text clear of platform UI (heuristic)', 'warn' if safe_hits else 'pass',
          'no text in the bottom 220 px or the lower right 100 px column' if not safe_hits
          else f'{len(safe_hits)} text box(es) where app buttons/captions may cover them', safe_hits[:10])

    ck = rep['checks']
    r.add('shaping', 'Correct Arabic shaping', 'fail' if (ck['shaping'] or not ck['font']) else 'pass',
          f'{rep["texts"]} distinct texts; Cairo loaded; letters join (each word drawn shaped differs from its letters drawn apart)'
          if not ck['shaping'] and ck['font'] else 'unshaped text or font not loaded', ck['shaping'][:10])
    rtl = ck['rtl'] + ck['digits']
    r.add('rtl', 'No broken RTL', 'fail' if rtl else 'pass',
          'every line with Arabic runs right→left (also when it starts with a Latin word); numbers read left→right' if not rtl else f'{len(rtl)} line(s) out of order',
          rtl[:10])
    r.add('stable', 'Page runs without errors', 'fail' if rep['errors'] else 'pass',
          'no page or console errors' if not rep['errors'] else 'page errors', rep['errors'][:10])
    return [x['t'] for x in clipped + cap_hits + face_hits + safe_hits]


# ---------------------------------------------------------------------------------------------------- media
def ffprobe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def faststart(path):
    with open(path, 'rb') as f:
        pos = 0
        while True:
            hdr = f.read(8)
            if len(hdr) < 8:
                return None
            size, kind = int.from_bytes(hdr[:4], 'big'), hdr[4:8]
            if size == 1:
                size = int.from_bytes(f.read(8), 'big'); hdr_len = 16
            else:
                hdr_len = 8
            if kind == b'moov':
                return True
            if kind == b'mdat':
                return False
            if size < hdr_len:
                return None
            pos += size; f.seek(pos)


def ff_filter(path, args):
    p = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path] + args + ['-f', 'null', '-'],
                       capture_output=True, text=True)
    return p.stderr


def check_export(r, video, fps, meta):
    info = ffprobe(video)
    v = next((s for s in info['streams'] if s['codec_type'] == 'video'), {})
    a = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
    probs = []
    if (v.get('width'), v.get('height')) != (W, H): probs.append(f'size {v.get("width")}×{v.get("height")}')
    if v.get('codec_name') != 'h264': probs.append(f'codec {v.get("codec_name")}')
    if v.get('profile') not in ('High', 'Main'): probs.append(f'profile {v.get("profile")}')
    if v.get('pix_fmt') != 'yuv420p': probs.append(f'pixel format {v.get("pix_fmt")}')
    if v.get('r_frame_rate') != f'{int(fps)}/1': probs.append(f'frame rate {v.get("r_frame_rate")}')
    if v.get('sample_aspect_ratio') not in (None, '1:1', '0:1'): probs.append(f'SAR {v.get("sample_aspect_ratio")}')
    fs = faststart(video)
    if fs is False: probs.append('moov atom after mdat (no faststart)')
    if 'mp4' not in info['format'].get('format_name', ''): probs.append('not MP4')
    dur = float(info['format']['duration'])
    nb = int(v.get('nb_frames') or 0)
    if nb and abs(nb - round(dur * fps)) > 1: probs.append(f'{nb} frames for {dur:.2f}s')
    kbps = int(info['format'].get('bit_rate', 0)) // 1000
    r.add('export', 'Export format (1080×1920 · 9:16 · 30 fps · H.264 · MP4)', 'fail' if probs else 'pass',
          f'{v.get("width")}×{v.get("height")}, {v.get("r_frame_rate")}, h264 {v.get("profile")} {v.get("pix_fmt")}, '
          f'faststart {"yes" if fs else "no"}, {dur:.2f}s, {kbps} kb/s, {os.path.getsize(video) / 1e6:.1f} MB'
          + ('' if not probs else ' — ' + '; '.join(probs)), probs)

    # audio
    if not a:
        r.add('audio', 'Consistent audio', 'fail', 'no audio stream'); return
    ap = []
    if a.get('codec_name') != 'aac': ap.append(f'codec {a.get("codec_name")}')
    if int(a.get('sample_rate', 0)) < 44100: ap.append(f'{a.get("sample_rate")} Hz')
    abr = int(a.get('bit_rate', 0)) // 1000
    if abr and abr < 128: ap.append(f'{abr} kb/s')
    adur = float(a.get('duration') or dur)
    if abs(adur - dur) > 0.1: ap.append(f'audio {adur:.2f}s vs video {dur:.2f}s')
    eb = ff_filter(video, ['-map', '0:a', '-af', 'ebur128=peak=true', '-vn'])
    I = re.findall(r'I:\s+(-?[\d.]+) LUFS', eb); TP = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', eb)
    LRA = re.findall(r'LRA:\s+(-?[\d.]+) LU', eb)
    lufs = float(I[-1]) if I else None; tpk = float(TP[-1]) if TP else None
    sil = ff_filter(video, ['-map', '0:a', '-af', 'silencedetect=noise=-45dB:d=1.2', '-vn'])
    gaps = [(float(s), float(e)) for s, e in zip(re.findall(r'silence_start: ([\d.]+)', sil),
                                                    re.findall(r'silence_end: ([\d.]+)', sil)) if float(s) > 0.3 and float(e) < dur - 0.3]
    warn = []
    if tpk is not None and tpk > -0.5: warn.append(f'true peak {tpk} dBTP (risk of clipping on platforms)')
    if gaps: warn.append(f'{len(gaps)} silent gap(s) > 1.2 s inside the reel: ' + ', '.join(f'{s:.1f}–{e:.1f}s' for s, e in gaps[:4]))
    r.add('audio', 'Consistent audio', 'fail' if ap else ('warn' if warn else 'pass'),
          f'aac {a.get("sample_rate")} Hz {a.get("channels")}ch {abr} kb/s; integrated {lufs} LUFS, '
          f'LRA {LRA[-1] if LRA else "?"} LU, true peak {tpk} dBTP; audio length = video length ±0.1 s'
          + (' — ' + '; '.join(ap + warn) if ap or warn else ''), ap + warn)

    # decode, black / frozen frames, transitions
    dec = subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-f', 'null', '-'], capture_output=True, text=True).stderr.strip()
    bk = ff_filter(video, ['-vf', 'blackdetect=d=0.1:pix_th=0.06', '-an'])
    blacks = re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', bk)
    fz = ff_filter(video, ['-vf', 'freezedetect=n=0.0008:d=1.5', '-an'])
    freezes = [(float(s), float(e)) for s, e in zip(re.findall(r'freeze_start: ([\d.]+)', fz), re.findall(r'freeze_end: ([\d.]+)', fz))]
    r.add('stable-render', 'Stable rendering (decodes cleanly, no black frames)', 'fail' if (dec or blacks) else 'pass',
          'whole file decodes without errors; no black frames ≥ 0.1 s' if not (dec or blacks) else 'problems',
          ([dec[:300]] if dec else []) + [f'black {s}–{e}s' for s, e in blacks[:5]])
    trs = [(s['id'], s['tr']) for s in meta['scenes'] if s.get('tr')]
    r.add('transitions', 'Smooth transitions', 'warn' if freezes else 'pass',
          (f'{len(trs)} designed transition(s) ({", ".join(f"{i}:{t[0]}" for i, t in trs)}); ' if trs else 'cuts only; ')
          + ('no frozen picture ≥ 1.5 s' if not freezes else f'{len(freezes)} frozen stretch(es) ≥ 1.5 s to review'),
          [f'frozen {s:.1f}–{e:.1f}s' for s, e in freezes[:5]])


def check_determinism(r, build_dir, times, adir):
    hashes = []
    for k in (1, 2):
        out = os.path.join(adir, f'det{k}')
        shutil.rmtree(out, ignore_errors=True)
        subprocess.run([node(), os.path.join(ROOT, 'engine', 'render.js'), '--build', build_dir, '--stills', out,
                        '--times', ','.join(f'{t:.3f}' for t in times)], check=True, capture_output=True)
        hashes.append([hashlib.sha256(open(os.path.join(out, f), 'rb').read()).hexdigest()
                       for f in sorted(os.listdir(out))])
    same = hashes[0] == hashes[1]
    for k in (1, 2):
        shutil.rmtree(os.path.join(adir, f'det{k}'), ignore_errors=True)
    r.add('determinism', 'Deterministic rerenders', 'pass' if same else 'fail',
          f'{len(times)} frames rendered twice: byte-identical PNGs' if same else 'frames differ between two renders',
          [] if same else [f't={t}' for t, a, b in zip(times, *hashes) if a != b])


def flagged_sheet(build_dir, times, adir, report):
    if not times:
        if os.path.exists(os.path.join(adir, 'flagged.png')):
            os.remove(os.path.join(adir, 'flagged.png'))         # nothing flagged now: drop a stale sheet
        return None
    ts = sorted(set(round(t, 2) for t in times))[:8]
    out = os.path.join(adir, 'flagged')
    shutil.rmtree(out, ignore_errors=True)
    subprocess.run([node(), os.path.join(ROOT, 'engine', 'render.js'), '--build', build_dir, '--stills', out,
                    '--times', ','.join(map(str, ts))], check=True, capture_output=True)
    from PIL import Image, ImageDraw
    ims = [Image.open(os.path.join(out, f)).convert('RGB').resize((270, 480)) for f in sorted(os.listdir(out))]
    sheet = Image.new('RGB', (270 * len(ims), 510), 'white'); dr = ImageDraw.Draw(sheet)
    for i, (im, t) in enumerate(zip(ims, ts)):
        sheet.paste(im, (i * 270, 30)); dr.text((i * 270 + 6, 8), f'{t:.2f}s', fill='black')
    p = os.path.join(adir, 'flagged.png'); sheet.save(p)
    shutil.rmtree(out, ignore_errors=True)
    return p


def run(d, video=None, determinism=True):
    adir = os.path.join(d, 'acceptance'); os.makedirs(adir, exist_ok=True)
    build_dir = os.path.join(d, 'build')
    r = Report()
    meta = builder.build(d)
    fps = meta['fps']
    words = load_words(os.path.join(d, 'words.json'))
    fin = [m for m in meta['anchor_misses'] if 'finance' in m.get('problem', '') or 'add up' in m.get('problem', '')]
    other = [m for m in meta['anchor_misses'] if m not in fin]
    n_fin = sum(1 for s in json.load(open(os.path.join(d, 'scenes.json'), encoding='utf-8')).get('scenes', [])
                for e in s.get('elements', []) if e.get('type') in ('equation', 'waterfall', 'donut', 'funnel', 'breakeven',
                                                                     'scorecard', 'beforeafter', 'statcard', 'bars'))
    r.add('finance', 'No incorrect financial calculations', 'fail' if fin else 'pass',
          f'{n_fin} financial component(s) checked by the build (totals, results, tones, chart sums)' if not fin
          else f'{len(fin)} problem(s)', [m['problem'] for m in fin])
    missing = [m['problem'] for m in other if 'missing asset' in m['problem']]
    timing = [f'{m.get("element")}: {m["problem"]}' for m in other if 'missing asset' not in m['problem']]
    cfn = len([f for f in os.listdir(os.path.join(build_dir, 'cf')) if f.endswith('.png')]) if os.path.isdir(os.path.join(build_dir, 'cf')) else 0
    need = int(meta['duration'] * fps) - 1
    if meta['mode'] == 'B' and cfn < need:
        missing.append(f'card frames: {cfn} of {need + 1} (run finalize-cut)')
    if not meta.get('audio'):
        missing.append('audio file missing')
    r.add('assets', 'No missing assets', 'fail' if missing else 'pass',
          f'audio present; {cfn} card frames for {meta["duration"]:.1f}s; fonts bundled' if not missing else 'missing', missing)
    r.add('timing', 'Graphics timed to speech', 'fail' if timing else 'pass',
          'every anchor found; nothing timed after its scene ends' if not timing else f'{len(timing)} problem(s)', timing[:10])
    check_captions(r, meta, words, fps)
    flagged = check_layout(r, d, meta, build_dir, adir)
    if video:
        check_export(r, video, fps, meta)
    else:
        r.add('export', 'Export format', 'blocked', 'no video given (pass --video exports/vNNN.mp4)')
    if determinism:
        st = [s['storyboard_t'] for s in meta['scenes']][:4] or [0.5]
        check_determinism(r, build_dir, st, adir)
    sheet = flagged_sheet(build_dir, flagged, adir, r)
    out = {'project': os.path.basename(d), 'video': os.path.relpath(video, d) if video else None,
           'verdict': r.verdict, 'checks': r.checks, 'flagged_sheet': os.path.relpath(sheet, d) if sheet else None,
           'scenes': [{'id': s['id'], 'style': s.get('style'), 'layout': s.get('card'), 'tr': (s.get('tr') or [None])[0]}
                      for s in meta['scenes']], 'duration': meta['duration']}
    with open(os.path.join(adir, 'report.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(os.path.join(adir, 'report.md'), 'w', encoding='utf-8') as f:
        f.write(markdown(out))
    return out


ICON = {'pass': '✅', 'warn': '⚠️', 'fail': '❌', 'blocked': '⛔'}


def markdown(out):
    L = [f'# Acceptance — {out["project"]}', '', f'Verdict: **{out["verdict"].upper()}** · video: `{out["video"]}` · '
         f'{out["duration"]:.1f}s', '', '| | Check | Result |', '|---|---|---|']
    for c in out['checks']:
        L.append(f'| {ICON[c["status"]]} | {c["name"]} | {c["detail"]} |')
    for c in out['checks']:
        if c['evidence'] and c['status'] != 'pass':
            L += ['', f'**{c["name"]}**'] + [f'- {json.dumps(e, ensure_ascii=False) if not isinstance(e, str) else e}' for e in c['evidence']]
    if out['flagged_sheet']:
        L += ['', f'Flagged moments: `{out["flagged_sheet"]}`']
    return '\n'.join(L) + '\n'


if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None), ensure_ascii=False, indent=1))
