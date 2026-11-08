"""Mode B footage tools: probe, STT, bad-take detection, rough cut, face-card frames."""
import json
import os
import re
import shutil
import subprocess
from difflib import SequenceMatcher

from timing import load_words, map_through_cuts, norm

FPS_B = 30


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                          'stream=codec_type,codec_name,width,height,r_frame_rate,bit_rate,duration:format=duration,bit_rate',
                          '-of', 'json', path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def duration(path):
    return float(probe(path)['format']['duration'])


def video_duration(path):
    v = next((s for s in probe(path)['streams'] if s['codec_type'] == 'video'), {})
    return float(v.get('duration') or duration(path))


def contact_sheet(video, out_png, cols=6, rows=2, width=240):
    d = duration(video)
    n = cols * rows
    run(['ffmpeg', '-y', '-v', 'error', '-i', video, '-vf',
         f'fps={n}/{d:.3f},scale={width}:-1,tile={cols}x{rows}', '-frames:v', '1', out_png])
    return out_png


def extract_audio(video, out_m4a):
    run(['ffmpeg', '-y', '-v', 'error', '-i', video, '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'aac', '-b:a', '64k', out_m4a])
    return out_m4a


def api_key(cfg):
    el = cfg['elevenlabs']
    k = os.environ.get(el['key_env'])
    if k:
        return k.strip()
    p = os.path.expanduser(el['key_file'])
    if os.path.exists(p):
        with open(p) as f:
            return f.read().strip()
    raise SystemExit(f'No ElevenLabs key: set ${el["key_env"]} or save it to {el["key_file"]} (umask 077). '
                     'Fallback: the ElevenLabs connector transcription, or a word-level SRT/JSON from the user.')


def stt(audio_path, out_json, cfg):
    """ElevenLabs Speech-to-Text with word timestamps. The key is read from env/file, never printed."""
    key = api_key(cfg)
    # The header is read from stdin (-H @-), so the key never appears in the process list.
    cmd = ['curl', '-sS', '--fail-with-body', '-X', 'POST', 'https://api.elevenlabs.io/v1/speech-to-text',
           '-H', '@-', '-F', f'model_id={cfg["elevenlabs"]["stt_model"]}',
           '-F', f'language_code={cfg["elevenlabs"]["stt_language"]}', '-F', 'timestamps_granularity=word',
           '-F', f'file=@{audio_path}', '-o', out_json]
    r = subprocess.run(cmd, input='xi-api-key: ' + key + '\n', capture_output=True, text=True)
    if r.returncode != 0:
        msg = (r.stderr or '').replace(key, '***')
        raise SystemExit('STT failed (check allowed domains / key): ' + msg[-400:])
    return load_words(out_json)


def silences(video, noise='-32dB', min_d=0.6):
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', video, '-af', f'silencedetect=noise={noise}:d={min_d}', '-f', 'null', '-'],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r.stderr)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r.stderr)]
    return list(zip(starts, ends + [duration(video)] * (len(starts) - len(ends))))


def sentences(words, gap=0.6):
    """Group words into spoken sentences split at pauses or end punctuation."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt is None or nxt['start'] - w['end'] > gap or w['text'].endswith(('.', '؟', '?', '!')):
            out.append({'start': cur[0]['start'], 'end': cur[-1]['end'], 'text': ' '.join(x['text'] for x in cur)})
            cur = []
    return out


def propose_cuts(words, total, lead=0.12, tail=0.18, sim=0.6):
    """Keep the LAST complete take of repeated sentences; drop false starts. Returns kept segments + report."""
    sents = sentences(words)
    keep = [True] * len(sents)
    reasons = {}
    for i in range(len(sents) - 1):
        a, b = norm(sents[i]['text']), norm(sents[i + 1]['text'])
        if not a:
            continue
        ratio = SequenceMatcher(None, a, b[:len(a) + 10]).ratio()
        if b.startswith(a[:max(4, len(a) // 2)]) or ratio >= sim:
            keep[i] = False; reasons[i] = f'retake (similar to next, {ratio:.2f})'
        elif len(sents[i]['text'].split()) <= 2 and sents[i + 1]['start'] - sents[i]['end'] > 0.4:
            keep[i] = False; reasons[i] = 'false start'
    segs = []
    for i, s in enumerate(sents):
        if keep[i]:
            st, en = max(0.0, s['start'] - lead), min(total, s['end'] + tail)
            if segs and st <= segs[-1][1] + 0.05:
                segs[-1][1] = en
            else:
                segs.append([round(st, 3), round(en, 3)])
    report = [{'start': s['start'], 'end': s['end'], 'text': s['text'], 'kept': keep[i], 'reason': reasons.get(i, '')}
              for i, s in enumerate(sents)]
    return segs, report


def snap(segments, fps=FPS_B):
    """Snap cut points to the output frame grid, so every segment is a whole number of frames and
    audio, video and word timings (map_through_cuts) all use exactly the same cuts."""
    out = []
    for s, e in segments:
        s2, e2 = round(round(s * fps) / fps, 4), round(round(e * fps) / fps, 4)
        if e2 > s2:
            out.append([s2, e2])
    return out


def cut_audio(video, segments, out_path, fade=0.035, codec=('-c:a', 'aac', '-b:a', '192k')):
    """Kept segments of the raw audio with short fades, concatenated (audio only: light on memory)."""
    segments = snap(segments)
    parts = []
    for i, (s, e) in enumerate(segments):
        d = e - s
        parts.append(f'[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d={fade},'
                     f'afade=t=out:st={max(0, d - fade):.3f}:d={fade}[a{i}]')
    fc = ';'.join(parts) + ';' + ''.join(f'[a{i}]' for i in range(len(segments))) + f'concat=n={len(segments)}:v=0:a=1[a]'
    run(['ffmpeg', '-y', '-v', 'error', '-i', video, '-filter_complex', fc, '-map', '[a]', *codec, '-ar', '48000', out_path])
    return out_path


def render_cut(video, segments, out_path, audio_only=False, fade=0.035, fps=FPS_B):
    """Review rough cut (or, with audio_only, the final cut audio).

    Video is cut one segment at a time (seek + exact frame count) and joined without re-encoding, so memory
    stays flat even for 4K footage; the audio is cut once from raw and laid over the whole video."""
    if audio_only:
        return cut_audio(video, segments, out_path, fade)
    segments = snap(segments, fps)
    tmp = out_path + '.parts'
    os.makedirs(tmp, exist_ok=True)
    try:
        names = []
        for i, (s, e) in enumerate(segments):
            n = round((e - s) * fps)
            p = os.path.join(tmp, f'{i:03d}.mp4')
            run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{s:.4f}', '-i', video, '-frames:v', str(n), '-an',
                 '-vf', f'fps={fps},scale=1080:-2:flags=lanczos', '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
                 '-pix_fmt', 'yuv420p', p])
            names.append(p)
        lst = os.path.join(tmp, 'list.txt')
        with open(lst, 'w') as f:
            f.writelines(f"file '{p}'\n" for p in names)
        wav = cut_audio(video, segments, os.path.join(tmp, 'audio.wav'), fade, codec=('-c:a', 'pcm_s16le'))
        total = sum(round((e - s) * fps) for s, e in segments) / fps
        run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-i', wav, '-map', '0:v', '-map', '1:a',
             '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', f'{total:.4f}', '-movflags', '+faststart', out_path])
    finally:
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)
    return out_path


def card_frames(video, segments, out_dir, crop=None, size=(1000, 920), fps=FPS_B, grade_vfs=None):
    """Face-card PNG frames straight from raw (never from the rough cut), one segment at a time:
    seek → exact frame count → crop → scale. Numbered continuously across segments."""
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        if f.endswith('.png'):
            os.remove(os.path.join(out_dir, f))
    w, h = size
    vf = f'fps={fps}' + (f',crop={crop}' if crop else '') + \
         f',scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}'
    k = 1
    for si, (s, e) in enumerate(snap(segments, fps)):
        n = round((e - s) * fps)
        seg_vf = vf if not grade_vfs else vf.replace(f'fps={fps}', f'fps={fps},{grade_vfs[si]}', 1)  # grade the footage only
        run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{s:.4f}', '-i', video, '-frames:v', str(n), '-vf', seg_vf,
             '-start_number', str(k), os.path.join(out_dir, '%05d.png')])
        got = len([f for f in os.listdir(out_dir) if f.endswith('.png')])
        if got < k - 1 + n:  # a short read at the very end of the file: repeat the last frame
            last = os.path.join(out_dir, f'{got:05d}.png')
            for j in range(got + 1, k + n):
                shutil.copy(last, os.path.join(out_dir, f'{j:05d}.png'))
        k += n
    return k - 1


def crop_preview(video, crop, out_png, t=1.0):
    """Frame with the crop rectangle drawn on it, to check framing before extracting frames."""
    w, h, x, y = crop.split(':')
    run(['ffmpeg', '-y', '-v', 'error', '-ss', str(t), '-i', video, '-frames:v', '1', '-vf',
         f'drawbox=x={x}:y={y}:w={w}:h={h}:color=red@0.9:t=8,scale=540:-1', out_png])
    return out_png


__all__ = ['probe', 'duration', 'snap', 'cut_audio', 'video_duration', 'contact_sheet', 'extract_audio', 'stt', 'silences', 'sentences', 'propose_cuts',
           'render_cut', 'card_frames', 'crop_preview', 'map_through_cuts']
