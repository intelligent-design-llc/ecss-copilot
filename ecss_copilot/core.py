"""Analysis pipeline: requirements -> findings -> verification draft -> result dict."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import List

from . import __version__
from .models import Requirement, SEVERITY_ORDER
from .rules import check_all, quality_score
from .verification import draft_all

DISCLAIMER = (
    "ADVISORY ONLY. Automatically generated draft for engineering review; it does not replace "
    "engineering judgement, product-assurance review or customer approval. Human sign-off required. "
    "Do NOT upload ITAR/EAR- or otherwise export-controlled, classified or customer-confidential data "
    "you are not authorised to process."
)


def analyse(reqs: List[Requirement], source_name: str = "pasted text") -> dict:
    findings = check_all(reqs)
    verifs = {v.req_id: v for v in draft_all(reqs)}
    by_req = {}
    for f in findings:
        by_req.setdefault(f.req_id, []).append(f)
    rows = []
    for r in reqs:
        fs = sorted(by_req.get(r.id, []), key=lambda f: SEVERITY_ORDER[f.severity])
        v = verifs[r.id]
        rows.append({
            **r.to_dict(),
            "score": quality_score(fs),
            "findings": [f.to_dict() for f in fs],
            "verification": v.to_dict(),
            "llm": None,
        })
    sev = Counter(f.severity for f in findings)
    rules = Counter(f"{f.rule_id} {f.rule_name}" for f in findings)
    methods = Counter(v.primary for v in verifs.values())
    clean = sum(1 for row in rows if not row["findings"])
    return {
        "tool": f"ECSS Copilot v{__version__} (prototype)",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": source_name,
        "disclaimer": DISCLAIMER,
        "summary": {
            "requirements": len(reqs),
            "findings": len(findings),
            "requirements_with_findings": len(reqs) - clean,
            "clean_requirements": clean,
            "by_severity": {k: sev.get(k, 0) for k in ("High", "Medium", "Low")},
            "by_rule": dict(rules.most_common()),
            "verification_methods": dict(methods.most_common()),
            "average_score": round(sum(r["score"] for r in rows) / len(rows), 1) if rows else 0,
        },
        "requirements": rows,
        "llm_used": False,
    }
