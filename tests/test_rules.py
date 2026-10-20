import pytest

from ecss_copilot.models import Requirement
from ecss_copilot.rules import check_requirement, check_all, quality_score, _missing_unit_numbers


def ids(text, rid="T-001"):
    return {f.rule_id for f in check_requirement(Requirement(rid, text))}


def test_clean_requirement_has_no_findings():
    assert ids("The EPS shall provide a regulated 5 V ± 0.1 V bus.") == set()
    assert ids("The OBC shall boot into safe mode within 30 s after power-on.") == set()


@pytest.mark.parametrize("text", [
    "The system should be designed for reliability.",
    "The radio will transmit telemetry at 9.6 kbps.",
    "The EPS provides 5 V.",
])
def test_missing_shall(text):
    assert "RQ-01" in ids(text)


def test_multiple_shall():
    fs = [f for f in check_requirement(Requirement("X", "The OBC shall reject bad TCs and shall log them.")) if f.rule_id == "RQ-02"]
    assert fs and fs[0].severity == "High" and "2" in fs[0].match


@pytest.mark.parametrize("term", ["adequate", "user-friendly", "fast", "as appropriate", "sufficient", "robust"])
def test_vague_terms(term):
    assert "RQ-03" in ids(f"The software shall be {term} for operators.")


def test_about_axis_not_vague():
    assert "RQ-03" not in ids("The ADCS shall rotate the spacecraft about the Z axis at 1 deg/s.")


@pytest.mark.parametrize("text", ["The EPS shall provide TBD W.", "The mass shall be below 4 kg (TBC).",
                                  "The value is to be determined and shall be met."])
def test_open_items(text):
    assert "RQ-04" in ids(text)


def test_escape_clause():
    assert "RQ-05" in ids("The spacecraft shall maintain contact with the ground as far as possible.")


def test_unverifiable_absolute():
    assert "RQ-06" in ids("The on-board software shall never crash.")
    assert "RQ-06" in ids("The OBC shall operate under all conditions.")


def test_weak_modal_mixed_with_shall():
    assert "RQ-07" in ids("The OBC shall store data and should compress it.")


def test_missing_subject_is_high():
    fs = [f for f in check_requirement(Requirement("X", "Shall protect the battery against overcharge.")) if f.rule_id == "RQ-08"]
    assert fs and fs[0].severity == "High"


def test_passive_without_agent_is_low():
    fs = [f for f in check_requirement(Requirement("X", "Telecommands shall be verified before execution.")) if f.rule_id == "RQ-08"]
    assert fs and fs[0].severity == "Low"
    assert "RQ-08" not in ids("Telecommands shall be verified by the OBC before execution.")


def test_and_or():
    assert "RQ-09" in ids("The EPS shall protect against overcharge and/or deep discharge.")


def test_missing_units():
    assert "RQ-10" in ids("The battery shall have a capacity of 40.")
    assert "RQ-10" in ids("The watchdog shall reset the OBC if not serviced within 10.")


@pytest.mark.parametrize("text", [
    "The EPS shall provide 3 switchable power lines.",
    "The structure shall comply with ECSS-E-ST-32C.",
    "The spacecraft shall fit a 3U envelope of 100 mm x 100 mm x 340.5 mm.",
    "The battery shall operate between 0 °C and 40 °C.",
    "The OBC shall increment the counter by 1.",
    "The link margin shall be at least 3 dB at 10 deg elevation.",
    "The spacecraft shall comply with [AD-3] issue 2.",
])
def test_units_no_false_positive(text):
    assert _missing_unit_numbers(text) == [], text


def test_open_ended():
    assert "RQ-11" in ids("The radio shall support UHF, VHF, etc.")


def test_negative():
    assert "RQ-12" in ids("The transmitter shall not transmit before enable.")
    assert "RQ-12" not in ids("The mass shall not exceed 4 kg.")


def test_long_statement():
    text = "The spacecraft shall " + " ".join(["provide"] * 50) + "."
    assert "RQ-13" in ids(text)


def test_pronoun():
    assert "RQ-14" in ids("The thermal design shall keep it within 0 °C to 40 °C.")


def test_design_solution():
    assert "RQ-15" in ids("The ADCS shall use a Kalman filter for estimation.")


def test_document_level_duplicates_and_missing_id():
    reqs = [Requirement("A-1", "The X shall do Y."), Requirement("A-1", "The X shall do Z."),
            Requirement("AUTO-001", "The X shall do Y.", id_generated=True)]
    rules = [f.rule_id for f in check_all(reqs)]
    assert rules.count("DOC-01") == 1
    assert "DOC-02" in rules
    assert "DOC-03" in rules


def test_every_finding_has_severity_and_fix():
    text = "Shall be fast and adequate and/or robust, etc., TBD, as far as possible, never 10."
    fs = check_requirement(Requirement("X", text))
    assert len(fs) >= 6
    for f in fs:
        assert f.severity in {"High", "Medium", "Low"}
        assert f.suggestion and f.message


def test_quality_score_bounds():
    fs = check_requirement(Requirement("X", "Shall be fast and adequate and/or robust, etc., TBD, never 10."))
    assert 0 <= quality_score(fs) < 50
    assert quality_score([]) == 100
