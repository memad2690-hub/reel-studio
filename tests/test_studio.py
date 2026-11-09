"""Usability pass: director modes, look-2 grade default, studio project/upload/pipeline."""
import http.client
import json
import os
import shutil
import subprocess as sp
import sys
import tempfile
import threading
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'studio'))
import reel  # noqa: E402
import planner  # noqa: E402
import grade as grading  # noqa: E402
import serve  # noqa: E402

TALK = ('بص لو عندك 50 ألف جنيه ميزانية ما تحرقهمش. أول حاجة تعمل test صغير وتاني حاجة تقارن الـ CPA. '
        'الـ CPA كان مية وخمسين جنيه وبقى تسعين. الفرق بين الحملة دي والحملة دي كبير. اكتبلي BUDGET')


def W(text, step=0.45):
    return [{'text': w, 'start': round(i * step, 2), 'end': round(i * step + 0.38, 2)} for i, w in enumerate(text.split())]


class DirectorModeTests(unittest.TestCase):
    def draft(self, **kw):
        words = W(TALK)
        return planner.draft_scenes(planner.plan(words, 'medium'), words, **kw)

    def test_auto_mixes_styles_and_marks_look2(self):
        d = self.draft(director='auto')
        self.assertEqual(d['look'], 2)
        self.assertEqual(d['director']['mode'], 'auto')
        styles = {sc.get('style') for sc in d['scenes']}
        self.assertGreaterEqual(len(styles), 2, styles)
        self.assertNotIn('collage', styles)                     # needs segmentation → never auto-picked
        self.assertNotIn('parallax', styles)
        self.assertLessEqual(len(styles), planner.AUTO_MAX_STYLES)

    def test_auto_cap(self):
        st = planner.auto_styles(['hook', 'setup', 'comparison', 'conclusion', 'data', 'process'])
        self.assertLessEqual(len(set(st)), 3)
        self.assertEqual(planner.auto_styles(['hook', 'setup']), ['cinematic', 'editorial'])

    def test_single_uses_one_style(self):
        d = self.draft(director='single', style='kinetic')
        self.assertEqual({sc.get('style') for sc in d['scenes']}, {'kinetic'})

    def test_hybrid_keeps_data_scenes(self):
        d = self.draft(director='hybrid', style='editorial')
        for sc in d['scenes']:
            role = sc.get('role') or (sc.get('meta') or {}).get('role')
            if role in planner.HYBRID_OVERRIDE:
                self.assertEqual(sc['style'], planner.HYBRID_OVERRIDE[role])
        self.assertIn('editorial', {sc.get('style') for sc in d['scenes']})

    def test_bad_mode_is_refused(self):
        r = sp.run([sys.executable, 'reel.py', 'plan', 'nope', '--director', 'random'], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


class DirectorReadingTests(unittest.TestCase):
    """From the first real test reel: a checklist of questions, a yes/no question, a lowercase CTA keyword."""
    TEXT = ('فقبل ما نزود الصرف محتاجين نجاوب على هل المخزون يستحمل؟ هل الـ contribution is positive؟ '
            'يعني هل إحنا بنطلع عليها ربح ولا لأ؟ هل الـ tracking هل الـ tracking validated؟ وهل فيه creatives جديدة؟ '
            'كلام عادي جدا هنا كمان شوية. لو عندك brand ابعت لي scale مع نوع المنتج')

    def test_checklist_not_comparison_and_cta(self):
        words = W(self.TEXT)
        pl = planner.plan(words, 'medium', cta_keyword='SCALE')
        roles = [s['role'] for s in pl['segments']]
        self.assertIn('process', roles)
        self.assertNotIn('comparison', roles)
        self.assertEqual(roles[-1], 'cta')
        d = planner.draft_scenes(pl, words, cta_keyword='SCALE')
        num = [e for sc in d['scenes'] for e in sc['elements'] if e['type'] == 'numbered'][0]
        self.assertEqual(len(num['steps']), 4)                          # the retake is not a 5th step
        import timing
        A = timing.Anchors(words)
        seg = next(s for s in pl['segments'] if s['role'] == 'process')
        ts = [A.resolve(st['in'], seg['start']) for st in num['steps']]
        self.assertEqual(ts, sorted(set(ts)))                           # each step on its own question
        cta = [e for sc in d['scenes'] for e in sc['elements'] if e['type'] == 'cta'][0]
        self.assertEqual(cta['prompt'], 'ابعت لي')


class GradeDefaultTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def put(self, name, data):
        with open(os.path.join(self.d, name), 'w') as f:
            json.dump(data, f)

    def test_look2_defaults_to_rc_warm_for_every_style(self):
        self.put('project.json', {'mode': 'B', 'look': 2})
        self.put('scenes.json', {'look': 2, 'scenes': [{'style': 'kinetic'}]})
        g = grading.project_grade(self.d)
        self.assertEqual(g['preset'], grading.DEFAULT_STYLE09)

    def test_look1_non_cinematic_is_untouched(self):
        self.put('project.json', {'mode': 'B'})
        self.put('scenes.json', {'scenes': [{'style': 'editorial'}]})
        self.assertIsNone(grading.project_grade(self.d))

    def test_grade_json_off_wins(self):
        self.put('project.json', {'mode': 'B', 'look': 2})
        self.put('grade.json', {'preset': grading.DEFAULT_STYLE09, 'intensity': 0})
        g = grading.project_grade(self.d)
        self.assertTrue(g is None or not g.get('intensity'))

    def test_grade_image_writes_copy_not_source(self):
        src = os.path.join(self.d, 'p.png')
        sp.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=gray:s=64x64', '-frames:v', '1', src], check=True)
        before = open(src, 'rb').read()
        dst = os.path.join(self.d, 'g', 'p.jpg')
        grading.grade_image(src, dst, {'preset': grading.DEFAULT_STYLE09, 'intensity': 1.0})
        self.assertTrue(os.path.exists(dst))
        self.assertEqual(open(src, 'rb').read(), before)


class StudioServerTests(unittest.TestCase):
    slug = '_test-studio-ui'

    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 0), serve.H)
        cls.port = cls.srv.server_address[1]
        cls.srv.allowed_hosts = {f'127.0.0.1:{cls.port}'}
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.d = os.path.join(reel.PROJECTS, cls.slug)
        shutil.rmtree(cls.d, ignore_errors=True)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        shutil.rmtree(cls.d, ignore_errors=True)

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=60)
        hd = {'Host': f'127.0.0.1:{self.port}'}
        if isinstance(body, dict):
            body = json.dumps(body).encode(); hd['Content-Type'] = 'application/json'
        hd.update(headers or {})
        c.request(method, path, body=body, headers=hd)
        r = c.getresponse()
        return r.status, json.loads(r.read() or b'{}')

    def test_flow(self):
        st, r = self.req('POST', '/api/projects', {'slug': self.slug, 'title': 'تجربة', 'cta': 'BUDGET'})
        self.assertEqual(st, 200, r)
        st, r = self.req('POST', '/api/projects', {'slug': self.slug})
        self.assertNotEqual(st, 200)                                # never overwrites a project
        st, ed = self.req('GET', f'/api/project/{self.slug}/edit')
        self.assertEqual(ed['look'], 2)
        self.assertEqual(ed['grade']['preset'], grading.DEFAULT_STYLE09)
        self.assertEqual([p['id'] for p in ed['pipeline']][:2], ['import', 'transcribe'])
        self.assertFalse(ed['pipeline'][0]['done'])
        # upload: header required, non-video refused, real video accepted once
        up = f'/api/project/{self.slug}/upload?name=talk.mp4'
        st, _ = self.req('PUT', up, b'x' * 10)
        self.assertEqual(st, 403)
        st, r = self.req('PUT', up, b'not a video' * 100, {'X-Reel-Upload': '1'})
        self.assertEqual(st, 400, r)
        vid = os.path.join(tempfile.mkdtemp(), 'v.mp4')
        sp.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=s=320x568:d=1', '-f', 'lavfi', '-i', 'sine=d=1',
                '-shortest', '-pix_fmt', 'yuv420p', vid], check=True)
        st, r = self.req('PUT', up, open(vid, 'rb').read(), {'X-Reel-Upload': '1'})
        self.assertEqual(st, 200, r)
        st, r = self.req('PUT', up, open(vid, 'rb').read(), {'X-Reel-Upload': '1'})
        self.assertEqual(st, 409)                                   # raw footage is never replaced
        st, ed = self.req('GET', f'/api/project/{self.slug}/edit')
        self.assertTrue(ed['pipeline'][0]['done'])
        self.assertTrue(ed['raw'])
        st, s = self.req('GET', '/api/settings')
        kf = os.path.expanduser('~/.el_key')
        if os.path.exists(kf):
            with open(kf) as f:
                secret = f.read().strip()
            self.assertNotIn(secret, json.dumps(s) + json.dumps(ed))   # status only, never the key

    def test_direct_job_args(self):
        a = serve.job_args('direct', 'x', {'director': 'hybrid', 'style': 'kinetic', 'intensity': 'high'}, 'B')
        self.assertEqual(a[:2], ['plan', 'x'])
        self.assertIn('--apply', a)
        self.assertEqual(a[a.index('--director') + 1], 'hybrid')
        self.assertEqual(a[a.index('--style') + 1], 'kinetic')
        a = serve.job_args('direct', 'x', {'director': 'evil; rm'}, 'B')
        self.assertEqual(a[a.index('--director') + 1], 'auto')
        self.assertEqual(serve.job_args('preview', 'x', {'scene': 's3'}, 'B'), ['preview', 'x', '--scene', 's3'])


if __name__ == '__main__':
    unittest.main()
