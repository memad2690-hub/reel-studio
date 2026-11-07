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
"""
import argparse
import json
import mimetypes
import os
import socket
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import reel  # noqa: E402

STATIC = os.path.join(ROOT, 'studio', 'static')
PROJECTS = reel.PROJECTS
SLUG_OK = set('abcdefghijklmnopqrstuvwxyz0123456789-_')


def safe_slug(slug):
    if not slug or set(slug) - SLUG_OK or not os.path.isdir(os.path.join(PROJECTS, slug)):
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
        if path.startswith('/api/project/'):
            slug = safe_slug(path.split('/')[3])
            return self.send_json(project_detail(slug)) if slug else self.send_json({'error': 'no project'}, 404)
        if path.startswith('/media/'):
            _, _, slug, rel = path.split('/', 3)
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
        if n > 200_000:
            raise ValueError('too large')
        return json.loads(self.rfile.read(n) or b'{}')

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
    a = ap.parse_args()
    port = free_port(a.port)
    srv = ThreadingHTTPServer(('127.0.0.1', port), H)
    srv.allowed_hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
    print(f'Reel Studio running at http://127.0.0.1:{port}  (Ctrl+C to stop)', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
