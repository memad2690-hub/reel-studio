"""AI editing director, first pass (rule-based): transcript → plan → draft scenes.

    plan(words, intensity) -> {'segments': [...], 'intensity', 'budget'}
    draft_scenes(plan, ...) -> scenes dict (never written over scenes.json by this module)

Each segment: start/end, exact spoken text, language mix, role, keywords, money/percent/ratio values (parsed from
digits *and* Egyptian-Arabic number words), comparisons, process steps, recommended treatment + layout, confidence and
the reason. Low confidence → plain talking head. Claude reviews plan.md and refines scenes before any storyboard.
Every number in a draft comes from the speaker's words; nothing is invented.
"""
import re

from timing import norm

# ------------------------------------------------------------------ Egyptian-Arabic numbers
UNITS = {'واحد': 1, 'واحده': 1, 'واحدة': 1, 'اتنين': 2, 'اثنين': 2, 'تلات': 3, 'تلاته': 3, 'تلاتة': 3, 'ثلاثه': 3, 'ثلاثة': 3,
         'اربع': 4, 'اربعه': 4, 'اربعة': 4, 'خمس': 5, 'خمسه': 5, 'خمسة': 5, 'ست': 6, 'سته': 6, 'ستة': 6, 'سبع': 7, 'سبعه': 7,
         'سبعة': 7, 'تمن': 8, 'تمانيه': 8, 'تمانية': 8, 'ثمانية': 8, 'تسع': 9, 'تسعه': 9, 'تسعة': 9, 'عشر': 10, 'عشره': 10,
         'عشرة': 10, 'حداشر': 11, 'اتناشر': 12, 'تلتاشر': 13, 'اربعتاشر': 14, 'خمستاشر': 15, 'ستاشر': 16, 'سبعتاشر': 17,
         'تمنتاشر': 18, 'تسعتاشر': 19}
TENS = {'عشرين': 20, 'تلاتين': 30, 'ثلاثين': 30, 'اربعين': 40, 'خمسين': 50, 'ستين': 60, 'سبعين': 70, 'تمانين': 80,
        'ثمانين': 80, 'تسعين': 90}
HUNDREDS = {'ميه': 100, 'مية': 100, 'مائه': 100, 'مائة': 100, 'ميت': 100, 'ميتين': 200, 'تلتميه': 300, 'تلتمية': 300,
            'ربعميه': 400, 'ربعمية': 400, 'خمسميه': 500, 'خمسمية': 500, 'ستميه': 600, 'ستمية': 600, 'سبعميه': 700,
            'سبعمية': 700, 'تمنميه': 800, 'تمنمية': 800, 'تسعميه': 900, 'تسعمية': 900}
SCALES = {'الف': 1000, 'آلاف': 1000, 'الاف': 1000, 'الفين': 2000, 'مليون': 1_000_000, 'ملايين': 1_000_000, 'مليار': 1e9}
CURRENCY = ('جنيه', 'جنية', 'ج', 'egp', 'دولار', '$')
MONEY_CTX = ['جنيه', 'budget', 'ميزانية', 'مبيعات', 'sales', 'صرف', 'بيصرف', 'تصرف', 'ربح', 'خسارة', 'تكلفة', 'مصاريف',
             'إعلانات', 'ads', 'فلوس', 'ألف جنيه', 'cpa', 'aov', 'سعر']
PERCENT = ('في المية', 'في الميه', 'بالمية', 'بالميه', '%')


def _strip(tok):
    t = norm(tok)
    for p in ('وبال', 'بال', 'وال', 'ال', 'و', 'ب', 'ف'):
        if t.startswith(p) and len(t) > len(p) + 1 and (t[len(p):] in UNITS or t[len(p):] in TENS or t[len(p):] in HUNDREDS
                                                          or t[len(p):] in SCALES or re.fullmatch(r'[\d.,]+', t[len(p):])):
            return t[len(p):]
    return t


def _val(t):
    if re.fullmatch(r'\d+([.,]\d+)?', t):
        return float(t.replace(',', '')) if ',' in t and len(t.split(',')[-1]) == 3 else float(t.replace(',', '.'))
    for d in (UNITS, TENS, HUNDREDS):
        if t in d:
            return d[t]
    return None


def numbers(words):
    """Find spoken numbers. Returns [{'value', 'i0', 'i1', 'start', 'end', 'text', 'kind'}] with kind money|percent|ratio|count."""
    out, i, n = [], 0, len(words)
    while i < n:
        t = _strip(words[i]['text'])
        raw = norm(words[i]['text'])
        v = _val(t)
        digits = re.search(r'\d[\d,.]*', words[i]['text'])
        if v is None and digits:
            v = _val(digits.group(0).replace('،', ','))
        if v is None and t in SCALES:                       # "ألف" / "ألفين" alone
            v = SCALES[t]
        if v is None:
            i += 1; continue
        j, total, cur = i, 0.0, v
        while j + 1 < n:                                      # absorb "و" chains and scales: خمسة وعشرين ألف
            nt = _strip(words[j + 1]['text'])
            nv = _val(nt)
            if nt in SCALES:
                cur = (cur or 1) * SCALES[nt]; total += cur; cur = 0; j += 1; continue
            if nv is not None and norm(words[j + 1]['text']).startswith('و'):
                cur += nv; j += 1; continue
            break
        value = total + cur
        if value == 0:
            i = j + 1; continue
        after = ' '.join(norm(w['text']) for w in words[j + 1:j + 3])
        after_ns = after.replace(' ', '')
        before = ' '.join(norm(w['text']) for w in words[max(0, i - 2):i])
        kind = 'count'
        skip = 0
        if any(norm(p) and after_ns.startswith(norm(p)) for p in PERCENT) or '%' in words[j]['text'] or \
                (j + 1 < n and '%' in words[j + 1]['text']):
            kind = 'percent'
            skip = 2 if after_ns.startswith('في') else (1 if after_ns.startswith('بال') else 0)   # don't re-read "المية" as 100
        elif any(c in after.split()[:1] for c in CURRENCY) or 'جنيه' in raw or \
                (value >= 11 or digits) and has(' '.join(w['text'] for w in words[max(0, i - 4):j + 4]), MONEY_CTX):
            kind = 'money'
        elif 'roas' in before or 'roas' in after:
            kind = 'ratio'
        out.append({'value': value, 'i0': i, 'i1': j, 'start': words[i]['start'], 'end': words[j]['end'],
                    'text': ' '.join(w['text'] for w in words[i:j + 1]), 'kind': kind})
        i = j + 1 + skip
    for a, b in zip(out, out[1:]):                          # "…كان مية وخمسين جنيه وبقى تسعين": continue the list's kind
        if b['kind'] == 'count' and a['kind'] in ('money', 'percent') and b['i0'] - a['i1'] <= 6:
            b['kind'] = a['kind']
    return out


# ------------------------------------------------------------------ roles
CUES = {
    'cta': ['اكتب', 'اكتبلي', 'ابعت', 'ابعتلي', 'كومنت', 'comment', 'تابعني', 'لينك', 'في الكومنتات'],
    'contrast': ['بس', 'لكن', 'المشكلة', 'الغلطة', 'رغم', 'بالعكس', 'مع إن'],
    'process': ['أول حاجة', 'تاني حاجة', 'تالت حاجة', 'رابع حاجة', 'أول واحدة', 'تاني واحدة', 'تالت واحدة', 'خطوة',
                'وبعدين', 'بعد كده', 'بعد كدا', 'أولا', 'تانيا', 'تالتا'],
    'example': ['تخيل', 'مثلا', 'مثلًا', 'مثال', 'لو عندك', 'يعني لو'],
    'comparison': [' ولا ', 'مقابل', ' vs ', 'أحسن من', 'أغلى', 'الأولاني', 'التاني', 'قبل', 'بعد'],
    'conclusion': ['عشان كده', 'عشان كدا', 'الخلاصة', 'النتيجة', 'الحقيقي', 'يعني في الآخر', 'فالـ', 'فالتنوع'],
}
FINANCE = {'positive': ['مبيعات', 'sales', 'ربح', 'أرباح', 'الربح', 'revenue', 'دخل', 'فاضل'],
           'negative': ['خسارة', 'خسران', 'بيخسر', 'تكلفة', 'تكاليف', 'مصاريف', 'إعلانات', 'الإعلانات', 'ads', 'شحن', 'مرتجعات', 'cpa'],
           'metric': ['roas', 'cpa', 'cpm', 'ctr', 'margin', 'هامش', 'break-even', 'breakeven', 'contribution', 'conversion']}
EMPHATIC = ['أبدًا', 'ابدا', 'دايمًا', 'دايما', 'أهم', 'اهم', 'مش', 'لازم', 'خطير', 'أكتر', 'اكتر', 'بجد']


def has(text, cues):
    """Cues present in text, matched on word boundaries (norm() drops spaces, so normalise word by word)."""
    ws = [norm(w) for w in text.split()]
    ws = [w for w in ws if w]
    t = ' ' + ' '.join(ws) + ' '
    out, seen = [], set()
    for c in cues:
        cn = ' '.join(x for x in (norm(p) for p in c.split()) if x)
        if not cn or cn in seen:          # spelling variants of one cue count once
            continue
        seen.add(cn)
        if (' ' + cn + ' ') in t or (' ' not in cn and len(cn) > 3 and any(cn in w for w in ws)):
            out.append(c)
    return out


def latin_terms(text):
    return [w for w in re.findall(r'[A-Za-z][A-Za-z\-]+', text) if len(w) > 2]


def keyword_of(text):
    """Comment keyword: an ALL-CAPS Latin word (AUDIT, PROFIT…)."""
    m = re.findall(r'\b[A-Z]{3,}\b', text)
    return m[-1] if m else None


def sentences_of(words):
    out, cur = [], []
    for k, w in enumerate(words):
        cur.append(k)
        nxt = words[k + 1]['start'] if k + 1 < len(words) else None
        if re.search(r'[.؟?!]$', w['text']) or (nxt is not None and nxt - w['end'] > 0.6):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


INTENSITY = {   # pacing presets: min scene length (s), max graphic scenes per minute, layout variety
    'low':    {'min_scene': 6.0, 'graphics_per_min': 4, 'layouts': ['top', 'bottom', 'hero'], 'captions': 'clean', 'anim': 'fade'},
    'medium': {'min_scene': 4.0, 'graphics_per_min': 8, 'layouts': ['top', 'bottom', 'pip-right', 'hero', 'pip-left'], 'captions': 'highlight', 'anim': 'spring'},
    'high':   {'min_scene': 2.5, 'graphics_per_min': 14, 'layouts': ['full', 'top', 'pip-right', 'bottom', 'half-top', 'pip-left'], 'captions': 'kinetic', 'anim': 'stamp'},
}


def classify(seg, idx, n):
    text = seg['text']
    nums = seg['numbers']
    money = [x for x in nums if x['kind'] == 'money']
    roles, reasons = [], []
    if keyword_of(text) and has(text, CUES['cta']):
        return 'cta', 0.95, 'comment keyword + call-to-action verb'
    if idx == 0:
        roles.append(('hook', 0.75, 'opening sentence'))
    if len(money) >= 2 or (money and has(text, FINANCE['negative'] + FINANCE['positive'])):
        roles.append(('data', 0.8 if len(money) >= 2 else 0.7, f'{len(money)} money value(s) + finance terms'))
    elif nums and has(text, FINANCE['metric']):
        roles.append(('data', 0.65, 'metric with a number'))
    p = has(text, CUES['process'])
    if len(p) >= 2:                                        # a real sequence needs at least two ordinal cues
        roles.append(('process', 0.75, f'sequence cues: {", ".join(p[:3])}'))
    if has(text, ['الأولاني', 'الاولاني', 'الأول ولا', 'قبل وبعد']):
        roles.append(('comparison', 0.55, 'first/second option cue'))
    if has(text, [' ولا ']) and ('؟' in text or '?' in text):
        roles.append(('comparison', 0.6, 'either/or question'))
    elif has(text, ['أحسن من', 'مقابل', 'vs']):
        roles.append(('comparison', 0.55, 'comparison cue'))
    c = has(text, CUES['contrast'])
    if c and text.split()[0].strip('،,') in [x.strip() for x in CUES['contrast']] + ['بس', 'لكن']:
        roles.append(('contrast', 0.6, f'starts with {c[0]}'))
    e = has(text, CUES['example'])
    if e:
        roles.append(('example', 0.6, f'example cue: {e[0]}'))
    cc = has(text, CUES['conclusion'])
    if cc and idx >= n * 0.5:
        roles.append(('conclusion', 0.6, f'conclusion cue: {cc[0]}'))
    if not roles:
        emph = has(text, EMPHATIC)
        if len(text.split()) <= 9 and (emph or '!' in text):
            return 'emphasis', 0.5, f'short emphatic line ({emph[0] if emph else "!"})'
        return 'setup', 0.35, 'no strong cue'
    return max(roles, key=lambda r: r[1])


TREATMENT = {   # role → (style, component, reason)
    'hook': ('editorial', 'headline+statcard', 'hook: earn the first 3 seconds'),
    'data': ('data', 'statcards/equation', 'financial values → animated stat cards'),
    'process': ('whiteboard', 'numbered', 'step-by-step → numbered whiteboard'),
    'comparison': ('split', 'versus', 'two options → split-screen'),
    'contrast': ('kinetic', 'kinetic', 'turn in the argument → kinetic words'),
    'emphasis': ('kinetic', 'kinetic', 'strong line → kinetic words'),
    'example': ('editorial', 'pill+statcard', 'example → labelled مثال card'),
    'conclusion': ('kinetic', 'kinetic', 'payoff → kinetic words'),
    'cta': ('editorial', 'cta', 'call to action → high-contrast keyword'),
    'setup': ('talking-head', None, 'low confidence → clean talking head'),
}


def plan(words, intensity='medium'):
    P = INTENSITY[intensity]
    sents = sentences_of(words)
    segs = []
    for k, idx in enumerate(sents):
        ws = [words[i] for i in idx]
        text = ' '.join(w['text'] for w in ws)
        nums = numbers(ws)
        lat = latin_terms(text)
        seg = {'start': round(ws[0]['start'], 2), 'end': round(ws[-1]['end'], 2), 'text': text, 'w0': idx[0], 'w1': idx[-1],
               'lang': 'mixed' if lat else 'ar', 'numbers': nums,
               'keywords': sorted(set(lat + has(text, FINANCE['metric'] + FINANCE['negative'] + FINANCE['positive'])))[:6]}
        role, conf, why = classify(seg, k, len(sents))
        seg.update(role=role, confidence=round(conf, 2), reason=why)
        segs.append(seg)
    # pacing: merge short neighbours with the same role; protect breathing room
    def absorb(m, s):
        if s['confidence'] > m['confidence']:
            m.update(role=s['role'], reason=s['reason'])
        m.update(end=s['end'], text=m['text'] + ' ' + s['text'], w1=s['w1'], numbers=m['numbers'] + s['numbers'],
                 keywords=sorted(set(m['keywords'] + s['keywords']))[:6], confidence=max(m['confidence'], s['confidence']))

    # a first ordinal ("أول حاجة") opens a list when another ordinal follows within 15 s
    for k, sg in enumerate(segs):
        if sg['role'] not in ('cta', 'data') and has(sg['text'], ['أول حاجة', 'أول واحدة', 'أولا']):
            if any(has(o['text'], CUES['process']) for o in segs[k + 1:k + 5] if o['start'] - sg['end'] < 15):
                sg.update(role='process', confidence=0.75, reason='ordinal list (first + later ordinals)')
    ORDINALS = [c for c in CUES['process'] if c.split()[0] in ('أول', 'تاني', 'تالت', 'رابع') or c in ('أولا', 'تانيا', 'تالتا')]
    CONT = {'process': ORDINALS, 'comparison': ['تاني', 'التاني', 'التانية']}
    merged = []
    for s in segs:
        if s['role'] != 'cta':
            # a later cue continues an open list/comparison: pull everything since it started back into it
            hit = None
            for k in range(len(merged) - 1, -1, -1):
                m = merged[k]
                if s['start'] - m['end'] > 10 or m['role'] == 'cta':
                    break
                if m['role'] in CONT and has(s['text'], CONT[m['role']]):
                    hit = k; break
            if hit is not None:
                for x in merged[hit + 1:]:
                    absorb(merged[hit], x)
                role = merged[hit]['role']
                absorb(merged[hit], s)
                merged[hit]['role'] = role
                del merged[hit + 1:]
                continue
        prev = merged[-1] if merged else None
        if prev and prev['role'] != 'cta' and s['role'] != 'cta' and s['role'] == prev['role']:
            absorb(prev, s)
            continue
        merged.append(dict(s))
    # minimum scene length (pacing preset): fold short scenes into the stronger neighbour (CTA stays separate)
    changed = True
    while changed:
        changed = False
        for k, s in enumerate(merged):
            if s['role'] == 'cta' or s['end'] - s['start'] >= P['min_scene'] or len(merged) == 1:
                continue
            nb = [j for j in (k - 1, k + 1) if 0 <= j < len(merged) and merged[j]['role'] != 'cta']
            if not nb:
                continue
            # a long plain neighbour lends only the time needed (split at a word boundary), so a visual scene
            # never stretches over a long stretch of plain talking
            plain = [j for j in nb if merged[j]['role'] == 'setup']
            if plain and s['role'] != 'setup':
                j = plain[0]
                need = P['min_scene'] - (s['end'] - s['start'])
                m = merged[j]
                if m['end'] - m['start'] - need >= P['min_scene']:
                    if j > k:   # take from the start of the following plain scene
                        cut = next((i for i in range(m['w0'], m['w1'] + 1) if words[i]['start'] - m['start'] >= need), m['w1'])
                        moved = words[m['w0']:cut]
                        if moved:
                            s.update(end=moved[-1]['end'], w1=cut - 1, text=s['text'] + ' ' + ' '.join(w['text'] for w in moved))
                            m.update(start=words[cut]['start'], w0=cut, text=' '.join(w['text'] for w in words[cut:m['w1'] + 1]))
                    else:       # take from the end of the preceding plain scene
                        cut = next((i for i in range(m['w1'], m['w0'] - 1, -1) if m['end'] - words[i]['start'] >= need), m['w0'])
                        moved = words[cut:m['w1'] + 1]
                        if moved and cut > m['w0']:
                            s.update(start=moved[0]['start'], w0=cut, text=' '.join(w['text'] for w in moved) + ' ' + s['text'])
                            m.update(end=words[cut - 1]['end'], w1=cut - 1, text=' '.join(w['text'] for w in words[m['w0']:cut]))
                    s['start'], s['end'] = round(s['start'], 2), round(s['end'], 2)
                    m['start'], m['end'] = round(m['start'], 2), round(m['end'], 2)
                    if s['end'] - s['start'] >= P['min_scene'] - 0.05:
                        changed = True
                        break
            j = plain[0] if plain and s['role'] != 'setup' else max(nb, key=lambda j: merged[j]['confidence'])
            keep_role = s['role'] if merged[j]['role'] == 'setup' else merged[j]['role']
            keep = s if merged[j]['role'] == 'setup' else merged[j]
            a, b = (merged[j], s) if j < k else (s, merged[j])
            absorb(a, b)
            a.update(role=keep_role, reason=keep['reason'], confidence=keep['confidence'])
            merged.remove(b)
            changed = True
            break
    # budget: graphic scenes per minute, minimum scene length; weakest scenes fall back to talking head
    dur = (words[-1]['end'] - words[0]['start']) if words else 0
    budget = max(1, int(P['graphics_per_min'] * dur / 60 + 0.5))
    ranked = sorted([s for s in merged if s['role'] != 'setup'], key=lambda s: -s['confidence'])
    keep = {id(s) for s in ranked[:budget]} | {id(s) for s in merged if s['role'] in ('hook', 'cta')}
    for s in merged:
        style, comp, why = TREATMENT[s['role']]
        if s['confidence'] < 0.45:
            style, comp, why = 'talking-head', None, 'low confidence → clean talking head'
        elif id(s) not in keep:
            style, comp, why = 'talking-head', None, 'over the graphics budget → clean talking head'
        s.update(style=style, component=comp, treatment_reason=why)
    return {'intensity': intensity, 'budget': {'graphic_scenes': budget, 'min_scene': P['min_scene'], 'duration': round(dur, 1)},
            'segments': merged}


# ------------------------------------------------------------------ draft scenes
LABELS = [('ميزانية', ['budget', 'ميزانيه']), ('مبيعات', ['مبيعات', 'sales', 'بيبيع', 'يبيع']), ('إعلانات', ['اعلانات', 'ads', 'صرف']),
          ('تكاليف', ['تكلفه', 'تكاليف', 'مصاريف', 'بضاعه']), ('ربح', ['ربح', 'فاضل']), ('خسارة', ['خساره', 'خسران', 'بيخسر']),
          ]


TONE_OF = {'مبيعات': 'positive', 'ربح': 'positive', 'إعلانات': 'negative', 'تكاليف': 'negative', 'خسارة': 'negative',
           'ميزانية': 'neutral'}


def money_label(words, nb):
    ctx = ' '.join(norm(w['text']) for w in words[max(0, nb['i0'] - 5):nb['i1'] + 3])
    for lab, keys in LABELS:
        if any(k in ctx for k in keys):
            return lab
    return 'المبلغ'


FILLERS = {'هي', 'هو', 'الـ', 'ال', 'ان', 'إن', 'انه', 'إنه', 'يعني', 'بقى', 'كمان', 'حاجة', 'حاجه', 'لازم', 'تبقى',
           'لو', 'فيه', 'في', 'عارف', 'إنه', 'إنك', 'انك', 'أصلًا', 'اصلا', 'بتاعك'}


def step_name(ws):
    """Name a list step with the speaker's own words: first English term (with الـ if he said it), else the first
    two non-filler words. Never invents text."""
    for k, w in enumerate(ws):
        if re.search(r'[A-Za-z]', w):
            j = k
            while j + 1 < len(ws) and re.search(r'^[A-Za-z]', ws[j + 1]) and j - k < 2:
                j += 1
            pre = 'الـ ' if k and ws[k - 1] in ('الـ', 'ال') else ''
            return pre + ' '.join(ws[k:j + 1]).rstrip('.،,؛')
    real = [w for w in ws if w.strip('.،,؛') not in FILLERS]
    return ' '.join(real[:2]).rstrip('.،,؛') or ' '.join(ws[:2])


def phrase_len(ws, lo=4, hi=10):
    """Words for a kinetic line: up to the first natural break (punctuation) between lo and hi words."""
    for k in range(min(hi, len(ws))):
        if k + 1 >= lo and re.search(r'[.،,؛؟?!]$', ws[k]['text']):
            return k + 1
    return min(hi if len(ws) > hi else len(ws), len(ws))


def anchor_for(words, i):
    """A short exact anchor for word i (single token is enough for build's anchor search after the scene start)."""
    return words[i]['text']


def draft_scenes(pl, words, brand='media-buying', cta_keyword=None):
    P = INTENSITY[pl['intensity']]
    layouts = P['layouts']
    scenes, li = [], 0
    for k, s in enumerate(pl['segments']):
        ws = words[s['w0']:s['w1'] + 1]
        sc = {'id': f'{s["role"]}-{k + 1}', 'title': f'{s["role"]} ({s["confidence"]})', 'elements': [],
              '_plan': {'role': s['role'], 'confidence': s['confidence'], 'reason': s['reason'], 'treatment': s['treatment_reason']}}
        if k:
            sc['start'] = {'at': ws[0]['text'], 'after': round(max(0, s['start'] - 0.3), 2)}
        st = s['style']
        if st == 'talking-head':
            sc['layout'] = 'hero'
        elif s['role'] == 'cta':
            sc['layout'] = 'top'
            kw = keyword_of(s['text']) or cta_keyword or 'AUDIT'
            kw_i = next((i for i, w in enumerate(ws) if kw in w['text']), 0)
            sc['elements'].append({'type': 'cta', 'keyword': kw, 'x': 540, 'y': 160, 'in': anchor_for(ws, max(0, kw_i - 1)), 'anim': P['anim']})
        elif st == 'data':
            sc['layout'] = 'pip-right'
            money = [nb for nb in s['numbers'] if nb['kind'] in ('money', 'ratio', 'percent')][:4]
            for j, nb in enumerate(money):
                lab = money_label(ws, nb)
                tone = TONE_OF.get(lab, 'neutral')
                unit = 'ج' if nb['kind'] == 'money' else ('%' if nb['kind'] == 'percent' else '')
                sc['elements'].append({'type': 'statcard', 'label': lab, 'value': nb['value'], 'unit': unit, 'tone': tone,
                                       'count': nb['kind'] == 'money', 'x': 540 if len(money) == 1 else (790 if j % 2 == 0 else 290),
                                       'y': 200 + (j // 2) * 280, 'size': 70, 'in': anchor_for(ws, nb['i0']), 'anim': 'spring'})
        elif st == 'whiteboard':
            sc['layout'] = layouts[li % len(layouts)]; li += 1
            steps, cur = [], None
            skip = 0
            for i, w in enumerate(ws):
                if skip:
                    skip -= 1; continue
                pair = w['text'] + ' ' + (ws[i + 1]['text'] if i + 1 < len(ws) else '')
                cue = has(pair, CUES['process'])
                if cue and has(w['text'] + ' x', [c.split()[0] + ' x' for c in cue]) or (cue and len(cue[0].split()) == 1):
                    if cur:
                        steps.append(cur)
                    cur = {'i': i, 'words': []}
                    skip = len(cue[0].split()) - 1           # don't keep "حاجة"/"واحدة" of the cue as content
                elif cur is not None and len(cur['words']) < 6:
                    cur['words'].append(w['text'])
            if cur:
                steps.append(cur)
            steps = [x for x in steps if x['words']][:5]
            if steps:
                sc['elements'].append({'type': 'numbered', 'x': 540, 'y': 150, 'gap': 150,
                                       'steps': [{'text': step_name(x['words']), 'in': anchor_for(ws, x['i'])} for x in steps]})
            else:
                st = 'kinetic'
        elif st == 'split':
            sc['layout'] = 'half-top'
            i_or = next((i for i, w in enumerate(ws) if norm(w['text']) == 'ولا'), None)
            if i_or:
                a = ' '.join(w['text'] for w in ws[max(0, i_or - 2):i_or])
                b = ' '.join(w['text'] for w in ws[i_or + 1:i_or + 3]).rstrip('؟?')
                sc['elements'].append({'type': 'versus', 'x': 540, 'y': 420, 'h': 520,
                                       'a': {'title': a, 'color': 'blue', 'in': anchor_for(ws, max(0, i_or - 2))},
                                       'b': {'title': b, 'color': 'red', 'in': anchor_for(ws, i_or + 1)}})
            else:
                st = 'kinetic'
        if st in ('kinetic', 'editorial') and not sc['elements']:
            sc['layout'] = layouts[li % len(layouts)]; li += 1
            n = phrase_len(ws)
            emph = next((w['text'] for w in ws if has(w['text'], EMPHATIC + FINANCE['metric'] + FINANCE['negative'])), None)
            sc['elements'].append({'type': 'kinetic', 'from': ws[0]['text'], 'count': n, 'intensity': pl['intensity'],
                                   'emphasis': [emph] if emph else [], 'x': 540, 'y': 380, 'size': 92, 'w': 920})
            money = [nb for nb in s['numbers'] if nb['kind'] == 'money'][:1]
            if s['role'] in ('hook', 'example') and money:
                nb = money[0]
                lab = money_label(ws, nb)
                sc['elements'].append({'type': 'statcard', 'label': lab, 'value': nb['value'], 'tone': TONE_OF.get(lab, 'neutral'),
                                       'x': 540, 'y': 640, 'size': 72, 'in': anchor_for(ws, nb['i0']), 'anim': 'spring'})
            if s['role'] == 'example':
                sc['elements'].append({'type': 'pill', 'text': 'مثال', 'color': 'blue', 'x': 540, 'y': 60, 'size': 36, 'in': {'rel': 0.05}})
        scenes.append(sc)
    if scenes:
        scenes[0].setdefault('layout', 'full' if pl['intensity'] == 'high' else 'top')
    return {'mode': 'B', 'brand': brand, 'words': 'words.json', 'audio': 'build/cut_audio.m4a', 'captions': True,
            'caption_style': P['captions'],
            'caption_keywords': sorted({k for s in pl['segments'] for k in s['keywords'] if len(k) > 2})[:8],
            'scenes': scenes}


def plan_markdown(pl, title=''):
    rows = ['| # | time | role | conf | treatment | numbers | text |', '|---|---|---|---|---|---|---|']
    for i, s in enumerate(pl['segments']):
        nums = ', '.join(f'{x["value"]:,.0f}{"%" if x["kind"] == "percent" else ""}' for x in s['numbers']) or '—'
        txt = s['text'] if len(s['text']) < 90 else s['text'][:87] + '…'
        rows.append(f'| {i + 1} | {s["start"]:.1f}–{s["end"]:.1f} | {s["role"]} | {s["confidence"]} | '
                    f'{s["style"]}{(" / " + s["component"]) if s["component"] else ""} — {s["treatment_reason"]} | {nums} | {txt} |')
    b = pl['budget']
    return (f'# Edit plan {title}\n\nIntensity **{pl["intensity"]}** · {b["duration"]} s · graphic-scene budget {b["graphic_scenes"]} · '
            f'min scene {b["min_scene"]} s\n\nRoles and treatments are proposals (rule-based, confidence 0–1). Claude reviews and '
            f'refines before `scenes.json` is written; every number below was heard in the transcript.\n\n' + '\n'.join(rows) + '\n')
