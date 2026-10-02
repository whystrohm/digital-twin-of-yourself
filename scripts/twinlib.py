"""Shared text handling for the twin scripts.

Standard library only. No network access. Every function here is
deterministic: the same input gives the same output, byte for byte.
"""

import hashlib
import json
import os
import re
import statistics

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TEXT_EXTENSIONS = (".md", ".txt")

# ---------------------------------------------------------------- redaction

# Redaction runs on raw text at load time, before any counting, so no
# email, phone number or money figure can reach patterns.json, a report,
# a snippet or a repeated-phrase list.
# Markdown emphasis characters are allowed inside the local part, so
# "**bob**@example.com" is caught before cleaning turns it into an address.
_EMAIL = re.compile(r"[A-Za-z0-9._%+*~`-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_EXT = r"(?:\s?(?:x|ext\.?)\s?\d{1,6})?"
_PHONE = re.compile(
    # +44 20 7946 0958, +1 (617) 555-0100: a plus, then digit groups split by separators
    r"(?<![\w$])\+\d{1,3}(?:[\s.-]\(?\d{1,4}\)?){2,5}" + _EXT + r"(?!\d|\.\d)"
    # (617) 555-0100, 617.555.0100x22, 6175550100
    r"|(?<![\w$.])(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}" + _EXT + r"(?!\d|\.\d)"
    # 555-1234
    r"|(?<![\w$.-])\d{3}-\d{4}(?![\d-])",
    re.IGNORECASE,
)


def _phone_sub(m):
    # A real number has at least 7 digits. This keeps scores like +21.9 intact.
    return REDACTION_TOKENS["phone"] if len(re.sub(r"\D", "", m.group(0))) >= 7 else m.group(0)


_CURRENCY_SIGNS = "$\u20ac\u00a3\u00a5\u20b9\u20a9\u20bd\u20ba\u20aa\u20a6\u20b1"
_AMOUNT = r"\d[\d,]*(?:\.\d+)?"
_SCALE = r"(?:\s?(?:k|m|mm|bn|million|billion|thousand)\b)?"
_MONEY = re.compile(
    r"[" + _CURRENCY_SIGNS + r"]\s?" + _AMOUNT + _SCALE
    + r"|\b(?:USD|EUR|GBP|CAD|AUD|JPY|INR|CHF|CNY)\s?" + _AMOUNT + _SCALE
    + r"|\b" + _AMOUNT + r"\s?(?:dollars?|usd|eur|euros?|gbp|pounds?|yen|rupees?)\b",
    re.IGNORECASE,
)

REDACTION_TOKENS = {
    "email": "[redacted-email]",
    "phone": "[redacted-phone]",
    "amount": "[redacted-amount]",
}


def redact(text, counts=None):
    """Replace emails, phone numbers and money amounts. Updates counts."""
    for kind, pattern in (("email", _EMAIL), ("phone", _PHONE), ("amount", _MONEY)):
        repl = _phone_sub if kind == "phone" else REDACTION_TOKENS[kind]
        before = text
        text = pattern.sub(repl, text)
        n = text.count(REDACTION_TOKENS[kind]) - before.count(REDACTION_TOKENS[kind])
        if counts is not None and n:
            counts[kind] = counts.get(kind, 0) + n
    return text


# ---------------------------------------------------------------- lexicons


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_lexicon(path=None):
    return load_json(path or os.path.join(DATA_DIR, "lexicon.json"))


def load_metaphors(path=None):
    data = load_json(path or os.path.join(DATA_DIR, "metaphors.json"))
    families = data.get("families")
    if not isinstance(families, dict) or not families:
        raise ValueError("metaphor file needs a non-empty 'families' object")
    return {name: [w.lower() for w in words] for name, words in sorted(families.items())}


# ---------------------------------------------------------------- markdown


_FENCE = re.compile(r"^\s*(```|~~~)")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+")
_QUOTE = re.compile(r"^\s*>\s?")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_RULE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_URL = re.compile(r"https?://\S+|www\.\S+")
_INLINE_CODE = re.compile(r"`[^`]*`")
_HTML_TAG = re.compile(r"<[^>]+>")
_EMPHASIS = re.compile(r"(\*\*|__|\*|_)(?=\S)(.+?)(?<=\S)\1")


def classify_lines(text):
    """Split text into lines and tag each one.

    Returns a list of dicts: {"no": 1-based line number, "raw": str,
    "kind": "blank"|"code"|"frontmatter"|"heading"|"list"|"table"|"text",
    "clean": str}. "clean" is the prose with markdown syntax removed.
    """
    lines = text.split("\n")
    out = []
    in_code = False
    in_front = bool(lines) and lines[0].strip() == "---"
    in_comment = False
    for i, raw in enumerate(lines):
        no = i + 1
        stripped = raw.strip()
        if in_front:
            out.append({"no": no, "raw": raw, "kind": "frontmatter", "clean": ""})
            if i > 0 and stripped in ("---", "..."):
                in_front = False
            continue
        if _FENCE.match(raw):
            in_code = not in_code
            out.append({"no": no, "raw": raw, "kind": "code", "clean": ""})
            continue
        if in_code:
            out.append({"no": no, "raw": raw, "kind": "code", "clean": ""})
            continue
        if in_comment or stripped.startswith("<!--"):
            in_comment = "-->" not in stripped
            out.append({"no": no, "raw": raw, "kind": "code", "clean": ""})
            continue
        if not stripped:
            out.append({"no": no, "raw": raw, "kind": "blank", "clean": ""})
            continue
        if _TABLE_RULE.match(raw):
            out.append({"no": no, "raw": raw, "kind": "table", "clean": ""})
            continue
        kind = "text"
        body = raw
        if _HEADING.match(body):
            kind = "heading"
            body = _HEADING.sub("", body)
        elif _LIST_ITEM.match(body):
            kind = "list"
            body = _LIST_ITEM.sub("", body)
        elif _TABLE_ROW.match(body):
            kind = "table"
            body = body.replace("|", " ")
        body = _QUOTE.sub("", body)
        # Redact again after cleaning: removing markdown can join an address.
        out.append({"no": no, "raw": raw, "kind": kind, "clean": redact(clean_inline(body))})
    return out


def clean_inline(s):
    s = _IMAGE.sub(" ", s)
    s = _LINK.sub(r"\1", s)
    s = _URL.sub(" ", s)
    s = _INLINE_CODE.sub(" ", s)
    s = _HTML_TAG.sub(" ", s)
    for _ in range(2):
        s = _EMPHASIS.sub(r"\2", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- sentences

_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")
_ABBREV = {
    "e.g", "i.e", "etc", "vs", "mr", "mrs", "ms", "dr", "inc", "ltd", "co",
    "jr", "sr", "st", "no", "fig", "approx", "dept", "est", "u.s", "a.m", "p.m",
}
_END = re.compile(r"[.!?]+[\"'”’)\]]*(?=\s|$)")


REDACTED_WORD = "__redacted__"
_REDACTED_TOKEN = re.compile(r"\[redacted-(?:email|phone|amount)\]")


def words(s):
    """Word tokens. A redaction placeholder becomes one REDACTED_WORD token,
    so it counts as one word and never forms part of a phrase."""
    parts = _REDACTED_TOKEN.split(s)
    out = []
    for i, part in enumerate(parts):
        if i:
            out.append(REDACTED_WORD)
        out.extend(_WORD.findall(part))
    return out


def split_sentences(lines):
    """Turn classified lines into sentences.

    Paragraph lines join into one block. Each list item and table row is
    its own block. Headings are skipped: they are labels, not sentences.
    Returns dicts {"text", "line", "words": int, "end": "." | "?" | "!" | ""}.
    """
    blocks = []
    current = []
    for ln in lines:
        kind = ln["kind"]
        if kind == "text":
            current.append(ln)
            continue
        if current:
            blocks.append(current)
            current = []
        if kind in ("list", "table") and ln["clean"]:
            blocks.append([ln])
    if current:
        blocks.append(current)

    sentences = []
    for block in blocks:
        text = ""
        offsets = []  # (start offset in text, line number)
        for ln in block:
            if text:
                text += " "
            offsets.append((len(text), ln["no"]))
            text += ln["clean"]
        start = 0
        for m in _END.finditer(text):
            candidate = text[start:m.end()]
            prev = re.findall(r"([A-Za-z.]+)\.*$", text[start:m.start()])
            token = prev[0].lower().rstrip(".") if prev else ""
            if m.group(0).startswith(".") and (
                token in _ABBREV or (len(token) == 1 and token.isalpha())
            ):
                continue
            if candidate.strip():
                sentences.append(_sentence(candidate, start, offsets))
            start = m.end()
        if text[start:].strip():
            sentences.append(_sentence(text[start:], start, offsets))
    return [s for s in sentences if s["words"] > 0]


def _line_at(pos, offsets):
    line = offsets[0][1]
    for off, no in offsets:
        if off <= pos:
            line = no
    return line


def _sentence(raw, offset, offsets):
    """raw is the unstripped slice starting at offset in the block text."""
    lead = len(raw) - len(raw.lstrip())
    text = raw.strip()
    first = offset + lead
    last = first + max(len(text) - 1, 0)
    stripped = text.rstrip("\"'”’)] ")
    end = stripped[-1] if stripped and stripped[-1] in ".?!" else ""
    return {"text": text, "line": _line_at(first, offsets), "end_line": _line_at(last, offsets),
            "words": len(words(text)), "end": end}


# ---------------------------------------------------------------- matching


def phrase_regex(phrase):
    """Compile a plain phrase the way foundrkit-lint compiles a plain string.

    Case-insensitive. A word boundary is added only on a side that starts
    or ends with a word character, so a punctuation rule matches anywhere.
    """
    escaped = re.escape(phrase)
    lead = r"\b" if re.match(r"\w", phrase) else ""
    tail = r"\b" if re.search(r"\w$", phrase) else ""
    return re.compile(lead + escaped + tail, re.IGNORECASE)


def literal_regex(literal):
    """Compile a "/body/flags" regex literal. Flags: i, m, s. g is ignored.

    With no flags, matching is case-insensitive, as in foundrkit-lint.
    """
    if not (literal.startswith("/") and literal.rfind("/") > 0):
        raise ValueError("regex pattern must look like /body/flags: %r" % literal)
    last = literal.rfind("/")
    body, flags = literal[1:last], literal[last + 1:] or "gi"
    bad = set(flags) - set("gims")
    if bad:
        raise ValueError("unsupported regex flags %r in %r" % ("".join(sorted(bad)), literal))
    value = 0
    if "i" in flags:
        value |= re.IGNORECASE
    if "m" in flags:
        value |= re.MULTILINE
    if "s" in flags:
        value |= re.DOTALL
    return re.compile(body, value)


_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⭐⭕‼⁉️]"
)


def emoji_regex():
    return _EMOJI


def count_phrases(text, phrases):
    """Count each phrase in text. Returns {phrase: count} for counts > 0."""
    out = {}
    for p in phrases:
        n = len(phrase_regex(p).findall(text))
        if n:
            out[p] = n
    return out


def sentence_has_any(text, compiled):
    return any(rx.search(text) for rx in compiled)


# ---------------------------------------------------------------- files


def list_text_files(root):
    """All .md/.txt files under root, sorted, skipping hidden folders."""
    root = os.path.abspath(root)
    if os.path.isfile(root):
        return [root]
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            if name.lower().endswith(TEXT_EXTENSIONS):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def read_text(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        return fh.read().replace("\r\n", "\n").replace("\r", "\n")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def write_json(path, data):
    text = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ---------------------------------------------------------------- numbers


def rnd(x, places=3):
    return None if x is None else round(float(x), places)


def percentile(values, q):
    """Nearest-rank percentile. q in [0, 100]."""
    if not values:
        return None
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, int(-(-q * len(ordered) // 100)) - 1))
    return ordered[k]


def mean(values):
    return statistics.mean(values) if values else None


def pstdev(values):
    return statistics.pstdev(values) if len(values) > 1 else 0.0


def snippet(text, start=None, end=None, width=90):
    """A short, single-line excerpt, centred on [start, end) when given."""
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= width:
        return flat
    if start is None:
        return flat[: width - 3].rstrip() + "..."
    # Window on the original text so the offsets stay true, then flatten.
    centre = (start + (end or start)) // 2
    lo = max(0, centre - width // 2)
    hi = min(len(text), lo + width)
    lo = max(0, hi - width)
    out = re.sub(r"\s+", " ", text[lo:hi]).strip()
    head = "..." if text[:lo].strip() else ""
    tail = "..." if text[hi:].strip() else ""
    return head + out + tail
