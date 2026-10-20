# Roadmap

ECSS Copilot is an early prototype. The roadmap is indicative and may change with user feedback.

## v0.1 (current)
- Requirement extraction from DOCX, PDF (text layer), CSV, XLSX, TXT and ReqIF (best effort)
- 15 rule-based requirement-quality checks plus 3 document-level checks, each with a severity and suggested fix
- Draft verification method per requirement (Test / Analysis / Review of design / Inspection)
- Optional LLM rewrite pass through any OpenAI-compatible endpoint
- XLSX export (summary, requirements, findings, verification matrix, rule catalogue)

## v0.2: compliance matrix
- Draft a compliance matrix (C / PC / NC / N/A plus justification) against a chosen standard
- **Bring your own standard:** the user uploads their own copy of the standard; the project never ships or redistributes standard text
- Clause-level citations so every compliance statement can be checked by a reviewer
- Tailoring-matrix support (applicable / tailored / not applicable)

## v0.3: interoperability
- ReqIF export (round-trip with DOORS, Polarion, Capella and similar tools)
- Traceability checks: parent/child links, coverage gaps, orphan requirements
- Diffing between document issues/revisions

## Deployment and data control
- Published Docker image for self-hosted / on-premises use (a Dockerfile is already included)
- Local open-weights model option (e.g. via vLLM or Ollama) so no data leaves the customer network
- Documented configuration for EU-hosted LLM providers
- Optional project persistence with explicit deletion

## Quality
- Larger public evaluation set of synthetic requirements with expected findings
- False-positive tracking and per-rule enable/disable and severity configuration
- Additional languages (German, French) for rule vocabularies

Suggestions are welcome; please open an issue.
