"""Non-destructive editing used by the studio (and tests).

Every write backs the previous file up (scenes.prev-<time>.json / words.prev-<time>.json) and appends a line to
edits.json, so any change can be traced and undone. Locked scenes are never changed by an edit, a regenerate or
`reel.py plan --apply`. Transcript edits may fix a word's spelling only: the word count and every timing stay as
spoken, so the speaker's words are never rewritten or re-timed.
"""
import datetime as dt
import json
import os
import shutil

import build as builder
import planner
from timing import Anchors, load_words

SCENE_KEYS = {'style', 'layout', 'transition', 'caption_style', 'zoom', 'parallax', 'punch', 'start', 'title',
              'locked', 'elements'}


class EditError(ValueError):
    pass


def _rj(p, default=None):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _wj(p, obj):
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def stamp():
    return dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')


def backup(d, name):
    src = os.path.join(d, name)
    if not os.path.exists(src):
        return None
    stem, ext = os.path.splitext(name)
    dst = os.path.join(d, f'{stem}.prev-{stamp()}{ext}')
    shutil.copy(src, dst)
    return os.path.basename(dst)


def log_edit(d, action, **info):
    p = os.path.join(d, 'edits.json')
    log = _rj(p, []) or []
    log.append({'at': dt.datetime.now().isoformat(timespec='seconds'), 'action': action, **info})
    _wj(p, log)


def load_spec(d):
    spec = _rj(os.path.join(d, 'scenes.json'))
    if not spec:
        raise EditError('no scenes.json yet')
    return spec


def check(d):
    """Build the page and return its problems + notes (render blocks on problems)."""
    m = builder.build(d)
    return {'problems': m['anchor_misses'], 'notes': m.get('notes', []), 'scenes': m['scenes'],
            'duration': m['duration']}


def save_spec(d, spec, action, **info):
    """Back up, write, build. If the build itself fails the previous file is restored."""
    bak = backup(d, 'scenes.json')
    _wj(os.path.join(d, 'scenes.json'), spec)
    try:
        res = check(d)
    except Exception as e:                                     # never leave a project that cannot build
        if bak:
            shutil.copy(os.path.join(d, bak), os.path.join(d, 'scenes.json'))
        raise EditError(f'edit not saved, build failed: {e}')
    log_edit(d, action, backup=bak, **info)
    res['backup'] = bak
    return res


def find_scene(spec, sid):
    for i, s in enumerate(spec.get('scenes', [])):
        if str(s.get('id', i)) == str(sid):
            return i, s
    raise EditError(f'no scene {sid!r}')


def validate_patch(patch):
    bad = set(patch) - SCENE_KEYS
    if bad:
        raise EditError(f'cannot edit {", ".join(sorted(bad))} here (allowed: {", ".join(sorted(SCENE_KEYS))})')
    if 'layout' in patch and patch['layout'] not in (None, '') and patch['layout'] not in builder.LAYOUTS:
        raise EditError(f'unknown layout {patch["layout"]!r}')
    if patch.get('transition') and patch['transition'] not in builder.TRANSITIONS:
        raise EditError(f'unknown transition {patch["transition"]!r}')
    if patch.get('caption_style') and patch['caption_style'] not in builder.CAPTION_STYLES:
        raise EditError(f'unknown caption style {patch["caption_style"]!r}')
    if patch.get('style'):
        st = builder.style_name(patch['style'])
        if st not in builder.STYLES:
            raise EditError(f'style {patch["style"]!r} is not available'
                            + (' (05 needs real CEOS screens)' if st == 'floating-ui' else ''))
    if 'zoom' in patch and patch['zoom'] not in (None, ''):
        z = patch['zoom']
        if not (isinstance(z, list) and len(z) == 2 and all(isinstance(v, (int, float)) and 0.8 <= v <= 2 for v in z)):
            raise EditError('zoom must be [start, end] between 0.8 and 2')
    if 'parallax' in patch and patch['parallax'] not in (None, '') and not (0 <= float(patch['parallax']) <= 1):
        raise EditError('parallax must be 0-1')
    if 'elements' in patch and not (isinstance(patch['elements'], list) and all(isinstance(e, dict) and e.get('type')
                                                                               for e in patch['elements'])):
        raise EditError('elements must be a list of objects with a "type"')


def update_scene(d, sid, patch):
    spec = load_spec(d)
    i, s = find_scene(spec, sid)
    validate_patch(patch)
    if s.get('locked') and set(patch) - {'locked'}:
        raise EditError(f'scene {sid} is locked: unlock it first')
    for k, v in patch.items():
        if v is None or v == '':
            s.pop(k, None)
        else:
            s[k] = v
    if i == 0 and 'start' in patch:
        s.pop('start', None)                                   # the first scene always starts at 0
    return save_spec(d, spec, 'scene', scene=str(sid), keys=sorted(patch))


def _draft(d, intensity, brand=None):
    words = load_words(os.path.join(d, 'words.json'))
    if not words:
        raise EditError('no words.json yet')
    proj = _rj(os.path.join(d, 'project.json'), {}) or {}
    pl = planner.plan(words, intensity)
    draft = planner.draft_scenes(pl, words, brand=brand, cta_keyword=proj.get('cta_keyword'))
    anchors = Anchors(words)
    times, prev = [], 0.0
    for j, ds in enumerate(draft['scenes']):
        t = 0.0 if j == 0 and ds.get('start') is None else anchors.resolve(ds.get('start'), prev, default=prev)
        times.append(t); prev = t
    return draft, times


def regenerate_scene(d, sid, intensity='medium'):
    """Replace one scene's elements with the director's draft for the same stretch of speech (layout and
    style choices the user made are kept). Locked scenes are refused."""
    spec = load_spec(d)
    i, s = find_scene(spec, sid)
    if s.get('locked'):
        raise EditError(f'scene {sid} is locked: unlock it first')
    cur = check(d)['scenes']
    st, en = cur[i]['start'], cur[i]['end']
    draft, times = _draft(d, intensity, spec.get('brand'))
    anchors = Anchors(load_words(os.path.join(d, 'words.json')))
    picked, why, dropped = [], [], 0
    for ds, t in zip(draft['scenes'], times):
        if st - 0.05 <= t < en - 0.05:
            for e in ds.get('elements', []):
                t_in = anchors.resolve(e.get('in'), max(t, st), default=max(t, st)) if e.get('in') else max(t, st)
                if t_in < en - 0.6:                            # must be on screen long enough to read
                    picked.append(e)
                else:
                    dropped += 1
            if ds.get('_plan'):
                why.append(f'{ds["_plan"]["role"]} ({ds["_plan"]["confidence"]})')
    if not picked:                                             # nothing proposed: leave the scene as it is
        res = check(d)
        res['regenerated'] = {'elements': 0, 'roles': why, 'dropped_late': dropped,
                              'note': 'the director proposes a plain talking head here; scene left unchanged '
                                      '(clear its elements yourself if you want that)'}
        return res
    s['elements'] = picked
    res = save_spec(d, spec, 'regenerate', scene=str(sid), intensity=intensity, roles=why)
    res['regenerated'] = {'elements': len(picked), 'roles': why, 'dropped_late': dropped,
                          'note': 'draft — review it'}
    return res


def merge_with_locks(spec, cur_scenes, draft, draft_times):
    """Plan --apply with locks: locked scenes stay exactly as they are; draft scenes that start inside a locked
    scene's time span are dropped; everything is kept in time order."""
    locked = [(cur_scenes[i]['start'], cur_scenes[i]['end'], s) for i, s in enumerate(spec.get('scenes', []))
              if s.get('locked') and i < len(cur_scenes)]
    if not locked:
        return draft
    out = []
    for ds, t in zip(draft['scenes'], draft_times):
        if any(a - 0.05 <= t < b - 0.05 for a, b, _ in locked):
            continue
        out.append((t, ds))
    for a, _, s in locked:
        out.append((a, s))
    out.sort(key=lambda x: x[0])
    merged = dict(draft)
    merged['scenes'] = [s for _, s in out]
    if merged['scenes'] and merged['scenes'][0].get('start') is not None:
        first = dict(merged['scenes'][0]); first.pop('start')      # the first scene always covers 0
        merged['scenes'][0] = first
    return merged


# ---- transcript / captions ------------------------------------------------------------------------------

def words(d):
    return _rj(os.path.join(d, 'words.json'), None)


def _word_list(w):
    return w['words'] if isinstance(w, dict) else w


def edit_words(d, changes):
    """changes: {index: new text}. Spelling fixes only — same word count, same timings."""
    w = words(d)
    if not w:
        raise EditError('no words.json yet')
    lst = _word_list(w)
    log = []
    for k, txt in changes.items():
        i = int(k)
        if not 0 <= i < len(lst):
            raise EditError(f'no word {i}')
        txt = str(txt).strip()
        if not txt or any(c.isspace() for c in txt):
            raise EditError(f'word {i}: one word, no spaces (splitting or adding words would change what was said)')
        if txt != lst[i]['text']:
            log.append({'i': i, 'from': lst[i]['text'], 'to': txt, 't': lst[i].get('start')})
    if not log:
        return {'changed': 0}
    has_spec = os.path.exists(os.path.join(d, 'scenes.json'))
    before = len(check(d)['problems']) if has_spec else 0
    bak = backup(d, 'words.json')
    for c in log:
        lst[c['i']]['text'] = c['to']
    _wj(os.path.join(d, 'words.json'), w)
    anchors_fixed, sbak = 0, None
    if has_spec and len(check(d)['problems']) > before:
        # the corrected word is a timing anchor: update anchors that used the old spelling
        spec = load_spec(d)
        anchors_fixed = _rename_anchors(spec, {c['from']: c['to'] for c in log})
        if anchors_fixed:
            sbak = backup(d, 'scenes.json')
            _wj(os.path.join(d, 'scenes.json'), spec)
        if len(check(d)['problems']) > before:                  # still breaks timing: undo everything
            shutil.copy(os.path.join(d, bak), os.path.join(d, 'words.json'))
            if sbak:
                shutil.copy(os.path.join(d, sbak), os.path.join(d, 'scenes.json'))
            check(d)
            raise EditError('this correction would break scene/element timing anchors; nothing was changed')
    tp = os.path.join(d, 'transcript_edits.json')
    te = _rj(tp, []) or []
    te += [dict(c, at=dt.datetime.now().isoformat(timespec='seconds')) for c in log]
    _wj(tp, te)
    log_edit(d, 'transcript', backup=bak, changed=len(log), anchors_fixed=anchors_fixed, scenes_backup=sbak)
    res = check(d) if has_spec else {}
    res.update({'changed': len(log), 'backup': bak, 'anchors_fixed': anchors_fixed})
    return res


ANCHOR_KEYS = ('start', 'in', 'out', 'at', 'fill_end')


def _rename_anchors(spec, ren):
    """Replace whole words in anchor strings (scene start, element in/out, punch at…). Returns how many changed."""
    n = 0

    def fix(v):
        nonlocal n
        if isinstance(v, str):
            toks = v.split()
            new = [ren.get(t, t) for t in toks]
            if new != toks:
                n += 1
                return ' '.join(new)
        return v

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ANCHOR_KEYS and isinstance(v, str):
                    o[k] = fix(v)
                elif k in ANCHOR_KEYS and isinstance(v, dict) and isinstance(v.get('at'), str):
                    v['at'] = fix(v['at'])
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(spec)
    return n


def toggle_keyword(d, word):
    spec = load_spec(d)
    kw = list(spec.get('caption_keywords', []))
    word = str(word).strip()
    if not word:
        raise EditError('empty keyword')
    if word in kw:
        kw.remove(word)
    else:
        kw.append(word)
    spec['caption_keywords'] = kw
    res = save_spec(d, spec, 'caption_keyword', word=word, on=word in kw)
    res['caption_keywords'] = kw
    return res


# ---- variants -------------------------------------------------------------------------------------------

def clean_name(name):
    return ''.join(c for c in str(name) if c.isascii() and (c.isalnum() or c in '-_'))[:40]


def save_variant(d, name):
    name = clean_name(name)
    if not name:
        raise EditError('variant name: letters, digits, - or _')
    os.makedirs(os.path.join(d, 'variants'), exist_ok=True)
    p = os.path.join(d, 'variants', f'{name}.scenes.json')
    if os.path.exists(p):
        raise EditError(f'variant {name} exists: pick another name (variants are never overwritten)')
    shutil.copy(os.path.join(d, 'scenes.json'), p)
    log_edit(d, 'variant_saved', name=name)
    return {'variant': name}


def list_variants(d):
    vd = os.path.join(d, 'variants')
    return sorted(f[:-len('.scenes.json')] for f in os.listdir(vd) if f.endswith('.scenes.json')) if os.path.isdir(vd) else []


def use_variant(d, name):
    name = clean_name(name)
    p = os.path.join(d, 'variants', f'{name}.scenes.json')
    spec = _rj(p)
    if not spec:
        raise EditError(f'no variant {name!r}')
    return save_spec(d, spec, 'variant_used', name=name)


def scene_diff(a, b):
    """What changed between two scenes.json snapshots, per scene id (for the compare view)."""
    def idx(spec):
        return {str(s.get('id', i)): s for i, s in enumerate((spec or {}).get('scenes', []))}
    A, B = idx(a), idx(b)
    out = []
    for sid in list(dict.fromkeys(list(A) + list(B))):
        x, y = A.get(sid), B.get(sid)
        if x is None or y is None:
            out.append({'scene': sid, 'change': 'added' if x is None else 'removed'}); continue
        keys = sorted(k for k in set(x) | set(y) if k != 'elements' and x.get(k) != y.get(k))
        ex = [e.get('type') for e in x.get('elements', [])]; ey = [e.get('type') for e in y.get('elements', [])]
        if keys or x.get('elements') != y.get('elements'):
            out.append({'scene': sid, 'change': 'changed', 'keys': keys,
                        'elements': None if x.get('elements') == y.get('elements') else [ex, ey]})
    for k in sorted(set(a or {}) | set(b or {})):
        if k != 'scenes' and (a or {}).get(k) != (b or {}).get(k):
            out.append({'scene': '(reel)', 'change': 'changed', 'keys': [k]})
    return out
