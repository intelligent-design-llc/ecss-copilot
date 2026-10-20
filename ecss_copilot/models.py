from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Requirement:
    id: str
    text: str
    source: str = ""          # e.g. "table row 4", "paragraph 12", "line 30"
    id_generated: bool = False  # True if we had to invent the ID

    def to_dict(self):
        return asdict(self)


@dataclass
class Finding:
    req_id: str
    rule_id: str
    rule_name: str
    severity: str        # "High" | "Medium" | "Low"
    message: str
    suggestion: str
    match: str = ""      # text fragment that triggered the rule

    def to_dict(self):
        return asdict(self)


@dataclass
class Verification:
    req_id: str
    primary: str                 # "Test" | "Analysis" | "Inspection" | "Review of design"
    secondary: Optional[str]
    rationale: str
    source: str = "rule-based"   # or "llm"

    def to_dict(self):
        return asdict(self)


SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
SEVERITY_PENALTY = {"High": 25, "Medium": 10, "Low": 4}
METHODS = ["Test", "Analysis", "Inspection", "Review of design"]
