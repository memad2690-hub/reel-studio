"""Word timings, Arabic-safe anchors, script alignment and caption chunking."""
import json
import re
from difflib import SequenceMatcher

TASHKEEL = re.compile(r'[ؐ-ًؚ-ٰٟۖ-ۭ]')
PUNCT = re.compile(r'[^\w؀-ۿ]+', re.UNICODE)
BREAK_AFTER = ('.', '،', '…', '؟', ':', '!', '?', ',', '؛')


def norm(s):
    """Normalize Arabic/Latin text for matching: no diacritics, tatweel or punctuation, unified alef."""
    s = TASHKEEL.sub('', str(s)).replace('ـ', '')
    s = re.sub('[أإآٱ]', 'ا', s).replace('ى', 'ي')
    s = re.sub('[\u060C\u061B\u061F\u066A-\u066D\u06D4«»…]', '', s)
    return PUNCT.sub('', s).lower()


def load_words(path):
    """Load ElevenLabs STT JSON (words[] with type) or a plain list of {text,start,end}."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get('words', [])
    out = []
    for w in data:
        if w.get('type', 'word') != 'word':
            continue
        text = (w.get('text') or '').strip()
        if not text:
            continue
        if not any(c.isalnum() for c in text):
            # STT sometimes returns a lone '.' or '،' as a word: glue it to the previous word
            if out:
                out[-1]['text'] += text
            continue
        out.append({'text': text, 'start': float(w['start']), 'end': float(w['end'])})
    return out


class Anchors:
    """Resolve time specs against word timings.

    A time spec is one of:
      12.5                      absolute seconds
      "كلمة"                    first word containing this text, searched from the default 'after' time
      {"at": "كلمة", "after": 10, "nth": 2, "offset": -0.1, "edge": "end"}
      {"rel": 0.4}              seconds after the scene start
    """

    def __init__(self, words):
        self.words = words
        self.normed = [norm(w['text']) for w in words]
        self.misses = []

    def _match(self, i, token):
        w = self.normed[i]
        # tiny words (ما، في) match inside other words; require an exact token match
        return w == token if len(token) <= 2 else token in w

    def at(self, needle, after=0.0, nth=1, edge='start'):
        """First word (or consecutive-word phrase) containing the needle, starting at or after `after`."""
        tokens = [norm(t) for t in str(needle).split() if norm(t)]
        if not tokens:
            raise ValueError(f'empty anchor: {needle!r}')
        k = len(tokens)
        hits = [i for i in range(len(self.words) - k + 1)
                if self.words[i]['start'] >= after - 1e-6 and all(self._match(i + j, tokens[j]) for j in range(k))]
        if len(hits) < nth:
            self.misses.append({'anchor': needle, 'after': round(after, 2)})
            return None
        i = hits[nth - 1]
        return self.words[i]['start'] if edge == 'start' else self.words[i + k - 1]['end']

    def resolve(self, spec, scene_start=0.0, default=None):
        if spec is None:
            return default
        if isinstance(spec, (int, float)):
            return float(spec)
        if isinstance(spec, str):
            t = self.at(spec, after=scene_start)
            return default if t is None else t
        if isinstance(spec, dict):
            if 'rel' in spec:
                return scene_start + float(spec['rel'])
            after = spec.get('after', scene_start)
            if isinstance(after, str):
                after = self.at(after, after=scene_start) or scene_start
            t = self.at(spec['at'], after=after, nth=spec.get('nth', 1), edge=spec.get('edge', 'start'))
            if t is None:
                return default
            return t + float(spec.get('offset', 0))
        raise ValueError(f'bad time spec: {spec!r}')


def align_script(script_text, stt_words):
    """Give each word of an approved clean script a time from the STT words (Mode B).
    Unmatched words are interpolated between matched neighbours."""
    script = [w for w in script_text.split() if norm(w)]
    a = [norm(w) for w in script]
    b = [norm(w['text']) for w in stt_words]
    times = [None] * len(script)
    for blk in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            sw = stt_words[blk.b + k]
            times[blk.a + k] = (sw['start'], sw['end'])
    known = [i for i, t in enumerate(times) if t]
    if not known:
        raise ValueError('script and transcript share no words')
    for i, t in enumerate(times):
        if t:
            continue
        prev = max([k for k in known if k < i], default=None)
        nxt = min([k for k in known if k > i], default=None)
        if prev is None:
            s = times[nxt][0]; times[i] = (s, s)
        elif nxt is None:
            e = times[prev][1]; times[i] = (e, e)
        else:
            t0, t1 = times[prev][1], times[nxt][0]
            frac = (i - prev) / (nxt - prev)
            s = t0 + (t1 - t0) * frac
            times[i] = (s, s + max(0.05, (t1 - t0) / (nxt - prev)))
    return [{'text': w, 'start': round(t[0], 3), 'end': round(t[1], 3)} for w, t in zip(script, times)]


def map_through_cuts(words, segments):
    """Map raw-footage word times into the edited timeline given kept [start,end] segments."""
    out, offset = [], 0.0
    for s, e in segments:
        for w in words:
            mid = (w['start'] + w['end']) / 2
            if s <= mid < e:
                out.append({'text': w['text'],
                            'start': round(max(w['start'], s) - s + offset, 3),
                            'end': round(min(w['end'], e) - s + offset, 3)})
        offset += e - s
    return out


def chunk_captions(words, min_words=2, max_words=4, max_gap=0.6, max_chars=26, orphan_slack=1):
    """Caption chunks built per clause from that clause's own words (never by time window):
    clauses end at punctuation or pauses; each clause is split into balanced chunks of at most
    max_words words / max_chars characters, so a 4-word clause becomes 2+2, not 3+1.
    orphan_slack lets a clause of max_words+slack words stay on one line (Mode A only)."""
    clauses, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt is None or w['text'].endswith(BREAK_AFTER) or nxt['start'] - w['end'] > max_gap:
            clauses.append(cur); cur = []
    if cur:
        clauses.append(cur)

    def chars(ws):
        return len(' '.join(x['text'] for x in ws))

    chunks = []
    for c in clauses:
        if len(c) <= max_words + orphan_slack and chars(c) <= max_chars:
            chunks.append(c); continue
        n = max(-(-len(c) // max_words), -(-chars(c) // max_chars))
        while True:
            size = -(-len(c) // n)
            parts = [c[k:k + size] for k in range(0, len(c), size)]
            if all(chars(p) <= max_chars for p in parts) or size == 1:
                break
            n += 1
        chunks.extend(parts)
    caps = []
    for i, c in enumerate(chunks):
        end = c[-1]['end'] + 0.25
        if i + 1 < len(chunks):
            end = min(end, chunks[i + 1][0]['start'])
        text = ' '.join(w['text'] for w in c).rstrip('.،,؛')
        caps.append({'start': round(c[0]['start'], 3), 'end': round(end, 3), 'text': text})
    return caps
