"""Story World Engine: build an episode (world preset + episode JSON + voice timing) into a renderable page.

    python3 reel.py episode episodes/ep001.json            # voice (cached) → timing → build → render → QA
    python3 reel.py episode episodes/ep001.json --build    # build only (page.html + meta.json)

The world is drawn once by worlds/<world>/preset.py (SVG, world coordinates) and driven by worlds/<world>/world.js.
Every event in the episode is anchored to a spoken word: {"at": "word"} or {"at": {"word": "w", "nth": 2}} within its
line, or "start"/"end" of the line, plus an optional "offset". No hardcoded seconds.
"""
import importlib.util
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1080, 1920, 30


def load_preset(name):
    p = os.path.join(ROOT, 'worlds', name, 'preset.py')
    spec = importlib.util.spec_from_file_location(f'world_{name}', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def norm(s):
    s = re.sub(r'[ً-ْـ]', '', s)          # harakat, shadda, tatweel
    return re.sub(r'[^\w]', '', s)


class LineClock:
    """Resolves anchors inside one line's words."""

    def __init__(self, line_id, words, span):
        self.id, self.words, self.span = line_id, words, span

    def at(self, a, offset=0.0):
        if a in (None, 'start'):
            t = self.span[0]
        elif a == 'end':
            t = self.span[1]
        else:
            word, nth, edge = (a, 1, 'start') if isinstance(a, str) else (a['word'], a.get('nth', 1), a.get('edge', 'start'))
            hits = [w for w in self.words if norm(w['text']) == norm(word)] or \
                   [w for w in self.words if norm(word) and norm(word) in norm(w['text'])]
            if len(hits) < nth:
                raise KeyError(f'{self.id}: no word "{word}" (#{nth}) in: ' + ' '.join(w['text'] for w in self.words))
            t = hits[nth - 1][edge]
        return round(t + float(offset or 0), 3)


def build(ep_path, out_dir=None):
    ep = json.load(open(ep_path))
    base = os.path.splitext(ep_path)[0]
    timing = json.load(open(os.path.join(base, 'timing.json')))
    out_dir = out_dir or os.path.join(base, 'build')
    os.makedirs(out_dir, exist_ok=True)
    pre = load_preset(ep['world'])
    words, spans = timing['words'], timing['spans']
    clocks = {}
    for l, sp in zip(ep['lines'], spans):
        clocks[l['id']] = LineClock(l['id'], [w for w in words if w['line'] == l['id']], sp)
    duration = round(spans[-1][1] + float(ep.get('tail', 0.6)), 3)

    events, cams, sfx, caps = [], [], [], []
    for l in ep['lines']:
        ck = clocks[l['id']]
        if l.get('cam'):
            c = l['cam']
            t0 = ck.at(c.get('at', 'start'), c.get('offset', 0))
            dur = c.get('dur')
            if c.get('until'):                            # move lasts until a later word of the line
                dur = round(ck.at(c['until'], c.get('until_offset', 0)) - t0, 3)
            cams.append({'t': t0, 'shot': c['shot'], 'move': c.get('move', 'drift'), 'dur': dur, 'line': l['id']})
            if c.get('move', 'drift') not in ('cut',) and c.get('whoosh', True):
                sfx.append({'t': t0, 'kind': 'swoosh', 'gain': c.get('whoosh_gain'), 'line': l['id'], 'auto': True})
        for e in l.get('events', []):
            e2 = {k: v for k, v in e.items() if k not in ('at', 'offset')}
            e2['t'] = ck.at(e.get('at', 'start'), e.get('offset', 0))
            e2['line'] = l['id']
            if e.get('until'):
                e2['over'] = round(ck.at(e['until'], e.get('until_offset', 0)) - e2['t'], 3)
                e2.pop('until', None)
            events.append(e2)
            if e['do'] == 'tray.emit':                    # one print tick per ad card
                for i in range(e.get('n', 1)):
                    sfx.append({'t': round(e2['t'] + i * e.get('interval', .2), 3), 'kind': 'tick', 'gain': None, 'line': l['id'], 'auto': True})
        for s in l.get('sfx', []):
            sfx.append({'t': ck.at(s.get('at', 'start'), s.get('offset', 0)), 'kind': s['kind'], 'gain': s.get('gain'), 'line': l['id']})
        keys = {norm(k) for k in l.get('keys', [])}
        caps.append({'line': l['id'], 'whisper': 'whispers' in (l.get('tag') or ''),
                     'words': [{'text': w['text'], 's': round(w['start'], 3), 'e': round(w['end'], 3), 'key': norm(w['text']) in keys}
                               for w in ck.words]})
    events.sort(key=lambda e: e['t'])
    cams.sort(key=lambda c: c['t'])
    shots = pre.shots()
    for c in cams:
        if isinstance(c['shot'], str):
            if c['shot'] not in shots:
                raise KeyError(f'unknown camera shot "{c["shot"]}" (known: {", ".join(shots)})')
            c['to'] = shots[c['shot']]
        else:
            c['to'] = c['shot']
    data = {'W': W, 'H': H, 'fps': FPS, 'duration': duration, 'events': events, 'cams': cams, 'caps': caps,
            'anchors': pre.anchors(), 'world': ep['world'], 'data': ep.get('data', {}), 'lines': [l['id'] for l in ep['lines']],
            'spans': spans}
    runtime = open(os.path.join(ROOT, 'worlds', ep['world'], 'world.js'), encoding='utf-8').read()
    font = os.path.join(ROOT, 'fonts', 'Cairo-Variable.ttf')
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Cairo;src:url("file://{font}");font-weight:200 1000}}
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:#000}}
#stage{{position:absolute;left:0;top:0;width:{W}px;height:{H}px}}
</style></head><body><svg id="stage" xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Cairo">
<rect width="{W}" height="{H}" fill="#000"/>
<g id="cam"><g id="world">{pre.svg()}<g id="worldFx"></g></g></g>
<g id="dim"><rect width="{W}" height="{H}" fill="#000" opacity="0" id="dimRect"/></g>
<rect width="{W}" height="{H}" fill="url(#vignette)"/>
<g id="hud"></g><g id="screenFx"></g><g id="caps"></g><g id="endcard"></g>
</svg>
<script>window.EP = {json.dumps(data, ensure_ascii=False)};</script>
<script>{runtime}</script></body></html>'''
    open(os.path.join(out_dir, 'page.html'), 'w', encoding='utf-8').write(html)
    bed = dict(ep.get('bed') or {})
    for k in ('duck_from', 'duck_to'):                    # bed ducking anchors: {"line": "L9", "at": "start"}
        if isinstance(bed.get(k), dict):
            bed[k] = clocks[bed[k]['line']].at(bed[k].get('at', 'start'), bed[k].get('offset', 0))
    meta = {'mode': 'W', 'W': W, 'H': H, 'fps': FPS, 'scale': 1, 'duration': duration, 'audio': None, 'sfx': sfx, 'bed': bed,
            'events': len(events), 'cams': len(cams)}
    json.dump(meta, open(os.path.join(out_dir, 'meta.json'), 'w'), ensure_ascii=False, indent=1)
    return out_dir, data, sfx


SFX_WORLD = os.path.join(ROOT, 'library', 'sfx', 'world')
SFX_GAIN = {'swoosh': -24, 'tick': -20, 'clunk': -16, 'ignite': -12, 'drop': -10, 'pulse': -11}


def _norm_sfx(kind, tmp):
    """Peak-normalise a library effect to −1 dBFS (cached next to the build) so gains mean the same for all."""
    src = os.path.join(SFX_WORLD, kind + '.mp3')
    dst = os.path.join(tmp, kind + '.wav')
    if not os.path.exists(dst):
        import subprocess
        mv = subprocess.run(['ffmpeg', '-i', src, '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True).stderr
        peak = float(mv.split('max_volume: ')[1].split(' dB')[0])
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', f'volume={-1 - peak:.2f}dB', '-ar', '48000', '-ac', '1', dst], check=True)
    return dst


def mix(ep_path, build_dir):
    """Voice + ducked hum bed + word-timed effects → build/mix.m4a (−14 LUFS, −1.5 dBTP)."""
    import subprocess
    base = os.path.splitext(ep_path)[0]
    meta = json.load(open(os.path.join(build_dir, 'meta.json')))
    voice = os.path.join(base, 'vo.wav')
    if not os.path.exists(voice):                         # fresh clone: the committed mp3 of the same take
        voice = os.path.join(base, 'vo.mp3')
    tmp = os.path.join(build_dir, 'sfx')
    os.makedirs(tmp, exist_ok=True)
    dur = meta['duration']
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', voice]
    fc, labels, n = [f'[0:a]aresample=48000,apad=whole_dur={dur}[v]'], ['[v]'], 1
    bed = meta.get('bed') or {}
    if bed.get('kind'):
        cmd += ['-stream_loop', '-1', '-i', _norm_sfx(bed['kind'], tmp)]
        g = bed.get('gain', -27)
        a, b, dg = bed.get('duck_from'), bed.get('duck_to'), bed.get('duck_gain', -60)
        vol = f"volume='{10 ** (g / 20):.5f}*if(between(t,{a},{b}),{10 ** ((dg - g) / 20):.6f},1)':eval=frame" if a is not None else f'volume={g}dB'
        fc.append(f'[{n}:a]atrim=0:{dur},asetpts=PTS-STARTPTS,{vol},afade=t=in:d=0.6,afade=t=out:st={dur - 0.8}:d=0.8[b]')
        labels.append('[b]'); n += 1
    for c in meta['sfx']:
        cmd += ['-i', _norm_sfx(c['kind'], tmp)]
        g = c['gain'] if c.get('gain') is not None else SFX_GAIN.get(c['kind'], -18)
        ms = max(0, int(round(c['t'] * 1000)))
        fc.append(f'[{n}:a]volume={g}dB,adelay={ms}|{ms}[s{n}]')
        labels.append(f'[s{n}]'); n += 1
    fc.append(f'{"".join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0,atrim=0:{dur},'
              f'loudnorm=I=-14:TP=-1.5:LRA=11[a]')
    out = os.path.join(build_dir, 'mix.m4a')
    subprocess.run(cmd + ['-filter_complex', ';'.join(fc), '-map', '[a]', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', out], check=True)
    return out
