"""Heuristic draft of the verification method per requirement.

The four classic methods used in space-project verification planning (cf. ECSS-E-ST-10-02)
are Test (T), Analysis (A, incl. similarity), Review of design (R) and Inspection (I).
This module scores keyword cues for each method and proposes a primary and optional
secondary method with a short rationale. Output is a DRAFT for engineer review.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .models import Requirement, Verification

# (regex, weight, cue description)
CUES: Dict[str, List[Tuple[str, int, str]]] = {
    "Test": [
        (r"\b(?:vibration|shock|thermal[- ]vacuum|tvac|thermal cycling|emc|esd|acoustic|bake-?out)\b", 5, "environmental test condition"),
        (r"\bwithstand|survive\b", 3, "environmental survival"),
        (r"\b(?:transmit|receive|downlink|uplink|telemetry|telecommand|command|data rate|bit rate|ber)\b", 3, "functional/RF behaviour"),
        (r"\b(?:within|in less than|no later than)\s+\d+(?:\.\d+)?\s*(?:ms|s|sec|seconds|min|minutes)\b", 4, "measurable timing"),
        (r"\b(?:shall\s+(?:detect|respond|switch|boot|reboot|reset|deploy|power|enter|recover|execute|store|acquire|measure|regulate|charge|provide|operate|perform|point|maintain))\b", 2, "observable function"),
        (r"\b\d+(?:\.\d+)?\s*(?:w|mw|v|mv|a|ma|hz|khz|mhz|ghz|dbm|dbw|db|kbps|mbps|bps|°c|k|gb|mb)\b", 2, "measurable physical quantity"),
        (r"\b\d+(?:\.\d+)?\s*(?:deg/s|°/s|deg|°|arcsec)(?!\w)", 2, "measurable angle/rate"),
        (r"\b(?:accuracy|stability|ripple|efficiency|output|voltage|current|power consumption)\b", 1, "performance parameter"),
        (r"\bsoftware\b.*\b(?:shall\s+(?:reject|accept|log|report|time-?tag))\b", 2, "software function"),
    ],
    "Analysis": [
        (r"\b(?:lifetime|life time|mission duration|years?\s+in\s+orbit|on-?orbit life)\b", 4, "lifetime (cannot be fully tested)"),
        (r"\b(?:reliability|probability|mtbf|failure rate|fmeca|fmea|single point failure)\b", 5, "reliability/probability"),
        (r"\b(?:radiation|total ionising dose|total ionizing dose|tid|see|seu|latch-?up|krad)\b", 3, "radiation environment"),
        (r"\b(?:de-?orbit|re-?ent(?:er|ry)|debris|detumbl\w*|casualty|25 years|orbital decay|collision)\b", 5, "orbital/debris analysis"),
        (r"\b(?:budget|margin|worst[- ]case|end of life|eol|beginning of life|bol)\b", 3, "budget/margin/worst case"),
        (r"\b(?:coverage|revisit|link budget|eclipse|orbit average)\b", 3, "mission/orbit analysis"),
        (r"\b(?:stiffness|first eigenfrequency|natural frequency|stress|safety factor)\b", 3, "structural analysis"),
        (r"\bsimilarity|heritage|qualified by similarity\b", 3, "similarity"),
    ],
    "Inspection": [
        (r"\b(?:label(?:led|ed)?|marked|marking|identified with|serial number|colou?r)\b", 5, "physical marking"),
        (r"\b(?:dimension|envelope|footprint|length|width|height|volume)\b", 3, "dimensions"),
        (r"\bmass\b|\bweigh", 3, "mass (measured/weighed)"),
        (r"\b(?:connector|fastener|harness|keyed|remove before flight|rbf|access port|test port)\b", 3, "physical feature"),
        (r"\b(?:made of|material|finish|coating|cleanliness|workmanship|solder)\b", 3, "material/workmanship"),
        (r"\b(?:shall be (?:provided with|equipped with|fitted with)|shall have)\b", 2, "presence of a feature"),
        (r"\b(?:delivered|delivery|documentation|data package|user manual|log ?book)\b", 3, "deliverable item"),
    ],
    "Review of design": [
        (r"\b(?:shall be designed|design shall|by design|designed to)\b", 5, "design feature"),
        (r"\b(?:comply|compliant|conform|in accordance with|according to|iaw)\b", 4, "standard compliance"),
        (r"\b(?:redundan(?:t|cy)|fail-?safe|fault toleran(?:t|ce)|inhibit|single point)\b", 3, "architecture property"),
        (r"\b(?:shall use|implemented (?:in|using|with)|architecture|modular|interface control|icd)\b", 3, "design/implementation choice"),
        (r"\b(?:coding standard|source code|programming language|software shall be written)\b", 4, "software design/code"),
        (r"\b(?:maintainab|extensib|upgrad|scalab|portab)\w*\b", 3, "design quality attribute"),
        (r"\b(?:shall not use|prohibited|forbidden)\b", 2, "design prohibition"),
    ],
}

SHORT = {"Test": "T", "Analysis": "A", "Inspection": "I", "Review of design": "R"}


def score_methods(text: str) -> Dict[str, Tuple[int, List[str]]]:
    low = text.lower()
    out = {}
    for method, cues in CUES.items():
        s = 0
        why = []
        for pat, w, desc in cues:
            if re.search(pat, low):
                s += w
                why.append(desc)
        out[method] = (s, why)
    return out


def draft_verification(req: Requirement) -> Verification:
    scores = score_methods(req.text)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1][0], list(SHORT).index(kv[0])))
    (m1, (s1, why1)), (m2, (s2, why2)) = ranked[0], ranked[1]
    if s1 == 0:
        return Verification(req.id, "Review of design", None,
                            "No strong cue found; defaulting to Review of design. Engineer to confirm.")
    secondary = m2 if s2 >= 3 and s2 >= s1 * 0.5 else None
    rationale = f"{m1}: {', '.join(why1)}"
    if secondary:
        rationale += f". Secondary {secondary}: {', '.join(why2)}"
    return Verification(req.id, m1, secondary, rationale)


def draft_all(reqs: List[Requirement]) -> List[Verification]:
    return [draft_verification(r) for r in reqs]
