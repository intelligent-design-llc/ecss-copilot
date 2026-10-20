import json

from ecss_copilot import llm
from ecss_copilot.core import analyse
from ecss_copilot.models import Requirement


def test_llm_disabled_without_env(monkeypatch):
    for k in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert llm.config()["enabled"] is False


def test_llm_refine_with_mocked_endpoint(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://example.invalid/v1")
    monkeypatch.setenv("LLM_MODEL", "mock-model")
    sent = {}

    def fake_post(messages, cfg, timeout=120):
        payload = json.loads(messages[1]["content"])
        sent["ids"] = [p["id"] for p in payload]
        return json.dumps({"items": [{"id": "B-2", "rewrite": "The OBC shall boot within [TBD: value, s].",
                                      "verification_method": "Test", "rationale": "Timed boot test."}]})

    monkeypatch.setattr(llm, "_post", fake_post)
    res = analyse([Requirement("A-1", "The EPS shall provide 5 V."), Requirement("B-2", "The OBC shall boot fast.")])
    out = llm.refine(res)
    assert sent["ids"] == ["B-2"]  # only flagged requirements are sent
    row = next(r for r in out["requirements"] if r["id"] == "B-2")
    assert row["llm"]["verification_method"] == "Test"
    assert out["llm_used"] and out["llm_errors"] == []
