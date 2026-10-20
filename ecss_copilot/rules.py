"""Rule-based requirement quality checks.

The rules are *inspired by* the requirement characteristics commonly expected in
space-project technical specifications (e.g. ECSS-E-ST-10-06) and by general
requirement-writing guidance (INCOSE-style): one requirement per statement, a
clear subject and mandatory "shall", no vague or unverifiable wording, no open
items, quantified values with units and so on. Wording here is our own
paraphrase; no standard text is reproduced.

Each rule returns zero or more Finding objects with a severity and a suggested fix.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Callable, Iterable, List

from .models import Finding, Requirement, SEVERITY_PENALTY

# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------

VAGUE_TERMS = [
    "adequate", "adequately", "appropriate", "appropriately", "as appropriate", "sufficient",
    "sufficiently", "suitable", "user-friendly", "user friendly", "easy", "easily", "simple",
    "fast", "quick", "quickly", "rapid", "rapidly", "timely", "efficient", "efficiently",
    "effective", "robust", "flexible", "reasonable", "reasonably", "acceptable", "normal",
    "normally", "typical", "typically", "generally", "usually", "significant", "significantly",
    "minimal", "minimum possible", "maximum possible", "optimal", "optimum", "optimise",
    "optimize", "maximise", "maximize", "minimise", "minimize", "state-of-the-art",
    "state of the art", "best practice", "high quality", "seamless", "seamlessly", "reliable",
    "reliably", "approximately", "about", "roughly", "nearly", "several", "some", "various",
    "many", "few", "large", "small", "high", "low", "good", "nominal performance", "etc",
    "and so on", "relevant", "clearly", "accurately", "precisely", "sufficiently accurate",
    "as required", "as needed", "as necessary", "where necessary", "if needed", "within limits",
    "as specified", "as defined", "user-defined", "properly", "correctly",
]

ESCAPE_CLAUSES = [
    "if possible", "where possible", "when possible", "as far as possible", "as far as practicable",
    "where practicable", "if practicable", "to the extent possible", "to the extent practicable",
    "unless otherwise", "where feasible", "if feasible", "as much as possible", "if necessary",
    "best effort", "best efforts",
]

OPEN_ITEMS = re.compile(r"\b(TBD|TBC|TBA|TBS|TBW|TBR|to be (?:determined|confirmed|defined|specified|agreed|decided))\b", re.I)

UNVERIFIABLE_ABSOLUTES = [
    "all conditions", "all circumstances", "any condition", "any conditions", "any circumstances", "at all times",
    "under all", "never", "always", "100 %", "100%", "no failure", "no failures", "zero failures",
    "fail-safe under", "without any", "without limitation", "infinite", "indefinitely",
    "completely", "totally", "fully", "every possible", "any possible", "error-free", "error free",
    "bug-free", "bug free",
]

WEAK_MODALS = ["should", "may", "might", "could", "will", "must", "can", "would", "is to", "are to",
               "is required to", "are required to", "has to", "have to", "needs to", "need to"]

OPEN_ENDED = ["etc.", "etc", "and so on", "including but not limited to", "including, but not limited to",
              "such as", "and the like", "among others", "for example", "e.g.", "i.e."]

PRONOUNS = ["it", "they", "them", "this", "these", "those", "its", "their"]

UNITS = {
    # length / area / volume
    "m", "km", "mm", "cm", "um", "µm", "nm", "m2", "m²", "cm3", "l", "u",  # U = CubeSat unit
    # time
    "s", "sec", "secs", "second", "seconds", "ms", "us", "µs", "ns", "min", "mins", "minute", "minutes",
    "h", "hr", "hrs", "hour", "hours", "day", "days", "week", "weeks", "month", "months", "year",
    "years", "orbit", "orbits",
    # mass / force / pressure / energy
    "kg", "g", "mg", "n", "nm", "mnm", "pa", "kpa", "mpa", "hpa", "bar", "mbar", "torr", "j", "kj",
    "wh", "mwh", "kwh", "ah", "mah", "grms", "g_rms", "g²/hz", "g2/hz", "gy", "krad", "rad", "mev",
    # electrical / rf
    "w", "mw", "kw", "v", "mv", "kv", "a", "ma", "µa", "ua", "ohm", "ohms", "ω", "mω", "kω", "hz",
    "khz", "mhz", "ghz", "db", "dbm", "dbw", "dbi", "dbic", "db/k", "dbhz", "f", "µf", "uf", "nf", "pf",
    # data
    "bit", "bits", "byte", "bytes", "b", "kb", "mb", "gb", "tb", "kbit", "mbit", "gbit", "bps",
    "kbps", "mbps", "gbps", "kbit/s", "mbit/s", "bit/s", "b/s", "ber", "fps", "ppm",
    # angle / temperature / misc
    "deg", "degree", "degrees", "°", "°c", "degc", "k", "c", "rad/s", "deg/s", "°/s", "arcsec",
    "arcmin", "mrad", "µrad", "urad", "%", "percent", "sigma", "σ", "lux", "m/s", "km/s", "m/s²",
    "m/s2", "rpm", "nm/s", "x", "times", "lsb",
}

# Nouns that make a bare number a legitimate count (no physical unit needed).
COUNT_NOUNS = {
    "channel", "channels", "cycle", "cycles", "unit", "units", "satellite", "satellites", "frame",
    "frames", "packet", "packets", "command", "commands", "event", "events", "set", "sets",
    "sample", "samples", "attempt", "attempts", "retries", "retry", "copies", "copy", "panel",
    "panels", "antenna", "antennas", "antennae", "battery", "batteries", "cell", "cells", "board",
    "boards", "connector", "connectors", "port", "ports", "slot", "slots", "string", "strings",
    "sensor", "sensors", "wheel", "wheels", "axis", "axes", "mode", "modes", "operator",
    "operators", "station", "stations", "pass", "passes", "parameter", "parameters", "file",
    "files", "image", "images", "point", "points", "failure", "failures", "fault", "faults",
    "independent", "redundant", "consecutive", "level", "levels", "pixel", "pixels", "line",
    "lines", "entries", "entry", "people", "persons", "users", "watchdog", "interfaces",
    "interface", "inhibits", "inhibit", "switches", "switch", "timers", "timer", "kit", "kits",
}

# Simple irregular / common past participles to detect passive voice without NLP deps.
IRREGULAR_PARTICIPLES = {
    "built", "made", "done", "given", "taken", "kept", "held", "sent", "shown", "known", "set",
    "put", "run", "written", "driven", "chosen", "drawn", "flown", "thrown", "grown", "seen",
    "brought", "bought", "found", "met", "read", "led", "fed", "left", "lost", "paid", "said",
    "sold", "told", "understood", "withstood", "undertaken", "overridden", "hidden", "begun",
}

NUMBER_RE = re.compile(r"(?<![\w.\-/])([-+±]?\d+(?:[.,]\d+)?(?:e[-+]?\d+)?)(?![\w.\-/]*\d)", re.I)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_terms(text: str, terms: Iterable[str]) -> List[str]:
    found = []
    low = text.lower()
    for t in sorted(set(terms), key=len, reverse=True):
        pat = r"(?<![\w-])" + re.escape(t.lower()) + r"(?![\w-])"
        if re.search(pat, low):
            # avoid reporting "fast" when "as fast as" etc. are handled; keep simple
            if not any(t.lower() in f.lower() for f in found):
                found.append(t)
    return found


def _shall_count(text: str) -> int:
    return len(re.findall(r"\bshall\b", text, re.I))


def _strip_refs(text: str) -> str:
    """Remove things that contain digits but are not quantities: IDs, standards, versions, dates,
    section/figure/table refs, list numbering."""
    t = text
    t = re.sub(r"\b[A-Z]{2,}[A-Z0-9]*(?:[-_./][A-Z0-9]+)+\b", " ", t)               # IDs, ECSS-E-ST-10-06C
    t = re.sub(r"\b(?:ISO|IEC|EN|MIL|NASA|ECSS|CCSDS|IEEE|RFC|DO|NPR|GEVS)[\s-]*[\w.\-/]*\d[\w.\-/]*", " ", t, flags=re.I)
    t = re.sub(r"\b(?:section|clause|chapter|figure|fig\.|table|annex|appendix|step|issue|rev|revision|version|v)\s*\.?\s*[\d.]+[a-z]?\b", " ", t, flags=re.I)
    t = re.sub(r"\b(?:19|20)\d{2}\b", " ", t)                                        # years
    t = re.sub(r"\b\d{1,2}(?:st|nd|rd|th)\b", " ", t)                                # ordinals
    t = re.sub(r"\[[^\]]*\]", " ", t)                                                # [AD-1], [RD3]
    t = re.sub(r"\b\d+U\b", " ", t)                                                  # 3U, 6U CubeSat form factor
    t = re.sub(r"^\s*[\d.]+\s", " ", t)                                              # list numbering
    return t


def _missing_unit_numbers(text: str) -> List[str]:
    t = _strip_refs(text)
    hits = []
    for m in NUMBER_RE.finditer(t):
        num = m.group(1)
        after = t[m.end():]
        # unit attached directly (e.g. 10W, 5kg, 25°C, 3.3V, 10%)
        attached = re.match(r"([^\s,;:)\]]+)", after)
        if attached:
            tok = attached.group(1).lower().rstrip(".")
            if tok in UNITS or tok.split("/")[0] in UNITS or tok.startswith(("°", "%")):
                continue
        nxt = re.match(r"\s*([^\s,;:)\]]+)", after)
        if not nxt:
            # number at the end of a sentence
            hits.append(num)
            continue
        tok = nxt.group(1).lower().rstrip(".")
        if tok in UNITS or tok.split("/")[0] in UNITS or tok.split("-")[0] in UNITS:
            continue
        if tok in COUNT_NOUNS or tok.rstrip("s") in COUNT_NOUNS:
            continue
        # allow one or two adjectives before the counted noun ("3 switchable power lines")
        ahead = [w.lower().strip(".,;:") for w in after.split()[:4]]
        if any(w in COUNT_NOUNS for w in ahead[1:3]):
            continue
        before = t[:m.start()].lower()
        if re.search(r"\bby\s*$", before) and re.search(r"\b(?:increment|decrement)", before):
            continue
        # "x 10^3" or "to 5 V" ranges: look one more token ahead for "to/-/and" ranges
        if tok in {"to", "-", "–", "and", "or", "±", "+/-", "x", "×"}:
            nxt2 = re.match(r"\s*\S+\s*[-+±]?\d+(?:[.,]\d+)?\s*([^\s,;:)\]]+)", after)
            if nxt2:
                tok2 = nxt2.group(1).lower().rstrip(".")
                if tok2 in UNITS or tok2 in COUNT_NOUNS:
                    continue
        # "one of 2" kind of statements, or the number is part of a ratio a:b
        if re.match(r"\s*[:/]\s*\d", after):
            continue
        hits.append(num)
    return hits


def _passive_without_agent(text: str):
    """Return the fragment if a 'shall be <participle>' construction has no 'by <agent>'."""
    m = re.search(r"\bshall\s+(?:not\s+)?be\s+(\w+)", text, re.I)
    if not m:
        return None
    word = m.group(1).lower()
    if word in {"able", "capable", "compatible", "compliant", "less", "greater", "more", "within",
                "at", "in", "between", "below", "above", "lower", "higher", "equal", "no", "a", "an",
                "the", "possible", "operational", "available", "redundant", "free", "accessible",
                "independent", "smaller", "larger", "visible", "removable", "consistent", "inhibited"}:
        return None
    is_participle = word.endswith("ed") or word.endswith("en") or word in IRREGULAR_PARTICIPLES
    if not is_participle:
        return None
    rest = text[m.end():]
    if re.search(r"\bby\s+(?:the\s+)?\w+", rest, re.I):
        return None
    return m.group(0)


# ---------------------------------------------------------------------------
# Rules (each: Requirement -> list[Finding])
# ---------------------------------------------------------------------------

Rule = Callable[[Requirement], List[Finding]]
RULES: List[tuple] = []  # (rule_id, name, func)


def rule(rule_id: str, name: str):
    def deco(fn):
        RULES.append((rule_id, name, fn))
        return fn
    return deco


def _f(req, rule_id, name, sev, msg, sug, match=""):
    return Finding(req_id=req.id, rule_id=rule_id, rule_name=name, severity=sev, message=msg,
                   suggestion=sug, match=match)


@rule("RQ-01", "Missing 'shall'")
def r_missing_shall(req):
    if _shall_count(req.text) > 0:
        return []
    weak = _find_terms(req.text, ["should", "will", "must", "may", "is to", "are to", "has to", "needs to", "can"])
    detail = f" It uses '{weak[0]}' instead." if weak else ""
    return [_f(req, "RQ-01", "Missing 'shall'", "High",
               "Statement has no mandatory 'shall', so it is not clearly a binding requirement." + detail,
               "Rewrite as '<The item> shall <verb> <measurable object/condition>'. If it is information, "
               "a goal or a design description, move it out of the requirement list (or mark it as a goal).",
               weak[0] if weak else "")]


@rule("RQ-02", "Multiple 'shall' in one statement")
def r_multiple_shall(req):
    n = _shall_count(req.text)
    if n <= 1:
        return []
    return [_f(req, "RQ-02", "Multiple 'shall' in one statement", "High",
               f"Statement contains {n} 'shall' clauses; each requirement should state one single need "
               "so that it can be traced and verified on its own.",
               f"Split into {n} separate requirements, each with its own ID (e.g. {req.id}a, {req.id}b).",
               f"{n}x shall")]


@rule("RQ-03", "Vague or subjective term")
def r_vague(req):
    terms = _find_terms(req.text, VAGUE_TERMS)
    # "about" is common in "rotation about the Z axis"
    if "about" in terms and re.search(r"\babout\s+(?:the\s+)?[xyz][- ]?axis|about\s+its", req.text, re.I):
        terms.remove("about")
    # "high"/"low" in "high voltage"/"low power mode" names are often fine -> Low severity only
    if not terms:
        return []
    strong = [t for t in terms if t.lower() not in {"high", "low", "large", "small", "normal", "some", "about", "clearly"}]
    sev = "High" if strong else "Low"
    return [_f(req, "RQ-03", "Vague or subjective term", sev,
               f"Contains subjective or non-quantified wording: {', '.join(repr(t) for t in terms)}. "
               "Different readers (and the verifier) can interpret it differently.",
               "Replace each vague term with a measurable criterion: a value, unit, tolerance and the "
               "conditions under which it applies (e.g. 'within 2 s', '>= 10 dB margin').",
               ", ".join(terms))]


@rule("RQ-04", "Open item (TBD/TBC)")
def r_open_item(req):
    hits = sorted(set(m.group(0) for m in OPEN_ITEMS.finditer(req.text)))
    if not hits:
        return []
    return [_f(req, "RQ-04", "Open item (TBD/TBC)", "High",
               f"Requirement contains open item(s): {', '.join(hits)}. It cannot be verified or baselined "
               "until resolved.",
               "Record the open item in the TBD/TBC list with an owner and closure date; meanwhile state "
               "the current best estimate, e.g. '10 W (TBC)'.",
               ", ".join(hits))]


@rule("RQ-05", "Escape clause")
def r_escape(req):
    hits = _find_terms(req.text, ESCAPE_CLAUSES)
    if not hits:
        return []
    return [_f(req, "RQ-05", "Escape clause", "High",
               f"Escape clause {', '.join(repr(h) for h in hits)} makes the requirement optional in practice "
               "and impossible to fail.",
               "Remove the clause. If there are real exceptions, list them explicitly, or split into a "
               "mandatory requirement plus a separately identified goal.",
               ", ".join(hits))]


@rule("RQ-06", "Unverifiable absolute")
def r_absolute(req):
    hits = _find_terms(req.text, UNVERIFIABLE_ABSOLUTES)
    if not hits:
        return []
    return [_f(req, "RQ-06", "Unverifiable absolute", "High",
               f"Absolute wording {', '.join(repr(h) for h in hits)} cannot be demonstrated by a finite "
               "test, analysis, inspection or review.",
               "Bound the claim: state the specific conditions/environments, the duration and an acceptable "
               "probability or failure rate (e.g. 'over the 2-year mission with reliability >= 0.95').",
               ", ".join(hits))]


@rule("RQ-07", "Weak or mixed modal verb")
def r_weak_modal(req):
    if _shall_count(req.text) == 0:
        return []  # already covered by RQ-01
    # ignore "can" inside "shall be capable" etc.; check modals outside the shall clause
    hits = [h for h in _find_terms(req.text, WEAK_MODALS) if h not in {"can"}]
    if not hits:
        return []
    return [_f(req, "RQ-07", "Weak or mixed modal verb", "Medium",
               f"Mixes 'shall' with {', '.join(repr(h) for h in hits)}, which blurs what is mandatory.",
               "Use 'shall' for mandatory content only; move non-binding text (should/may/will) into a "
               "note, rationale or a separate goal.",
               ", ".join(hits))]


@rule("RQ-08", "Passive voice / missing subject")
def r_passive(req):
    out = []
    stripped = req.text.strip()
    if re.match(r"^(?:shall|must|should)\b", stripped, re.I):
        out.append(_f(req, "RQ-08", "Passive voice / missing subject", "High",
                      "Statement starts with the modal verb; the responsible item (subject) is missing.",
                      "Start with the item the requirement applies to: 'The <EPS / OBC / spacecraft> shall ...'.",
                      stripped.split()[0]))
        return out
    frag = _passive_without_agent(req.text)
    if frag:
        out.append(_f(req, "RQ-08", "Passive voice / missing subject", "Low",
                      f"Passive construction '{frag}' does not say which item performs the action.",
                      "Prefer active voice with an explicit subject: 'The <item> shall <verb> ...'.",
                      frag))
    return out


@rule("RQ-09", "Compound 'and/or'")
def r_and_or(req):
    if re.search(r"\band\s*/\s*or\b", req.text, re.I):
        return [_f(req, "RQ-09", "Compound 'and/or'", "High",
                   "'and/or' leaves it open whether one or both conditions must be met.",
                   "Decide: use 'and' (both are required, consider splitting) or 'or' (state who chooses and how).",
                   "and/or")]
    if re.search(r"\b\w+\s*/\s*\w+\b", req.text) and re.search(r"\b(?:on|off|tx|rx|tm|tc)\s*/\s*(?:on|off|tx|rx|tm|tc)\b", req.text, re.I) is None:
        m = re.search(r"\b([A-Za-z]{3,})\s*/\s*([A-Za-z]{3,})\b", req.text)
        if m and m.group(1).lower() not in {"bit", "deg", "rad"} and m.group(2).lower() not in {"hz", "sec", "s"}:
            return [_f(req, "RQ-09", "Compound 'and/or'", "Low",
                       f"Slash construction '{m.group(0)}' may hide two alternatives or two requirements.",
                       "Replace the slash with an explicit 'and' or 'or', or split the requirement.",
                       m.group(0))]
    return []


@rule("RQ-10", "Number without unit")
def r_units(req):
    hits = _missing_unit_numbers(req.text)
    if not hits:
        return []
    return [_f(req, "RQ-10", "Number without unit", "Medium",
               f"Value(s) {', '.join(hits)} have no unit of measure (or the unit could not be recognised).",
               "Add SI units (and tolerance where relevant), e.g. '5 W ± 0.5 W', '20 °C'.",
               ", ".join(hits))]


@rule("RQ-11", "Open-ended list")
def r_open_ended(req):
    hits = _find_terms(req.text, OPEN_ENDED)
    if not hits:
        return []
    return [_f(req, "RQ-11", "Open-ended list", "Medium",
               f"Open-ended wording {', '.join(repr(h) for h in hits)} leaves the scope undefined.",
               "List every item explicitly (or reference a controlled list/annex). Move examples to a note.",
               ", ".join(hits))]


@rule("RQ-12", "Negative requirement")
def r_negative(req):
    if re.search(r"\bshall\s+not\b", req.text, re.I) and not re.search(r"shall\s+not\s+(?:exceed|be\s+(?:less|more|greater|lower|higher))", req.text, re.I):
        return [_f(req, "RQ-12", "Negative requirement", "Low",
                   "Negative statements ('shall not ...') are often hard to verify exhaustively.",
                   "Where possible, state the positive required behaviour and its bounds; keep 'shall not' "
                   "for clear prohibitions with a defined verification approach.",
                   "shall not")]
    return []


@rule("RQ-13", "Statement too long")
def r_long(req):
    n = len(req.text.split())
    if n <= 45:
        return []
    return [_f(req, "RQ-13", "Statement too long", "Low",
               f"Statement has {n} words; long requirements tend to bundle several needs and conditions.",
               "Keep the requirement to one sentence (~25-40 words). Move rationale and context to a "
               "separate 'Rationale' field.",
               f"{n} words")]


@rule("RQ-14", "Ambiguous pronoun reference")
def r_pronoun(req):
    # only flag when the pronoun is not obviously anchored in the same sentence start
    hits = [p for p in _find_terms(req.text, PRONOUNS)]
    hits = [h for h in hits if h.lower() not in {"its"}]  # 'its' is usually clear
    if not hits:
        return []
    return [_f(req, "RQ-14", "Ambiguous pronoun reference", "Low",
               f"Pronoun(s) {', '.join(repr(h) for h in hits)} may refer to more than one item, "
               "especially when the requirement is read out of context.",
               "Repeat the noun the pronoun refers to.",
               ", ".join(hits))]


@rule("RQ-15", "Design solution instead of need")
def r_design(req):
    m = re.search(r"\b(?:shall\s+(?:use|be\s+implemented\s+(?:using|with|in))|using\s+an?\s+\w+\s+(?:algorithm|processor|microcontroller))\b", req.text, re.I)
    if not m:
        return []
    return [_f(req, "RQ-15", "Design solution instead of need", "Low",
               f"'{m.group(0)}' prescribes an implementation. That is fine for an imposed constraint, but "
               "otherwise it restricts design freedom and hides the real need.",
               "Check whether this is a genuine constraint (heritage, customer-imposed). If not, state the "
               "required function/performance instead and keep the solution in the design file.",
               m.group(0))]


# ---------------------------------------------------------------------------
# Document-level checks
# ---------------------------------------------------------------------------


def document_findings(reqs: List[Requirement]) -> List[Finding]:
    out: List[Finding] = []
    ids = Counter(r.id for r in reqs)
    for rid, n in ids.items():
        if n > 1:
            for r in reqs:
                if r.id == rid:
                    out.append(_f(r, "DOC-01", "Duplicate requirement ID", "High",
                                  f"ID '{rid}' is used {n} times; traceability and verification records will be ambiguous.",
                                  "Give each requirement a unique, stable identifier.", rid))
                    break
    seen = {}
    for r in reqs:
        key = re.sub(r"\W+", " ", r.text.lower()).strip()
        if key in seen:
            out.append(_f(r, "DOC-02", "Duplicate requirement text", "Medium",
                          f"Same text as {seen[key]}.",
                          "Delete the duplicate or merge them and keep a single ID.", seen[key]))
        else:
            seen[key] = r.id
    for r in reqs:
        if r.id_generated:
            out.append(_f(r, "DOC-03", "Missing requirement ID", "Medium",
                          "No identifier was found in the source; an ID was generated for this report.",
                          "Assign a unique, permanent ID in the source document (e.g. SYS-PWR-010).", r.id))
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_requirement(req: Requirement) -> List[Finding]:
    findings: List[Finding] = []
    for _rid, _name, fn in RULES:
        findings.extend(fn(req))
    return findings


def check_all(reqs: List[Requirement]) -> List[Finding]:
    findings: List[Finding] = []
    for r in reqs:
        findings.extend(check_requirement(r))
    findings.extend(document_findings(reqs))
    return findings


def quality_score(findings_for_req: List[Finding]) -> int:
    score = 100 - sum(SEVERITY_PENALTY.get(f.severity, 0) for f in findings_for_req)
    return max(0, score)


def rule_catalogue():
    cat = [{"rule_id": rid, "name": name, "doc": (fn.__doc__ or "").strip()} for rid, name, fn in RULES]
    cat += [
        {"rule_id": "DOC-01", "name": "Duplicate requirement ID", "doc": ""},
        {"rule_id": "DOC-02", "name": "Duplicate requirement text", "doc": ""},
        {"rule_id": "DOC-03", "name": "Missing requirement ID", "doc": ""},
    ]
    return cat
