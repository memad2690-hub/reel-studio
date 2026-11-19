"""Line-by-line ElevenLabs voiceover with word timestamps (Story World episodes).

Each line is generated with /v1/text-to-speech/{voice}/with-timestamps, with the neighbouring lines passed as
previous_text / next_text when the model supports it (so the delivery stays consistent). Character alignment is
turned into word timings. Lines are cached by their full request: re-running costs nothing unless a line changed.
"""
import base64
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request

API = 'https://api.elevenlabs.io/v1'


def key():
    k = os.environ.get('ELEVENLABS_API_KEY')
    if k:
        return k.strip()
    with open(os.path.expanduser('~/.el_key')) as f:
        return f.read().strip()


def _post(url, body, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST',
                                 headers={'xi-api-key': key(), 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def words_from_alignment(al, spoken_text):
    """Characters + start/end times → words (split on spaces). Audio tags like [whispers] are dropped."""
    chars, st, en = al['characters'], al['character_start_times_seconds'], al['character_end_times_seconds']
    words, cur, t0, t1, in_tag = [], '', None, None, False
    for c, a, b in zip(chars, st, en):
        if c == '[':
            in_tag = True
            continue
        if in_tag:
            if c == ']':
                in_tag = False
            continue
        if c.isspace():
            if cur.strip():
                words.append({'text': cur.strip(), 'start': t0, 'end': t1})
            cur, t0 = '', None
            continue
        if t0 is None:
            t0 = a
        cur += c
        t1 = b
    if cur.strip():
        words.append({'text': cur.strip(), 'start': t0, 'end': t1})
    return words


def line(text, voice_id, out_dir, model='eleven_v3', settings=None, prev=None, nxt=None, seed=None):
    """Generate (or reuse) one line. Returns {'audio': path, 'words': [...], 'duration': s, 'model': m}."""
    settings = settings or {}
    body = {'text': text, 'model_id': model, 'voice_settings': settings, 'output_format': 'mp3_44100_128'}
    if seed is not None:
        body['seed'] = seed
    ctx = {}
    if prev:
        ctx['previous_text'] = prev
    if nxt:
        ctx['next_text'] = nxt
    h = hashlib.sha1(json.dumps([voice_id, body, ctx], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
    os.makedirs(out_dir, exist_ok=True)
    mp3, js = os.path.join(out_dir, h + '.mp3'), os.path.join(out_dir, h + '.json')
    if os.path.exists(mp3) and os.path.exists(js):
        return json.load(open(js))
    url = f'{API}/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128'
    try:
        r = _post(url, dict(body, **ctx))
        used_ctx = bool(ctx)
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors='replace')[:400]
        if ctx and e.code in (400, 422):                 # model without request stitching: retry without context
            r = _post(url, body)
            used_ctx = False
        else:
            raise RuntimeError(f'ElevenLabs {e.code}: {msg}')
    with open(mp3, 'wb') as f:
        f.write(base64.b64decode(r['audio_base64']))
    al = r.get('normalized_alignment') or r.get('alignment')
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp3],
                               capture_output=True, text=True).stdout.strip() or 0)
    res = {'audio': mp3, 'words': words_from_alignment(r['alignment'], text), 'duration': dur, 'model': model,
           'context_used': used_ctx, 'text': text, 'settings': settings, 'hash': h,
           'alignment_chars': len(al['characters']) if al else 0}
    json.dump(res, open(js, 'w'), ensure_ascii=False, indent=1)
    return res


def trim_silence(src, dst, head=0.04, tail=0.06):
    """Cut leading/trailing silence (keeps a little air); returns the seconds removed at the head."""
    p = subprocess.run(['ffmpeg', '-v', 'info', '-i', src, '-af', 'silencedetect=noise=-45dB:d=0.05', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src],
                               capture_output=True, text=True).stdout.strip())
    starts = [float(x.split('silence_start: ')[1].split()[0]) for x in p.splitlines() if 'silence_start:' in x]
    ends = [float(x.split('silence_end: ')[1].split()[0]) for x in p.splitlines() if 'silence_end:' in x]
    a = ends[0] if starts and starts[0] <= 0.01 and ends else 0.0
    b = starts[-1] if starts and (len(ends) < len(starts) or ends[-1] >= dur - 0.02) else dur
    a, b = max(0.0, a - head), min(dur, b + tail)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-ar', '48000', '-ac', '1', dst],
                   check=True)
    return a, b - a


def takes_for(text, dirs):
    """All cached takes (any dir) of this exact line text, tag stripped in the comparison."""
    import glob
    out = []
    for d in dirs:
        for f in glob.glob(os.path.join(d, '*.json')):
            r = json.load(open(f))
            if r.get('model') != 'eleven_v3':
                continue
            body = r['text'].split('] ', 1)[-1] if r['text'].startswith('[') else r['text']
            if body == text:
                out.append(r)
    return out


def assemble(lines, picks, out_wav, gaps, target=None, max_tempo=1.25):
    """Concatenate the chosen takes (silence-trimmed) with the given gaps, then time-stretch (pitch kept) to fit
    `target` seconds. Returns (words with global times + line id, per-line spans, tempo)."""
    import tempfile
    tmp = tempfile.mkdtemp()
    parts, spans, words, t = [], [], [], 0.0
    for i, (l, r) in enumerate(zip(lines, picks)):
        w = r['words']
        a, b = max(0.0, w[0]['start'] - 0.03), min(r['duration'], w[-1]['end'] + 0.06)
        seg = os.path.join(tmp, f'{i:02d}.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', r['audio'], '-ss', f'{a:.3f}', '-to', f'{b:.3f}',
                        '-ar', '48000', '-ac', '1', seg], check=True)
        if i:
            g = gaps[i - 1]
            sil = os.path.join(tmp, f'g{i:02d}.wav')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono', '-t', f'{g:.3f}', sil], check=True)
            parts.append(sil)
            t += g
        spans.append([t, t + (b - a)])
        for x in w:
            words.append({'text': x['text'], 'start': round(t + x['start'] - a, 4), 'end': round(t + x['end'] - a, 4), 'line': l['id']})
        parts.append(seg)
        t += b - a
    lst = os.path.join(tmp, 'list.txt')
    open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
    raw = os.path.join(tmp, 'raw.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', raw], check=True)
    tempo = 1.0
    if target and t > target:
        tempo = min(max_tempo, t / target)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af', f'atempo={tempo:.4f}', '-ar', '48000', '-ac', '1', out_wav], check=True)
    for x in words:
        x['start'] = round(x['start'] / tempo, 4); x['end'] = round(x['end'] / tempo, 4)
    spans = [[round(a / tempo, 4), round(b / tempo, 4)] for a, b in spans]
    return words, spans, tempo, t
