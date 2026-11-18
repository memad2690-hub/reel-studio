"""Final audio for a reel: the cut voice track, optionally cleaned, plus restrained sound effects at cue times.

Cues come from scenes.json (element/scene "sfx", or a top-level "sfx" list) and are resolved by build.py.
Sound effects live in library/sfx/<kind>.mp3 (made with ElevenLabs sound generation, kept in the repo).
Writes build/mix_audio.m4a and returns its project-relative path; cached on the inputs.
"""
import hashlib
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_DIR = os.path.join(ROOT, 'library', 'sfx')
# restrained by default: effects sit well under the voice
DEFAULT_GAIN = {'whoosh': -17, 'whoosh2': -17, 'pop': -20, 'pop2': -20, 'impact': -15}
# speech clean-up: rumble/hiss out, gentle denoise, light compression, broadcast loudness
CLEAN = ('highpass=f=80,lowpass=f=13000,afftdn=nf=-30:tn=1,'
         'acompressor=threshold=-21dB:ratio=2.2:attack=10:release=150:makeup=1.5,'
         'loudnorm=I=-15:TP=-1.5:LRA=9')


def available():
    return sorted(f[:-4] for f in os.listdir(SFX_DIR) if f.endswith('.mp3')) if os.path.isdir(SFX_DIR) else []


def mix(pdir, voice, cues, clean=True, out_rel='build/mix_audio.m4a'):
    out = os.path.join(pdir, out_rel)
    cues = sorted((c for c in cues if c['kind'] in available()), key=lambda c: c['t'])
    key = hashlib.sha1(json.dumps([os.path.getmtime(voice), os.path.getsize(voice), cues, clean, CLEAN,
                                   DEFAULT_GAIN]).encode()).hexdigest()
    stamp = out + '.key'
    if os.path.exists(out) and os.path.exists(stamp) and open(stamp).read() == key:
        return out_rel
    cmd = ['ffmpeg', '-y', '-v', 'error', '-i', voice]
    fc = [f'[0:a]{CLEAN if clean else "anull"},aresample=48000[v]']
    labels = ['[v]']
    for i, c in enumerate(cues, start=1):
        cmd += ['-i', os.path.join(SFX_DIR, c['kind'] + '.mp3')]
        ms = max(0, int(round(c['t'] * 1000)))
        g = c.get('gain') if c.get('gain') is not None else DEFAULT_GAIN.get(c['kind'], -18)
        fc.append(f'[{i}:a]aresample=48000,volume={g}dB,adelay={ms}|{ms}[s{i}]')
        labels.append(f'[s{i}]')
    if len(labels) > 1:
        fc.append(f'{"".join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.84[a]')
    else:
        fc.append('[v]anull[a]')
    subprocess.run(cmd + ['-filter_complex', ';'.join(fc), '-map', '[a]', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', out],
                   check=True)
    with open(stamp, 'w') as f:
        f.write(key)
    return out_rel
