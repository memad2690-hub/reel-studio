#!/usr/bin/env python3
"""Reel Studio command line. Run `python3 reel.py -h` for commands.

Every command reads and writes plain files in projects/<slug>/ so any assistant
(Claude Code, Codex, a cloud session) can pick up where the last one stopped.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import uuid

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'engine'))
import build as builder  # noqa: E402
import footage  # noqa: E402
from timing import align_script, load_words, map_through_cuts  # noqa: E402

PROJECTS = os.path.join(ROOT, 'projects')
TEMPLATE = os.path.join(ROOT, 'templates', 'project')
LIB = os.path.join(ROOT, 'library')
STAGES = {'A': ['brief', 'script', 'voiceover', 'storyboard', 'final'],
          'B': ['brief', 'roughcut', 'script', 'storyboard', 'final']}


# ------------------------------------------------------------------ helpers
def now():
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec='seconds')


def pdir(slug):
    d = os.path.join(PROJECTS, slug)
    if not os.path.isdir(d):
        sys.exit(f'No project {slug!r} in projects/. Create it with: python3 reel.py new {slug} --mode A')
    return d


def rj(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def wj(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, path)


def project(slug):
    return rj(os.path.join(pdir(slug), 'project.json'))


SLUG_RE = re.compile(r'^[a-z0-9_][a-z0-9_-]*$')


def valid_slug(slug):
    return bool(slug) and bool(SLUG_RE.match(slug))


def used_versions(d, prefix):
    """Version numbers already taken: recorded in versions.json or present on disk (incl. unjoined parts)."""
    vs = rj(os.path.join(d, 'versions.json'), [])
    used = {int(v['id'][len(prefix):]) for v in vs if re.fullmatch(re.escape(prefix) + r'\d+', v['id'])}
    pat = re.compile(re.escape(prefix) + r'(\d{3,})(?:[._]|$)')
    for sub in ('exports', 'storyboard'):
        p = os.path.join(d, sub)
        for f in (os.listdir(p) if os.path.isdir(p) else []):
            m = pat.match(f)
            if m:
                used.add(int(m.group(1)))
    return used


def next_version(d, prefix):
    return f'{prefix}{1 + max(used_versions(d, prefix) or [0]):03d}'


def version_taken(d, vid):
    """True if vid is recorded or its final export already exists (never overwrite an export)."""
    vs = rj(os.path.join(d, 'versions.json'), [])
    return any(v['id'] == vid for v in vs) or os.path.exists(os.path.join(d, 'exports', f'{vid}.mp4'))


def add_version(d, entry):
    vs = rj(os.path.join(d, 'versions.json'), [])
    vs.append(entry)
    wj(os.path.join(d, 'versions.json'), vs)


def log_status(d, line):
    with open(os.path.join(d, 'STATUS.md'), 'a', encoding='utf-8') as f:
        f.write(f'- {now()}: {line}\n')


def node():
    return shutil.which('node') or sys.exit('Node 18+ is required for rendering.')


# ------------------------------------------------------------------ commands
def cmd_new(a):
    if not valid_slug(a.slug):
        sys.exit(f'Bad slug {a.slug!r}: use lowercase letters, digits, "-" or "_" (e.g. {re.sub(r"[^a-z0-9_-]+", "-", a.slug.lower()).strip("-")!r}), '
                 'so the studio can open it.')
    d = os.path.join(PROJECTS, a.slug)
    if os.path.exists(d):
        sys.exit(f'projects/{a.slug} already exists')
    shutil.copytree(TEMPLATE, d)
    for sub in ('audio', 'raw', 'storyboard', 'exports', 'versions', 'references'):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    proj = rj(os.path.join(d, 'project.json'))
    proj.update({'slug': a.slug, 'title': a.title or a.slug, 'mode': a.mode, 'reel_id': a.reel_id or '',
                 'cta_keyword': a.cta or '', 'created': now(), 'stage': 'brief'})
    wj(os.path.join(d, 'project.json'), proj)
    sc = rj(os.path.join(d, 'scenes.json'))
    sc['mode'] = a.mode
    if a.mode == 'B':
        sc['audio'] = 'build/cut_audio.m4a'
    wj(os.path.join(d, 'scenes.json'), sc)
    log_status(d, f'created (mode {a.mode})')
    print(f'projects/{a.slug} created. Next: fill brief.md, then script.md.')


def cmd_build(a):
    d = pdir(a.slug)
    m = builder.build(d)
    out = {'duration': round(m['duration'], 2), 'scenes': [(s['id'], s['start']) for s in m['scenes']],
           'captions': len(m['captions']), 'anchor_misses': m['anchor_misses'], 'audio': m['audio']}
    print(json.dumps(out, ensure_ascii=False))
    if m['anchor_misses']:
        print('WARNING: timing problems: anchors not found (elements fell back to default times) or elements '
              'timed after their scene ends (they would never appear).', file=sys.stderr)
    return m


def stills(d, times, out_dir):
    subprocess.run([node(), os.path.join(ROOT, 'engine', 'render.js'), '--build', os.path.join(d, 'build'),
                    '--stills', out_dir, '--times', ','.join(f'{t:.3f}' for t in times)], check=True)
    return sorted(os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.endswith('.png'))


def sheet(images, labels, out_png, cols=4, thumb_w=360):
    from PIL import Image, ImageDraw, ImageFont
    ims = [Image.open(p).convert('RGB') for p in images]
    tw = thumb_w
    th = int(ims[0].height * tw / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    pad, lab = 16, 44
    W = cols * tw + (cols + 1) * pad
    H = rows * (th + lab) + (rows + 1) * pad
    canvas = Image.new('RGB', (W, H), (30, 30, 30))
    try:
        font = ImageFont.truetype(os.path.join(ROOT, 'fonts', 'Cairo-Variable.ttf'), 24)
    except OSError:
        font = ImageFont.load_default()
    dr = ImageDraw.Draw(canvas)
    for i, (im, label) in enumerate(zip(ims, labels)):
        r, c = divmod(i, cols)
        x, y = pad + c * (tw + pad), pad + r * (th + lab + pad)
        canvas.paste(im.resize((tw, th), Image.LANCZOS), (x, y + lab))
        dr.text((x + 4, y + 6), label, fill=(240, 240, 240), font=font)
    canvas.save(out_png)
    return out_png


def cmd_storyboard(a):
    d = pdir(a.slug)
    m = builder.build(d)
    times = [float(t) for t in a.times.split(',')] if a.times else [s['storyboard_t'] for s in m['scenes']]
    vid = next_version(d, 'sb')
    tmp = os.path.join(d, 'build', 'stills_' + vid)
    shutil.rmtree(tmp, ignore_errors=True)
    imgs = stills(d, times, tmp)
    labels = []
    for t in times:
        sc = next((s for s in m['scenes'] if s['start'] <= t < s['end']), None)
        labels.append(f'{sc["id"] if sc else "?"}  {int(t // 60)}:{t % 60:04.1f}')
    out = os.path.join(d, 'storyboard', f'{vid}.png')
    sheet(imgs, labels, out)
    shutil.copy(os.path.join(d, 'scenes.json'), os.path.join(d, 'versions', f'{vid}.scenes.json'))
    add_version(d, {'id': vid, 'kind': 'storyboard', 'file': f'storyboard/{vid}.png', 'created': now(),
                    'times': times, 'anchor_misses': m['anchor_misses'], 'note': a.note or ''})
    log_status(d, f'storyboard {vid} ({len(times)} frames)')
    print(json.dumps({'version': vid, 'file': out, 'anchor_misses': m['anchor_misses']}, ensure_ascii=False))


def qa(path, mode=None):
    info = footage.probe(path)
    v = next((s for s in info['streams'] if s['codec_type'] == 'video'), {})
    au = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
    num, den = (v.get('r_frame_rate', '0/1').split('/') + ['1'])[:2]
    res = {'width': v.get('width'), 'height': v.get('height'), 'fps': round(int(num) / max(1, int(den)), 2),
           'duration': round(float(info['format']['duration']), 2),
           'mbps': round(int(info['format'].get('bit_rate', 0)) / 1e6, 2), 'audio': bool(au)}
    problems = []
    if (res['width'], res['height']) != (1080, 1920):
        problems.append('not 1080x1920')
    if not au:
        problems.append('no audio stream')
    if mode in builder.MODES and abs(res['fps'] - builder.MODES[mode]['fps']) > 0.01:
        problems.append(f'fps {res["fps"]}, expected {builder.MODES[mode]["fps"]}')
    if au and v.get('duration') and au.get('duration'):
        gap = abs(float(v['duration']) - float(au['duration']))
        if gap > 0.1:
            problems.append(f'audio and video lengths differ by {gap:.2f}s')
    if mode == 'B' and res['mbps'] < 4:
        problems.append('low bitrate for footage')
    res['problems'] = problems
    return res


def cmd_render(a):
    d = pdir(a.slug)
    proj = project(a.slug)
    m = builder.build(d)
    if m['anchor_misses'] and not a.force:
        sys.exit(f'Timing problems: {json.dumps(m["anchor_misses"], ensure_ascii=False)}. Fix scenes.json or pass --force.')
    vid = a.version or next_version(d, 'v')
    if version_taken(d, vid):
        sys.exit(f'{vid} already exists. Every render is a new version: omit --version, or pick an unused one '
                 f'(next free: {next_version(d, "v")}).')
    partial = a.frm is not None or a.to is not None
    name = f'{vid}_part_{float(a.frm or 0):07.2f}.mp4' if partial else f'{vid}.mp4'
    out = os.path.join(d, 'exports', name)
    cmd = [node(), os.path.join(ROOT, 'engine', 'render.js'), '--build', os.path.join(d, 'build'), '--out', out]
    # Parts are rendered silent; join adds the full audio once, so there are no gaps or drift at the joints.
    if m['audio'] and not partial:
        cmd += ['--audio', os.path.join(d, m['audio'])]
    if a.frm is not None:
        cmd += ['--from', str(a.frm)]
    if a.to is not None:
        cmd += ['--to', str(a.to)]
    if a.draft:
        cmd += ['--preset', 'veryfast', '--crf', '22']
    if a.lossless:
        cmd += ['--lossless']
    subprocess.run(cmd, check=True)
    if partial:
        print(json.dumps({'part': out, 'next': f'render the remaining ranges with --version {vid}, then: reel.py join {a.slug} {vid}'}))
        return
    finish_render(d, proj, vid, out, a.note, a.draft)


def finish_render(d, proj, vid, out, note='', draft=False):
    res = qa(out, proj['mode'])
    cs = os.path.join(d, 'exports', f'{vid}_sheet.png')
    footage.contact_sheet(out, cs, cols=8, rows=1, width=200)
    shutil.copy(os.path.join(d, 'scenes.json'), os.path.join(d, 'versions', f'{vid}.scenes.json'))
    add_version(d, {'id': vid, 'kind': 'render', 'file': f'exports/{vid}.mp4', 'sheet': f'exports/{vid}_sheet.png',
                    'created': now(), 'qa': res, 'draft': bool(draft), 'note': note or ''})
    log_status(d, f'render {vid} {res["width"]}x{res["height"]} {res["duration"]}s {"DRAFT" if draft else ""} '
                  f'{"problems: " + ", ".join(res["problems"]) if res["problems"] else "QA ok"}')
    print(json.dumps({'version': vid, 'file': out, 'qa': res}, ensure_ascii=False))


def cmd_join(a):
    d = pdir(a.slug)
    if version_taken(d, a.version):
        sys.exit(f'{a.version} already exists; refusing to overwrite it.')
    exp = os.path.join(d, 'exports')
    parts = sorted((float(m.group(1)), f) for f in os.listdir(exp)
                   if (m := re.fullmatch(re.escape(a.version) + r'_part_([\d.]+)\.mp4', f)))
    if not parts:
        sys.exit('no parts found')
    m = builder.build(d)
    # The parts must tile the whole timeline with no hole or overlap.
    t, problems = 0.0, []
    for start, f in parts:
        if abs(start - t) > 0.05:
            problems.append(f'{f} starts at {start:.2f}s, expected {t:.2f}s')
        t = start + footage.video_duration(os.path.join(exp, f))
    if abs(t - m['duration']) > 0.1:
        problems.append(f'parts end at {t:.2f}s but the reel is {m["duration"]:.2f}s')
    if problems:
        sys.exit('Parts do not cover the reel: ' + '; '.join(problems) + '. Render the missing range with '
                 f'--from/--to --version {a.version}, then join again.')
    os.makedirs(os.path.join(d, 'build'), exist_ok=True)
    lst = os.path.join(d, 'build', 'parts.txt')
    with open(lst, 'w') as f:
        f.writelines(f"file '{os.path.join(exp, p)}'\n" for _, p in parts)
    out = os.path.join(exp, f'{a.version}.mp4')
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst]
    if m['audio']:
        # one continuous audio track for the whole reel (the parts are silent)
        cmd += ['-i', os.path.join(d, m['audio']), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', f'{t:.3f}']
    else:
        cmd += ['-c', 'copy']
    subprocess.run(cmd + ['-movflags', '+faststart', out], check=True)
    for _, p in parts:
        os.remove(os.path.join(exp, p))
    finish_render(d, project(a.slug), a.version, out)


def cmd_qa(a):
    print(json.dumps(qa(a.file), ensure_ascii=False))


# ------------------------------------------------------------------ feedback + approvals
def cmd_note(a):
    d = pdir(a.slug)
    fb = rj(os.path.join(d, 'feedback.json'), [])
    m = rj(os.path.join(d, 'build', 'meta.json'), {'scenes': []})
    scene = next((s['id'] for s in m['scenes'] if a.t is not None and s['start'] <= a.t < s['end']), None) \
        if (a.version or 'v').startswith('v') else None
    note = {'id': uuid.uuid4().hex[:8], 'version': a.version, 't': a.t, 'scene': scene, 'text': a.text,
            'status': 'open', 'created': now(), 'source': 'cli'}
    fb.append(note)
    wj(os.path.join(d, 'feedback.json'), fb)
    print(json.dumps(note, ensure_ascii=False))


def cmd_notes(a):
    d = pdir(a.slug)
    fb = rj(os.path.join(d, 'feedback.json'), [])
    for n in fb:
        if a.all or n['status'] == 'open':
            t = '' if n.get('t') is None else f'@{n["t"]:.1f}s'
            print(f'[{n["id"]}] {n["status"]:8} {n.get("version") or "-":6} {t:9} {n.get("scene") or "":10} {n["text"]}')


def cmd_resolve(a):
    d = pdir(a.slug)
    fb = rj(os.path.join(d, 'feedback.json'), [])
    for n in fb:
        if n['id'] in a.ids:
            n['status'] = 'applied'; n['applied'] = now()
            if a.version:
                n['applied_in'] = a.version
    wj(os.path.join(d, 'feedback.json'), fb)
    print(f'marked applied: {", ".join(a.ids)}')


def approve(d, stage, version=None, by='user'):
    ap = rj(os.path.join(d, 'approvals.json'), {})
    ap[stage] = {'approved': True, 'version': version, 'at': now(), 'by': by}
    wj(os.path.join(d, 'approvals.json'), ap)
    proj = rj(os.path.join(d, 'project.json'))
    stages = STAGES[proj['mode']]
    if stage in stages and stages.index(stage) + 1 < len(stages):
        proj['stage'] = stages[stages.index(stage) + 1]
    elif stage == 'final':
        proj['stage'] = 'done'
    wj(os.path.join(d, 'project.json'), proj)
    log_status(d, f'approved {stage} {version or ""}')
    return ap


def cmd_approve(a):
    d = pdir(a.slug)
    approve(d, a.stage, a.version)
    print(f'{a.stage} approved' + (f' ({a.version})' if a.version else ''))


def cmd_status(a):
    slugs = [a.slug] if a.slug else sorted(s for s in os.listdir(PROJECTS) if os.path.isdir(os.path.join(PROJECTS, s)))
    for s in slugs:
        d = os.path.join(PROJECTS, s)
        p = rj(os.path.join(d, 'project.json'), {})
        if not p:
            continue
        ap = rj(os.path.join(d, 'approvals.json'), {})
        vs = rj(os.path.join(d, 'versions.json'), [])
        fb = [n for n in rj(os.path.join(d, 'feedback.json'), []) if n['status'] == 'open']
        print(f'{s}: mode {p["mode"]} | stage {p.get("stage")} | approved: {", ".join(ap) or "none"} | '
              f'latest: {vs[-1]["id"] if vs else "-"} | open notes: {len(fb)}')


# ------------------------------------------------------------------ voiceover / footage
def cmd_stt(a):
    d = pdir(a.slug)
    cfg = builder.load_config()
    src = os.path.join(d, a.audio) if not os.path.isabs(a.audio) else a.audio
    if not os.path.exists(src):
        sys.exit(f'File not found: {src}')
    footage.api_key(cfg)  # fail early with the fallback message
    tmp = os.path.join(d, 'build'); os.makedirs(tmp, exist_ok=True)
    m4a = footage.extract_audio(src, os.path.join(tmp, 'stt_input.m4a'))
    out = os.path.join(d, a.out)
    words = footage.stt(m4a, out, cfg)
    print(f'{len(words)} words → {a.out}')


def cmd_import_words(a):
    """Normalize a transcript JSON (ElevenLabs flow output or {text,start,end} list) into words.json."""
    d = pdir(a.slug)
    data = rj(a.file)
    if isinstance(data, dict) and 'transcripts' in data:
        data = data['transcripts'][0]
    tmp = os.path.join(d, 'build', 'import.json'); os.makedirs(os.path.dirname(tmp), exist_ok=True)
    wj(tmp, data)
    words = load_words(tmp)
    wj(os.path.join(d, a.out), words)
    print(f'{len(words)} words → {a.out}')


def cmd_probe(a):
    d = pdir(a.slug)
    raw = os.path.join(d, a.raw)
    info = footage.probe(raw)
    os.makedirs(os.path.join(d, 'build'), exist_ok=True)
    sheet_png = footage.contact_sheet(raw, os.path.join(d, 'build', 'raw_sheet.png'))
    print(json.dumps({'probe': info, 'contact_sheet': sheet_png}, ensure_ascii=False))


def cmd_roughcut(a):
    d = pdir(a.slug)
    raw = os.path.join(d, a.raw)
    os.makedirs(os.path.join(d, 'build'), exist_ok=True)
    words = load_words(os.path.join(d, a.words))
    cuts_path = os.path.join(d, 'cuts.json')
    if a.reuse and os.path.exists(cuts_path):
        segs = rj(cuts_path)['segments']; report = rj(cuts_path).get('report', [])
    else:
        segs, report = footage.propose_cuts(words, footage.duration(raw))
        wj(cuts_path, {'source': a.raw, 'segments': segs, 'report': report, 'created': now(),
                       'note': 'Edit segments by hand if needed, then run: reel.py roughcut <slug> --reuse'})
    vid = next_version(d, 'rc')
    out = os.path.join(d, 'exports', f'{vid}.mp4')
    footage.render_cut(raw, segs, out)
    add_version(d, {'id': vid, 'kind': 'roughcut', 'file': f'exports/{vid}.mp4', 'created': now(),
                    'segments': segs, 'qa': qa(out)})
    log_status(d, f'rough cut {vid}: kept {len(segs)} segments')
    dropped = [r for r in report if not r['kept']]
    print(json.dumps({'version': vid, 'file': out, 'kept_segments': segs, 'dropped': dropped}, ensure_ascii=False, indent=1))


def cmd_finalize_cut(a):
    """After rough-cut approval: map words onto the new timeline, cut final audio and face-card frames from raw."""
    d = pdir(a.slug)
    cuts = rj(os.path.join(d, 'cuts.json'))
    raw = os.path.join(d, cuts['source'])
    segs = footage.snap(cuts['segments'])  # same frame-aligned cuts as the audio and card frames
    words = load_words(os.path.join(d, a.words))
    os.makedirs(os.path.join(d, 'build'), exist_ok=True)
    wj(os.path.join(d, 'words.json'), map_through_cuts(words, segs))
    footage.render_cut(raw, segs, os.path.join(d, 'build', 'cut_audio.m4a'), audio_only=True)
    import grade as grading
    g = grading.project_grade(d)
    gvfs = grading.segment_vfs(g, os.path.join(d, 'build', 'grade'), len(footage.snap(segs))) if g else None
    if a.full_frame:
        # V2 layouts: keep the whole 9:16 frame; the runtime crops/zooms per layout around the face focus
        n = footage.card_frames(raw, segs, os.path.join(d, 'build', 'cf'), crop=None, size=(1080, 1920), grade_vfs=gvfs)
        cuts['card_frames'] = 'full'
    else:
        n = footage.card_frames(raw, segs, os.path.join(d, 'build', 'cf'), crop=a.crop or cuts.get('crop'), grade_vfs=gvfs)
        cuts.pop('card_frames', None)
    cuts['graded'] = {'preset': g['preset'], 'intensity': g.get('intensity', 1.0)} if g else None
    if a.crop:
        cuts['crop'] = a.crop
    wj(os.path.join(d, 'cuts.json'), cuts)
    log_status(d, f'final cut prepared: words.json mapped, {n} card frames')
    print(json.dumps({'words': 'words.json', 'audio': 'build/cut_audio.m4a', 'card_frames': n}))


def cmd_crop_preview(a):
    d = pdir(a.slug)
    cuts = rj(os.path.join(d, 'cuts.json'), {'source': a.raw})
    out = footage.crop_preview(os.path.join(d, cuts['source']), a.crop, os.path.join(d, 'build', 'crop_preview.png'), a.t)
    print(out)


def cmd_align(a):
    d = pdir(a.slug)
    with open(os.path.join(d, a.script), encoding='utf-8') as f:
        txt = '\n'.join(l for l in f.read().splitlines() if not l.lstrip().startswith('#'))
    words = load_words(os.path.join(d, a.words))
    wj(os.path.join(d, 'words.json'), align_script(txt, words))
    print('words.json aligned to the approved script')


# ------------------------------------------------------------------ library
def cmd_plan(a):
    """AI director, first pass: words.json → plan.md / plan.json / scenes.draft.json (never overwrites scenes.json
    unless --apply, which first backs the current one up)."""
    import planner
    d = pdir(a.slug)
    words = load_words(os.path.join(d, 'words.json'))
    if not words:
        sys.exit('no words.json yet (run stt/finalize-cut/align first)')
    proj = project(a.slug)
    pl = planner.plan(words, a.intensity)
    wj(os.path.join(d, 'plan.json'), pl)
    with open(os.path.join(d, 'plan.md'), 'w', encoding='utf-8') as f:
        f.write(planner.plan_markdown(pl, f'— {proj.get("title", a.slug)}'))
    draft = planner.draft_scenes(pl, words, brand=a.brand, cta_keyword=proj.get('cta_keyword'))
    wj(os.path.join(d, 'scenes.draft.json'), draft)
    out = {'segments': len(pl['segments']), 'graphic_scenes': sum(1 for x in pl['segments'] if x['style'] != 'talking-head'),
           'plan': 'plan.md', 'draft': 'scenes.draft.json'}
    if a.apply:
        cur = os.path.join(d, 'scenes.json')
        if os.path.exists(cur):
            bak = os.path.join(d, f'scenes.prev-{dt.datetime.now().strftime("%Y%m%d-%H%M%S")}.json')
            shutil.copy(cur, bak); out['backup'] = os.path.basename(bak)
        clean = json.loads(json.dumps(draft))
        for sc in clean['scenes']:
            sc.pop('_plan', None)
        wj(cur, clean); out['applied'] = True
    log_status(d, f'plan ({a.intensity}): {out["segments"]} segments, {out["graphic_scenes"]} with graphics'
                  + (' — applied to scenes.json' if a.apply else ' — draft only'))
    print(json.dumps(out, ensure_ascii=False))


def cmd_grade(a):
    """Set the project's colour grade (non-destructive: grade.json; presets in grades/ are never modified)."""
    import grade as grading
    d = pdir(a.slug)
    p = os.path.join(d, 'grade.json')
    g = rj(p, {}) or {}
    if a.off:
        g = {'preset': None, 'intensity': 0}
    else:
        if a.preset:
            grading.load_preset(a.preset)
            g['preset'] = a.preset
        g.setdefault('preset', grading.DEFAULT_STYLE09)
        if a.intensity is not None:
            if not 0 <= a.intensity <= 100:
                sys.exit('intensity is 0-100')
            g['intensity'] = a.intensity / 100
        g.setdefault('intensity', 1.0)
        corr = {k: v for k, v in (('exposure', a.exposure), ('temperature', a.temperature), ('tint', a.tint)) if v is not None}
        if corr:
            if a.clip is not None:
                g.setdefault('clips', {}).setdefault(str(a.clip), {}).update(corr)
            else:
                g.setdefault('correction', {}).update(corr)
    wj(p, g)
    log_status(d, f'grade set: {json.dumps(g, ensure_ascii=False)} (re-run finalize-cut to apply)')
    print(json.dumps(g, ensure_ascii=False))


def cmd_grade_preview(a):
    """Before/after frames + checks (+ optional split-screen test MP4) straight from raw, using the cut timeline."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    import grade as grading
    d = pdir(a.slug)
    cuts = rj(os.path.join(d, 'cuts.json'))
    if not cuts:
        sys.exit('no cuts.json')
    g = grading.project_grade(d) or {'preset': a.preset or grading.DEFAULT_STYLE09, 'intensity': 1.0}
    if a.preset:
        g = dict(g, preset=a.preset)
    if a.intensity is not None:
        g = dict(g, intensity=a.intensity / 100)
    raw = os.path.join(d, cuts['source'])
    segs = footage.snap(cuts['segments'])
    out = os.path.join(d, 'build', 'grade'); os.makedirs(out, exist_ok=True)
    vfs = grading.segment_vfs(g, out, len(segs))
    # timeline time → (segment, raw time)
    acc, spans = 0.0, []
    for s0, e0 in segs:
        spans.append((acc, acc + e0 - s0, s0)); acc += e0 - s0
    times = [float(x) for x in a.times.split(',')] if a.times else [sp[0] + (sp[1] - sp[0]) / 2 for sp in spans][:6]
    font = ImageFont.truetype(os.path.join(ROOT, 'fonts', 'Cairo-Variable.ttf'), 34)
    report, sheets = [], []
    for t in times:
        si = next((i for i, sp in enumerate(spans) if sp[0] <= t < sp[1]), len(spans) - 1)
        rt = spans[si][2] + (t - spans[si][0])
        b_png, a_png = os.path.join(out, f'before_{t:06.2f}.png'), os.path.join(out, f'after_{t:06.2f}.png')
        base = ['ffmpeg', '-y', '-v', 'error', '-ss', f'{rt:.3f}', '-i', raw, '-frames:v', '1']
        subprocess.run(base + ['-vf', 'scale=1080:1920', b_png], check=True)
        subprocess.run(base + ['-vf', f'{vfs[si]},scale=1080:1920', a_png], check=True)
        B = np.asarray(Image.open(b_png).convert('RGB'), dtype=np.float32) / 255
        A = np.asarray(Image.open(a_png).convert('RGB'), dtype=np.float32) / 255
        m = grading.metrics(B, A)
        m.update(t=t, segment=si, problems=grading.problems(m))
        report.append(m)
        im = Image.new('RGB', (1080 + 20, 960 + 60), (24, 24, 24))
        im.paste(Image.open(b_png).resize((540, 960)), (0, 60)); im.paste(Image.open(a_png).resize((540, 960)), (560, 60))
        dr = ImageDraw.Draw(im)
        dr.text((10, 8), f'BEFORE  t={t:.1f}s', fill=(255, 255, 255), font=font)
        dr.text((570, 8), f'AFTER  {g["preset"]} {round(g.get("intensity", 1) * 100)}%', fill=(255, 220, 90), font=font)
        sheets.append(im)
    sheet = Image.new('RGB', (sheets[0].width * min(3, len(sheets)), sheets[0].height * ((len(sheets) + 2) // 3)), (24, 24, 24))
    for i, im in enumerate(sheets):
        sheet.paste(im, ((i % 3) * im.width, (i // 3) * im.height))
    cmp_path = os.path.join(out, 'compare.png'); sheet.save(cmp_path)
    lum = [r['mean_luma_after'] for r in report]
    consistency = {'luma_spread': round(max(lum) - min(lum), 3), 'flag': max(lum) - min(lum) > 0.12}
    res = {'grade': g, 'compare': cmp_path, 'frames': report, 'consistency': consistency}
    if a.mp4:
        # 6 s split-screen test: left = original, right = graded (same raw segment)
        si = next((i for i, sp in enumerate(spans) if sp[0] <= times[0] < sp[1]), 0)
        rt = spans[si][2] + (times[0] - spans[si][0])
        mp4 = os.path.join(d, 'exports', f'grade_test_{g["preset"]}_{round(g.get("intensity", 1) * 100)}.mp4')
        fc = (f'[0:v]fps=30,scale=1080:1920,split[o][c];[c]{vfs[si]}[g];[o]crop=540:1920:0:0[l];[g]crop=540:1920:540:0[r];'
              f'[l][r]hstack,drawbox=x=538:y=0:w=4:h=1920:color=white@0.9:t=fill[v]')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{rt:.3f}', '-t', '6', '-i', raw, '-filter_complex', fc,
                        '-map', '[v]', '-map', '0:a?', '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', mp4], check=True)
        res['mp4'] = mp4
    wj(os.path.join(out, 'grade_report.json'), res)
    print(json.dumps({'compare': cmp_path, 'mp4': res.get('mp4'), 'consistency': consistency,
                      'problems': {f'{r["t"]:.1f}s': r['problems'] for r in report if r['problems']}}, ensure_ascii=False))


def cmd_segment(a):
    """Person masks + cut-outs for V2 effects (text behind speaker, parallax, sticker collage). Optional dependency."""
    import segment
    d = pdir(a.slug)
    cf = os.path.join(d, 'build', 'cf')
    if not os.path.isdir(cf):
        sys.exit('no card frames: run finalize-cut --full-frame first')
    ok, why = segment.available()
    if not ok and 'model missing' in why:
        print('downloading segmentation model (≈176 MB, once)…', file=sys.stderr); segment.ensure_model()
    elif not ok:
        sys.exit(why)
    rng = [int(x) for x in a.frames.split('-')] if a.frames else [1, None]
    cuts = rj(os.path.join(d, 'cuts.json'), {}) or {}
    if a.exclude:
        cuts['mask_exclude'] = [[float(v) for v in z.split(',')] for z in a.exclude]
        wj(os.path.join(d, 'cuts.json'), cuts)
    res = segment.masks_for_frames(cf, os.path.join(d, 'build'), every=a.every, first=rng[0], last=rng[1],
                                   exclude=cuts.get('mask_exclude'),
                                   progress=lambda i, n: print(f'\r  {i}/{n}', end='', file=sys.stderr))
    print(file=sys.stderr)
    log_status(d, f'segment: frames {res["frames"]}, mask quality mean {res["quality_mean"]} min {res["quality_min"]}')
    print(json.dumps(res))


def cmd_library(a):
    tech = rj(os.path.join(LIB, 'techniques.json'), [])
    refs = rj(os.path.join(LIB, 'references.json'), [])
    if a.action == 'list':
        for t in tech:
            print(f'{t["id"]:22} [{t["mode"]}] {t["name"]} — {t["purpose"]}')
        print(f'\n{len(refs)} saved references')
        for r in refs:
            print(f'- {r["title"] or r["url"]} ({", ".join(r.get("techniques", []))})')
    elif a.action == 'show':
        t = next((t for t in tech if t['id'] == a.id), None) or sys.exit('unknown technique')
        print(json.dumps(t, ensure_ascii=False, indent=2))
    elif a.action == 'add-ref':
        refs.append({'id': uuid.uuid4().hex[:8], 'url': a.url, 'title': a.title or '', 'creator': a.creator or '',
                     'notes': a.notes or '', 'techniques': [x for x in (a.tech or '').split(',') if x],
                     'analysis': '', 'created': now()})
        wj(os.path.join(LIB, 'references.json'), refs)
        print('reference saved')


def cmd_studio(a):
    cmd = [sys.executable, os.path.join(ROOT, 'studio', 'serve.py')] + (['--port', str(a.port)] if a.port else [])
    if os.name == 'nt':  # exec on Windows detaches the server from the console; run it in the foreground instead
        try:
            sys.exit(subprocess.call(cmd))
        except KeyboardInterrupt:
            sys.exit(0)
    os.execvp(sys.executable, cmd)


def cmd_check(a):
    ok = True
    def line(name, good, hint=''):
        nonlocal ok
        ok &= bool(good) or name.startswith('(optional)')
        print(f'{"OK " if good else "-- "} {name}{"" if good else "  → " + hint}')
    line('python 3.9+', sys.version_info >= (3, 9), 'install Python 3.11+')
    line('ffmpeg + ffprobe', shutil.which('ffmpeg') and shutil.which('ffprobe'), 'install FFmpeg')
    line('node', shutil.which('node'), 'install Node 18+')
    pw = subprocess.run([shutil.which('node') or 'node', '-e', "try{require('playwright')}catch(e){require('./node_modules/playwright')}"],
                        cwd=ROOT, capture_output=True).returncode == 0 if shutil.which('node') else False
    line('playwright (node)', pw, 'npm install && npx playwright install chromium')
    try:
        import PIL  # noqa: F401
        pil = True
    except ImportError:
        pil = False
    line('Pillow (storyboard sheets)', pil, 'pip install Pillow')
    line('Cairo font bundled', os.path.exists(os.path.join(ROOT, 'fonts', 'Cairo-Variable.ttf')), 'restore fonts/')
    el = os.environ.get('ELEVENLABS_API_KEY') or os.path.exists(os.path.expanduser('~/.el_key'))
    line('(optional) ElevenLabs STT key', el, 'only needed for Mode B STT; connector fallback works without it')
    print('\nReady.' if ok else '\nFix the items above, then run this again.')


def main():
    p = argparse.ArgumentParser(description='Reel Studio')
    sp = p.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('new', help='create a project'); s.add_argument('slug'); s.add_argument('--mode', choices='AB', default='A')
    s.add_argument('--title'); s.add_argument('--reel-id'); s.add_argument('--cta'); s.set_defaults(f=cmd_new)
    s = sp.add_parser('build', help='build page.html from scenes.json'); s.add_argument('slug'); s.set_defaults(f=cmd_build)
    s = sp.add_parser('storyboard', help='render key frames into storyboard/sbNNN.png'); s.add_argument('slug')
    s.add_argument('--times'); s.add_argument('--note'); s.set_defaults(f=cmd_storyboard)
    s = sp.add_parser('render', help='render exports/vNNN.mp4'); s.add_argument('slug'); s.add_argument('--from', dest='frm', type=float)
    s.add_argument('--to', type=float); s.add_argument('--version'); s.add_argument('--draft', action='store_true')
    s.add_argument('--lossless', action='store_true', help='Mode A: PNG frames instead of JPEG q95 (about 7x slower)')
    s.add_argument('--force', action='store_true'); s.add_argument('--note'); s.set_defaults(f=cmd_render)
    s = sp.add_parser('join', help='join rendered parts'); s.add_argument('slug'); s.add_argument('version'); s.set_defaults(f=cmd_join)
    s = sp.add_parser('qa', help='check a video file'); s.add_argument('file'); s.set_defaults(f=cmd_qa)
    s = sp.add_parser('note', help='add a timestamped note'); s.add_argument('slug'); s.add_argument('text')
    s.add_argument('--t', type=float); s.add_argument('--version'); s.set_defaults(f=cmd_note)
    s = sp.add_parser('notes', help='list notes'); s.add_argument('slug'); s.add_argument('--all', action='store_true'); s.set_defaults(f=cmd_notes)
    s = sp.add_parser('resolve', help='mark notes applied'); s.add_argument('slug'); s.add_argument('ids', nargs='+')
    s.add_argument('--version'); s.set_defaults(f=cmd_resolve)
    s = sp.add_parser('approve', help='record an approval'); s.add_argument('slug')
    s.add_argument('stage', choices=['brief', 'script', 'voiceover', 'roughcut', 'storyboard', 'final'])
    s.add_argument('--version'); s.set_defaults(f=cmd_approve)
    s = sp.add_parser('status', help='project summary'); s.add_argument('slug', nargs='?'); s.set_defaults(f=cmd_status)
    s = sp.add_parser('stt', help='ElevenLabs STT with word timings'); s.add_argument('slug'); s.add_argument('audio')
    s.add_argument('--out', default='words_raw.json'); s.set_defaults(f=cmd_stt)
    s = sp.add_parser('import-words', help='normalize a transcript JSON'); s.add_argument('slug'); s.add_argument('file')
    s.add_argument('--out', default='words.json'); s.set_defaults(f=cmd_import_words)
    s = sp.add_parser('probe', help='Mode B: probe raw + contact sheet'); s.add_argument('slug'); s.add_argument('--raw', default='raw/raw.mp4')
    s.set_defaults(f=cmd_probe)
    s = sp.add_parser('roughcut', help='Mode B: propose cuts and render a review rough cut'); s.add_argument('slug')
    s.add_argument('--raw', default='raw/raw.mp4'); s.add_argument('--words', default='words_raw.json')
    s.add_argument('--reuse', action='store_true'); s.set_defaults(f=cmd_roughcut)
    s = sp.add_parser('crop-preview', help='Mode B: draw a crop box on a frame'); s.add_argument('slug'); s.add_argument('crop')
    s.add_argument('--t', type=float, default=1.0); s.add_argument('--raw', default='raw/raw.mp4'); s.set_defaults(f=cmd_crop_preview)
    s = sp.add_parser('finalize-cut', help='Mode B: words, audio and card frames for the approved cut'); s.add_argument('slug')
    s.add_argument('--words', default='words_raw.json'); s.add_argument('--crop')
    s.add_argument('--full-frame', action='store_true', help='V2 layouts: full 1080x1920 card frames (cropped live per layout)')
    s.set_defaults(f=cmd_finalize_cut)
    s = sp.add_parser('align', help='Mode B: time an approved clean script'); s.add_argument('slug')
    s.add_argument('--script', default='script_clean.txt'); s.add_argument('--words', default='words.json'); s.set_defaults(f=cmd_align)
    s = sp.add_parser('segment', help='person masks + cut-outs (text behind speaker, parallax, sticker collage)')
    s.add_argument('slug'); s.add_argument('--every', type=int, default=2); s.add_argument('--frames', help='e.g. 1-300')
    s.add_argument('--exclude', action='append', help='zone to drop from the mask, normalised x0,y0,x1,y1 (repeatable; saved in cuts.json)')
    s.set_defaults(f=cmd_segment)
    s = sp.add_parser('grade', help='set the colour grade (preset, intensity 0-100, per-reel or per-clip corrections)')
    s.add_argument('slug'); s.add_argument('--preset'); s.add_argument('--intensity', type=float)
    s.add_argument('--exposure', type=float, help='EV, e.g. 0.2'); s.add_argument('--temperature', type=float)
    s.add_argument('--tint', type=float); s.add_argument('--clip', type=int, help='cut segment index for a per-clip correction')
    s.add_argument('--off', action='store_true'); s.set_defaults(f=cmd_grade)
    s = sp.add_parser('grade-preview', help='before/after frames, clipping/skin/neutral checks, optional test MP4')
    s.add_argument('slug'); s.add_argument('--times'); s.add_argument('--preset'); s.add_argument('--intensity', type=float)
    s.add_argument('--mp4', action='store_true'); s.set_defaults(f=cmd_grade_preview)
    s = sp.add_parser('plan', help='AI director first pass: plan.md + scenes.draft.json from words.json')
    s.add_argument('slug'); s.add_argument('--intensity', choices=['low', 'medium', 'high'], default='medium')
    s.add_argument('--brand', default='media-buying'); s.add_argument('--apply', action='store_true')
    s.set_defaults(f=cmd_plan)
    s = sp.add_parser('library', help='techniques and references'); s.add_argument('action', choices=['list', 'show', 'add-ref'])
    s.add_argument('--id'); s.add_argument('--url'); s.add_argument('--title'); s.add_argument('--creator')
    s.add_argument('--notes'); s.add_argument('--tech'); s.set_defaults(f=cmd_library)
    s = sp.add_parser('studio', help='open the local review studio'); s.add_argument('--port', type=int); s.set_defaults(f=cmd_studio)
    s = sp.add_parser('check', help='check prerequisites'); s.set_defaults(f=cmd_check)
    a = p.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
