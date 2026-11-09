#!/usr/bin/env python3
"""Local review studio. Binds 127.0.0.1 only; personal use, no login.

GET  /                         the app
GET  /api/projects             project list
GET  /api/project/<slug>       project detail (versions, approvals, notes, scenes, script)
GET  /media/<slug>/<path>      project files (Range supported for video seeking)
GET  /api/library              techniques + references
POST /api/project/<slug>/notes            {version, t, text}
POST /api/project/<slug>/notes/<id>       {status} or {text}
POST /api/project/<slug>/approve          {stage, version}
POST /api/library/references              {url, title, creator, notes, techniques}

Editing (milestone 8; every write backs up the previous file and is logged in edits.json):
GET  /api/project/<slug>/edit             scenes.json + build check + words + pipeline + variants + options
GET  /api/project/<slug>/diff?a=v1&b=v2   what changed between two rendered versions' scenes
POST /api/project/<slug>/edit/scene       {id, patch}
POST /api/project/<slug>/edit/regenerate  {id, intensity}
POST /api/project/<slug>/edit/words       {changes: {index: text}}   spelling fixes only
POST /api/project/<slug>/edit/keyword     {word}
POST /api/project/<slug>/edit/variant     {name}  (save)  ·  /edit/variant/use {name}
POST /api/project/<slug>/run              {cmd, intensity?, confirm_cost?}  allowlisted reel.py jobs, one at a time
GET  /api/jobs/<id>  ·  POST /api/jobs/<id>/cancel

Production (day-to-day use):
POST /api/projects                        {slug, title, cta}  new Mode B project (look 2)
PUT  /api/project/<slug>/upload?name=x    raw footage, streamed to raw/ (never overwrites existing footage)
GET  /api/project/<slug>/previews         fast draft previews (exports/previews)
GET  /api/settings  ·  POST /api/settings/elevenlabs {key}   key status / save key to the local key file (never shown)
"""
import argparse
import json
import mimetypes
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import reel  # noqa: E402
import editor  # noqa: E402  (reel puts engine/ on sys.path)
import build as builder  # noqa: E402

STATIC = os.path.join(ROOT, 'studio', 'static')
PROJECTS = reel.PROJECTS
def safe_slug(slug):
    if not reel.valid_slug(slug) or not os.path.isdir(os.path.join(PROJECTS, slug)):
        return None
    return slug


def inside(base, rel):
    p = os.path.realpath(os.path.join(base, rel))
    return p if p.startswith(os.path.realpath(base) + os.sep) and os.path.isfile(p) else None


def project_detail(slug):
    d = os.path.join(PROJECTS, slug)
    read = lambda f, dflt: reel.rj(os.path.join(d, f), dflt)  # noqa: E731
    txt = {}
    for f in ('brief.md', 'script.md', 'STATUS.md'):
        p = os.path.join(d, f)
        txt[f] = open(p, encoding='utf-8').read() if os.path.exists(p) else ''
    vs = read('versions.json', [])
    for v in vs:
        v['exists'] = os.path.exists(os.path.join(d, v['file']))
    meta = read('build/meta.json', {})
    return {'project': read('project.json', {}), 'versions': vs, 'approvals': read('approvals.json', {}),
            'notes': read('feedback.json', []), 'scenes': meta.get('scenes', []), 'text': txt,
            'stages': reel.STAGES.get(read('project.json', {}).get('mode', 'A'), [])}


def pipeline(d):
    """The production steps and whether each is done (a file or an approval exists). `run` = the job behind the step,
    `hint` = what the user does there."""
    ex = lambda f: os.path.exists(os.path.join(d, f))  # noqa: E731
    proj = reel.rj(os.path.join(d, 'project.json'), {})
    ap = reel.rj(os.path.join(d, 'approvals.json'), {})
    vs = reel.rj(os.path.join(d, 'versions.json'), [])
    spec = reel.rj(os.path.join(d, 'scenes.json'), {}) or {}
    rawd = os.path.join(d, 'raw')
    raw = os.path.isdir(rawd) and any(not f.startswith('.') and not f.endswith('.part') for f in os.listdir(rawd))
    edited = any(sc.get('elements') for sc in spec.get('scenes', []))
    if proj.get('mode') == 'A':
        steps = [('import', 'Script / voice', ex('audio/vo.mp3'), None, 'add audio/vo.mp3'),
                 ('transcribe', 'Transcribe', ex('words.json'), 'stt', 'word timings (ElevenLabs)')]
    else:
        rendered = any(v['kind'] == 'render' for v in vs)
        cf = (os.path.isdir(os.path.join(d, 'build', 'cf')) and not ex('build/cf/.partial') and ex('words.json')) or rendered   # build/ may be cleaned after export
        steps = [('import', 'Upload', raw, None, 'upload the talking-head video'),
                 ('transcribe', 'Transcribe', ex('words_raw.json'), 'stt', 'word timings (uses ElevenLabs credits)'),
                 ('roughcut', 'Rough cut', bool(ap.get('roughcut')), 'roughcut', 'cuts pauses/retakes → approve it in Review'),
                 ('prepare', 'Prepare footage', cf, 'finalize-cut', 'graded card frames + captions timing')]
    steps += [('edit', 'Edit', edited, 'direct', 'Director: Auto / Single / Hybrid, then fine-tune scenes'),
              ('preview', 'Preview', ex('exports/previews/reel.json'), 'preview', 'fast half-size preview (≈3× faster)'),
              ('export', 'Export', any(v['kind'] == 'render' and not v.get('draft') for v in vs), 'export', 'full-quality 1080×1920 MP4'),
              ('final', 'Approve', bool(ap.get('final')), None, 'approve the final in Review, then download')]
    return [{'id': a, 'label': b, 'done': bool(c), 'run': r, 'hint': h} for a, b, c, r, h in steps]


def edit_state(slug):
    d = os.path.join(PROJECTS, slug)
    spec = reel.rj(os.path.join(d, 'scenes.json'), None)
    out = {'spec': spec, 'pipeline': pipeline(d), 'variants': editor.list_variants(d),
           'words': editor.words(d), 'edits': (reel.rj(os.path.join(d, 'edits.json'), []) or [])[-12:],
           'options': {'layouts': list(builder.LAYOUTS), 'styles': builder.STYLE_IDS, 'transitions': list(builder.TRANSITIONS),
                       'captions': list(builder.CAPTION_STYLES)},
           'versions': [v['id'] for v in reel.rj(os.path.join(d, 'versions.json'), []) if v['kind'] == 'render'
                        and os.path.exists(os.path.join(d, 'versions', v['id'] + '.scenes.json'))],
           'plan': [{'t0': x.get('start'), 't1': x.get('end'), 'role': x.get('role'), 'confidence': x.get('confidence')}
                    for x in (reel.rj(os.path.join(d, 'plan.json'), {}) or {}).get('segments', [])]}
    import grade as grading
    proj = reel.rj(os.path.join(d, 'project.json'), {})
    out['look'] = int((spec or {}).get('look', proj.get('look', 1)) or 1)
    out['grade'] = grading.project_grade(d) if proj.get('mode', 'B') == 'B' else None
    out['keys'] = key_status()
    out['previews'] = previews(slug)
    out['director'] = (spec or {}).get('director')
    rawp = (proj.get('raw') or 'raw/raw.mp4')
    out['raw'] = rawp if os.path.exists(os.path.join(d, rawp)) else None
    if spec:
        try:
            out['check'] = editor.check(d)
        except Exception as e:
            out['check'] = {'problems': [{'problem': f'build failed: {e}'}], 'notes': [], 'scenes': []}
    return out


# ---- jobs: allowlisted reel.py commands, one at a time (renders use every core) ----
JOBS, JOB_LOCK = {}, threading.Lock()
COST = {'stt': 'uses ElevenLabs speech-to-text credits'}


def job_args(cmd, slug, data, mode, raw='raw/raw.mp4'):
    I = data.get('intensity') if data.get('intensity') in ('low', 'medium', 'high') else 'medium'
    table = {'build': ['build', slug], 'storyboard': ['storyboard', slug], 'plan': ['plan', slug, '--intensity', I],
             'render-draft': ['render', slug, '--draft'], 'render': ['render', slug], 'segment': ['segment', slug],
             'grade-preview': ['grade-preview', slug], 'finalize-cut': ['finalize-cut', slug, '--full-frame'],
             'card-frames': ['finalize-cut', slug, '--full-frame', '--frames-only'], 'accept': ['accept', slug],
             'roughcut': ['roughcut', slug, '--raw', raw], 'stt': ['stt', slug, 'audio/vo.mp3' if mode == 'A' else raw],
             'preview': ['preview', slug] + (['--scene', str(data['scene'])] if data.get('scene') else []),
             'export': ['render', slug, '--note', 'final export from the studio']}
    if cmd == 'direct':
        director = data.get('director') if data.get('director') in ('auto', 'single', 'hybrid') else 'auto'
        args = ['plan', slug, '--intensity', I, '--director', director, '--apply']
        if director != 'auto':
            args += ['--style', str(data.get('style') or '')]
        if data.get('brand'):
            args += ['--brand', str(data['brand'])]
        return args
    return table.get(cmd)


def start_job(slug, cmd, data):
    d = os.path.join(PROJECTS, slug)
    proj = reel.rj(os.path.join(d, 'project.json'), {})
    mode = proj.get('mode', 'B')
    args = job_args(cmd, slug, data, mode, (proj.get('raw') or 'raw/raw.mp4'))
    if not args:
        raise ValueError(f'unknown job {cmd!r}')
    if cmd in COST and not data.get('confirm_cost'):
        raise ValueError(f'{cmd} {COST[cmd]}: confirm first')
    with JOB_LOCK:
        if any(j['status'] == 'running' for j in JOBS.values()):
            raise ValueError('another job is running; wait for it or cancel it')
        jid = uuid.uuid4().hex[:8]
        os.makedirs(os.path.join(d, 'build', 'jobs'), exist_ok=True)
        log = os.path.join(d, 'build', 'jobs', f'{jid}.log')
        f = open(log, 'w', encoding='utf-8')
        proc = subprocess.Popen([sys.executable, os.path.join(ROOT, 'reel.py')] + args, cwd=ROOT, stdout=f,
                                stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONUNBUFFERED='1', PYTHONIOENCODING='utf-8'))
        JOBS[jid] = {'id': jid, 'slug': slug, 'cmd': cmd, 'args': args, 'status': 'running', 'started': time.time(),
                     'log': log, 'proc': proc, 'fh': f}

    def wait():
        rc = proc.wait(); f.close()
        j = JOBS[jid]
        j.update(status='done' if rc == 0 else ('cancelled' if j.get('cancel') else 'failed'), rc=rc,
                 seconds=round(time.time() - j['started'], 1))
    threading.Thread(target=wait, daemon=True).start()
    return job_view(JOBS[jid])


def job_view(j):
    try:
        with open(j['log'], encoding='utf-8', errors='replace') as f:
            tail = f.read()[-4000:]
    except OSError:
        tail = ''
    return {k: v for k, v in j.items() if k not in ('proc', 'fh', 'log')} | {'tail': tail,
            'elapsed': round(time.time() - j['started'], 1)}


VIDEO_EXT = ('.mp4', '.mov', '.m4v')
MAX_UPLOAD = 8 * 1024 ** 3


def create_project(data):
    slug = str(data.get('slug', '')).strip().lower()
    if not reel.valid_slug(slug):
        raise ValueError('name: lowercase letters, digits, - or _ (e.g. scaling-test)')
    if os.path.exists(os.path.join(PROJECTS, slug)):
        raise ValueError(f'a project called {slug} already exists')
    args = [sys.executable, os.path.join(ROOT, 'reel.py'), 'new', slug, '--mode', 'B']
    if data.get('title'):
        args += ['--title', str(data['title'])[:200]]
    if data.get('cta'):
        args += ['--cta', str(data['cta'])[:40]]
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    if p.returncode:
        raise ValueError((p.stderr or p.stdout).strip()[-300:])
    return {'slug': slug}


def key_status():
    cfg = reel.builder.load_config()
    el = cfg.get('elevenlabs', {})
    env = bool(os.environ.get(el.get('key_env', 'ELEVENLABS_API_KEY')))
    f = os.path.expanduser(el.get('key_file', '~/.el_key'))
    return {'elevenlabs': env or os.path.exists(f), 'source': 'environment' if env else ('file' if os.path.exists(f) else None),
            'key_file': el.get('key_file', '~/.el_key')}


def save_key(key):
    key = str(key or '').strip()
    if not key or len(key) > 200 or any(c.isspace() for c in key):
        raise ValueError('paste the key exactly (one line, no spaces)')
    cfg = reel.builder.load_config()
    f = os.path.expanduser(cfg.get('elevenlabs', {}).get('key_file', '~/.el_key'))
    fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as fh:
        fh.write(key)
    return key_status()


def previews(slug):
    pd = os.path.join(PROJECTS, slug, 'exports', 'previews')
    out = []
    if os.path.isdir(pd):
        for f in sorted(os.listdir(pd)):
            if f.endswith('.json'):
                info = reel.rj(os.path.join(pd, f), {})
                if os.path.exists(os.path.join(PROJECTS, slug, info.get('preview', ''))):
                    out.append(info)
    return out


class H(BaseHTTPRequestHandler):
    server_version = 'ReelStudio/1'

    def log_message(self, fmt, *args):
        pass

    def host_ok(self):
        host = self.headers.get('Host', '')
        return host in self.server.allowed_hosts

    def origin_ok(self):
        origin = self.headers.get('Origin')
        return origin in (None, 'http://' + self.headers.get('Host', ''))

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        size = os.path.getsize(path)
        ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        if path.endswith('.md'):
            ctype = 'text/plain; charset=utf-8'
        rng = self.headers.get('Range')
        start, end = 0, size - 1
        if rng and rng.startswith('bytes='):
            a, _, b = rng[6:].partition('-')
            try:
                if a:
                    start = int(a); end = int(b) if b else size - 1
                else:
                    start = size - int(b)
            except ValueError:
                start, end = 0, size - 1
            end = min(end, size - 1)
            if start > end:
                self.send_response(416); self.send_header('Content-Range', f'bytes */{size}'); self.end_headers(); return
            self.send_response(206)
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        else:
            self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        with open(path, 'rb') as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_GET(self):
        if not self.host_ok():
            return self.send_json({'error': 'bad host'}, 403)
        path = unquote(urlparse(self.path).path)
        if path in ('/', '/index.html'):
            return self.send_file(os.path.join(STATIC, 'index.html'))
        if path.startswith('/static/'):
            p = inside(STATIC, path[len('/static/'):])
            return self.send_file(p) if p else self.send_json({'error': 'not found'}, 404)
        if path.startswith('/fonts/'):
            p = inside(os.path.join(ROOT, 'fonts'), path[len('/fonts/'):])
            return self.send_file(p) if p else self.send_json({'error': 'not found'}, 404)
        if path == '/api/health':
            return self.send_json({'app': 'reel-studio', 'root': ROOT})
        if path == '/api/projects':
            out = []
            for s in sorted(os.listdir(PROJECTS)):
                d = os.path.join(PROJECTS, s)
                p = reel.rj(os.path.join(d, 'project.json'), None)
                if not p:
                    continue
                notes = reel.rj(os.path.join(d, 'feedback.json'), [])
                vs = reel.rj(os.path.join(d, 'versions.json'), [])
                out.append({'slug': s, 'title': p.get('title'), 'mode': p.get('mode'), 'stage': p.get('stage'),
                            'reel_id': p.get('reel_id'), 'open_notes': sum(n['status'] == 'open' for n in notes),
                            'latest': vs[-1]['id'] if vs else None, 'updated': vs[-1]['created'] if vs else p.get('created')})
            out.sort(key=lambda x: x.get('updated') or '', reverse=True)
            return self.send_json(out)
        if path.startswith('/api/jobs/'):
            j = JOBS.get(path.split('/')[3])
            return self.send_json(job_view(j)) if j else self.send_json({'error': 'no job'}, 404)
        if path == '/api/settings':
            return self.send_json(key_status())
        if path.startswith('/api/project/') and path.endswith('/previews'):
            slug = safe_slug(path.split('/')[3])
            return self.send_json(previews(slug)) if slug else self.send_json({'error': 'no project'}, 404)
        if path == '/api/jobs':
            return self.send_json([job_view(j) for j in JOBS.values()])
        if path.startswith('/api/project/') and len(path.split('/')) == 5 and path.split('/')[4] in ('edit', 'diff'):
            slug = safe_slug(path.split('/')[3])
            if not slug:
                return self.send_json({'error': 'no project'}, 404)
            if path.endswith('/edit'):
                return self.send_json(edit_state(slug))
            from urllib.parse import parse_qs
            q = parse_qs(urlparse(self.path).query)
            snap = lambda v: reel.rj(os.path.join(PROJECTS, slug, 'versions', f'{v}.scenes.json'), None) if reel.valid_slug(v) else None  # noqa: E731
            a, b = (q.get('a') or [''])[0], (q.get('b') or [''])[0]
            return self.send_json({'a': a, 'b': b, 'diff': editor.scene_diff(snap(a), snap(b))})
        if path.startswith('/api/project/'):
            raw = path.split('/')[3]
            slug = safe_slug(raw)
            if slug:
                return self.send_json(project_detail(slug))
            if os.path.isdir(os.path.join(PROJECTS, raw)) and not reel.valid_slug(raw):
                return self.send_json({'error': 'folder names must be lowercase letters, digits, "-" or "_"; '
                                                'rename the folder in projects/'}, 400)
            return self.send_json({'error': 'no project'}, 404)
        if path.startswith('/media/'):
            bits = path.split('/', 3)
            if len(bits) < 4:
                return self.send_json({'error': 'not found'}, 404)
            _, _, slug, rel = bits
            slug = safe_slug(slug)
            p = inside(os.path.join(PROJECTS, slug), rel) if slug else None
            return self.send_file(p) if p else self.send_json({'error': 'not found'}, 404)
        if path == '/api/library':
            return self.send_json({'techniques': reel.rj(os.path.join(reel.LIB, 'techniques.json'), []),
                                   'references': reel.rj(os.path.join(reel.LIB, 'references.json'), [])})
        self.send_json({'error': 'not found'}, 404)

    def body(self):
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            raise ValueError('JSON only')
        n = int(self.headers.get('Content-Length', 0))
        if n > 2_000_000:
            raise ValueError('too large')
        return json.loads(self.rfile.read(n) or b'{}')

    def do_PUT(self):
        """Footage upload: streamed to raw/raw<ext>.part, checked with ffprobe, then moved in place. Existing
        footage is never replaced (a project gets one source video)."""
        if not (self.host_ok() and self.origin_ok()) or self.headers.get('X-Reel-Upload') != '1':
            return self.send_json({'error': 'forbidden'}, 403)
        u = urlparse(self.path)
        parts = u.path.strip('/').split('/')
        if not (len(parts) == 4 and parts[:2] == ['api', 'project'] and parts[3] == 'upload'):
            return self.send_json({'error': 'not found'}, 404)
        slug = safe_slug(parts[2])
        if not slug:
            return self.send_json({'error': 'no project'}, 404)
        from urllib.parse import parse_qs
        name = (parse_qs(u.query).get('name') or [''])[0]
        ext = os.path.splitext(name)[1].lower()
        if ext not in VIDEO_EXT:
            return self.send_json({'error': f'video files only ({", ".join(VIDEO_EXT)})'}, 400)
        n = int(self.headers.get('Content-Length', 0) or 0)
        if not 0 < n <= MAX_UPLOAD:
            return self.send_json({'error': 'empty or larger than 8 GB'}, 400)
        d = os.path.join(PROJECTS, slug)
        rawd = os.path.join(d, 'raw'); os.makedirs(rawd, exist_ok=True)
        if any(f.startswith('raw.') and not f.endswith('.part') for f in os.listdir(rawd)):
            return self.send_json({'error': 'this project already has its footage (create a new project for another video)'}, 409)
        dst = os.path.join(rawd, 'raw' + ext); tmp = dst + '.part'
        left = n
        with open(tmp, 'wb') as f:
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    break
                f.write(chunk); left -= len(chunk)
        if left:
            os.remove(tmp)
            return self.send_json({'error': 'upload interrupted'}, 400)
        pr = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height:format=duration',
                             '-of', 'json', tmp], capture_output=True, text=True)
        try:
            info = json.loads(pr.stdout)
            kinds = [st.get('codec_type') for st in info.get('streams', [])]
            assert 'video' in kinds and 'audio' in kinds
        except Exception:
            os.remove(tmp)
            return self.send_json({'error': 'not a video with sound (ffprobe could not read it)'}, 400)
        os.replace(tmp, dst)
        proj = reel.rj(os.path.join(d, 'project.json'), {})
        proj['raw'] = 'raw/raw' + ext; proj['source_name'] = os.path.basename(name)[:200]
        reel.wj(os.path.join(d, 'project.json'), proj)
        v = next(st for st in info['streams'] if st.get('codec_type') == 'video')
        reel.log_status(d, f'footage uploaded from the studio: {proj["source_name"]} ({n / 1e6:.0f} MB)')
        return self.send_json({'raw': proj['raw'], 'bytes': n, 'width': v.get('width'), 'height': v.get('height'),
                               'duration': round(float(info['format']['duration']), 2)})

    def do_POST(self):
        if not (self.host_ok() and self.origin_ok()):
            return self.send_json({'error': 'forbidden'}, 403)
        try:
            data = self.body()
        except ValueError as e:
            return self.send_json({'error': str(e)}, 400)
        parts = urlparse(self.path).path.strip('/').split('/')
        if parts[:2] == ['library', 'references'] or parts[:3] == ['api', 'library', 'references']:
            url = str(data.get('url', '')).strip()
            if not url.startswith(('http://', 'https://')):
                return self.send_json({'error': 'a http(s) link is required'}, 400)
            refs = reel.rj(os.path.join(reel.LIB, 'references.json'), [])
            ref = {'id': uuid.uuid4().hex[:8], 'url': url[:500], 'title': str(data.get('title', ''))[:200],
                   'creator': str(data.get('creator', ''))[:120], 'notes': str(data.get('notes', ''))[:4000],
                   'techniques': [str(t)[:60] for t in data.get('techniques', [])][:20], 'analysis': '',
                   'created': reel.now()}
            refs.append(ref)
            reel.wj(os.path.join(reel.LIB, 'references.json'), refs)
            return self.send_json(ref)
        if parts == ['api', 'projects']:
            try:
                return self.send_json(create_project(data))
            except ValueError as e:
                return self.send_json({'error': str(e)}, 400)
        if parts == ['api', 'settings', 'elevenlabs']:
            try:
                return self.send_json(save_key(data.get('key')))
            except ValueError as e:
                return self.send_json({'error': str(e)}, 400)
        if len(parts) == 4 and parts[:2] == ['api', 'jobs'] and parts[3] == 'cancel':
            j = JOBS.get(parts[2])
            if not j:
                return self.send_json({'error': 'no job'}, 404)
            if j['status'] == 'running':
                j['cancel'] = True; j['proc'].terminate()
            return self.send_json(job_view(j))
        if len(parts) >= 4 and parts[:2] == ['api', 'project'] and parts[3] in ('edit', 'run'):
            slug = safe_slug(parts[2])
            if not slug:
                return self.send_json({'error': 'no project'}, 404)
            d = os.path.join(PROJECTS, slug)
            try:
                if parts[3] == 'run':
                    return self.send_json(start_job(slug, str(data.get('cmd', '')), data))
                what = '/'.join(parts[4:])
                if what == 'scene':
                    return self.send_json(editor.update_scene(d, data.get('id'), data.get('patch') or {}))
                if what == 'regenerate':
                    return self.send_json(editor.regenerate_scene(d, data.get('id'), data.get('intensity') or 'medium'))
                if what == 'words':
                    return self.send_json(editor.edit_words(d, data.get('changes') or {}))
                if what == 'keyword':
                    return self.send_json(editor.toggle_keyword(d, data.get('word', '')))
                if what == 'variant':
                    return self.send_json(editor.save_variant(d, data.get('name', '')))
                if what == 'variant/use':
                    return self.send_json(editor.use_variant(d, data.get('name', '')))
            except (editor.EditError, ValueError) as e:
                return self.send_json({'error': str(e)}, 400)
            return self.send_json({'error': 'not found'}, 404)
        if len(parts) >= 4 and parts[:2] == ['api', 'project']:
            slug = safe_slug(parts[2])
            if not slug:
                return self.send_json({'error': 'no project'}, 404)
            d = os.path.join(PROJECTS, slug)
            fbp = os.path.join(d, 'feedback.json')
            if parts[3] == 'notes' and len(parts) == 4:
                text = str(data.get('text', '')).strip()
                if not text:
                    return self.send_json({'error': 'empty note'}, 400)
                t = data.get('t')
                meta = reel.rj(os.path.join(d, 'build', 'meta.json'), {'scenes': []})
                ver = str(data.get('version') or '')
                scene = data.get('scene') or (next((s['id'] for s in meta['scenes']
                                                    if t is not None and s['start'] <= float(t) < s['end']), None)
                                              if ver.startswith('v') else None)
                note = {'id': uuid.uuid4().hex[:8], 'version': data.get('version'),
                        't': None if t is None else round(float(t), 2), 'scene': scene, 'text': text[:2000],
                        'status': 'open', 'created': reel.now(), 'source': 'studio'}
                fb = reel.rj(fbp, []); fb.append(note); reel.wj(fbp, fb)
                return self.send_json(note)
            if parts[3] == 'notes' and len(parts) == 5:
                fb = reel.rj(fbp, [])
                n = next((n for n in fb if n['id'] == parts[4]), None)
                if not n:
                    return self.send_json({'error': 'no note'}, 404)
                if data.get('status') in ('open', 'applied', 'dismissed'):
                    n['status'] = data['status']
                if 'text' in data:
                    n['text'] = str(data['text'])[:2000]
                reel.wj(fbp, fb)
                return self.send_json(n)
            if parts[3] == 'approve':
                stage = data.get('stage')
                if stage not in ('brief', 'script', 'voiceover', 'roughcut', 'storyboard', 'final'):
                    return self.send_json({'error': 'bad stage'}, 400)
                return self.send_json(reel.approve(d, stage, data.get('version'), by='studio'))
        self.send_json({'error': 'not found'}, 404)


def free_port(start):
    for p in range(start, start + 50):
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1', p)) != 0:
                return p
    raise SystemExit('no free port')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--open', action='store_true', help='open the studio in the default browser')
    a = ap.parse_args()
    port = free_port(a.port)
    srv = ThreadingHTTPServer(('127.0.0.1', port), H)
    srv.allowed_hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
    print(f'Reel Studio running at http://127.0.0.1:{port}  (Ctrl+C to stop)', flush=True)
    if port != a.port:
        print(f'(port {a.port} was busy — is another Reel Studio window already open?)', flush=True)
    if a.open:
        import webbrowser
        threading.Timer(0.8, webbrowser.open, [f'http://127.0.0.1:{port}/']).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
