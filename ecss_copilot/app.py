"""FastAPI app: single-page UI + JSON API. Stateless: uploads are processed in memory and not stored."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from . import __version__
from .core import analyse
from .export import to_xlsx
from .extract import ExtractionError, extract, requirements_from_text
from . import llm

STATIC = Path(__file__).parent / "static"
MAX_BYTES = 15 * 1024 * 1024

app = FastAPI(title="ECSS Copilot (prototype)", version=__version__)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/config")
def get_config():
    c = llm.config()
    return {"version": __version__, "llm": {"enabled": c["enabled"], "base_url": c["base_url"], "model": c["model"]}}


@app.post("/api/analyze")
async def analyze(file: Optional[UploadFile] = File(None), text: str = Form("")):
    try:
        if file is not None and file.filename:
            data = await file.read()
            if len(data) > MAX_BYTES:
                raise HTTPException(413, "File too large (15 MB max in the prototype).")
            reqs = extract(file.filename, data)
            source = file.filename
        elif text.strip():
            reqs = requirements_from_text(text)
            source = "pasted text"
        else:
            raise HTTPException(400, "Upload a file or paste requirement text.")
    except ExtractionError as e:
        raise HTTPException(422, str(e))
    if not reqs:
        raise HTTPException(422, "No requirements found. Requirements need an ID (e.g. SYS-010) or a 'shall' statement, "
                                 "or a table with an ID and a requirement text column.")
    return analyse(reqs, source)


@app.post("/api/llm")
async def llm_refine(result: dict):
    if not llm.config()["enabled"]:
        raise HTTPException(400, "LLM is not configured on the server (LLM_BASE_URL / LLM_MODEL).")
    try:
        return llm.refine(result)
    except Exception as e:
        raise HTTPException(502, f"LLM call failed: {e}")


@app.post("/api/export")
async def export(result: dict):
    data = to_xlsx(result)
    name = "ecss-copilot-report.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})
