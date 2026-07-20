"""Momentum Life — Claims Processing portal (FastAPI entry point).

Single process: serves the built React frontend (webroot/) and the /api routes
on one port (Databricks Apps binds one port; single-process avoids CORS).
"""
import logging
import os
import threading

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from server.routes import claims, underwriting

log = logging.getLogger("momentum.app")

app = FastAPI(title="Momentum Life — Claims & Underwriting", version="1.1.0")

# Seeded demo cases — pre-warm their AI synopses on startup so the FIRST open in
# the demo is instant (Claude ai_query takes ~30s cold). Runs in a background
# thread so it never blocks app boot; failures are ignored (cache stays empty).
_WARM_CLAIMS = ["CLM-DEATH-CLEAN", "CLM-DISAB-DISCREP", "CLM-SUSPECT-FRAUD"]
_WARM_UW = ["UW-CLEAN-FASTTRACK", "UW-COUNTEROFFER", "UW-NTU-RISK"]


def _prewarm() -> None:
    try:
        from server.agent_client import draft_synopsis
        from server.uw_data import uw_synopsis
        for c in _WARM_CLAIMS:
            try:
                draft_synopsis(c)
            except Exception:
                pass
        for p in _WARM_UW:
            try:
                uw_synopsis(p)
            except Exception:
                pass
        log.info("synopsis pre-warm complete")
    except Exception as exc:  # pragma: no cover
        log.warning("synopsis pre-warm skipped: %s", exc)


@app.on_event("startup")
def _start_prewarm() -> None:
    threading.Thread(target=_prewarm, daemon=True).start()

# CORS for local dev (Vite :5173 -> FastAPI :8000). Harmless in the deployed app.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(claims.router)
app.include_router(underwriting.router)

# Serve the React SPA. Built artifacts live in webroot/ (a copy of frontend/dist
# under a name `databricks sync` won't special-case). Fall back to frontend/dist
# for local dev.
_HERE = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(_HERE, "webroot")
if not os.path.exists(FRONTEND_DIR):
    FRONTEND_DIR = os.path.join(_HERE, "frontend", "dist")

if os.path.exists(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "not found"}, status_code=404)
    # Serve root-level static files (favicon, logos) that Vite emits to dist root.
    # Confirm the resolved candidate stays INSIDE FRONTEND_DIR before serving.
    if full_path:
        root = os.path.realpath(FRONTEND_DIR)
        candidate = os.path.realpath(os.path.join(root, full_path.lstrip("/")))
        if (candidate == root or candidate.startswith(root + os.sep)) and os.path.isfile(candidate):
            return FileResponse(candidate)
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return JSONResponse({"detail": "frontend not built"}, status_code=404)
