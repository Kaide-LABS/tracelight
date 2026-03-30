# Tracelight Sidecar Demo — Project Instructions

## Overview
Containerized PoC demo (FastAPI + Streamlit) pitching adjacent "sidecar" AI workflows to Tracelight (Excel AI for finance). Two workflows: Synthetic Data Generator + Post-Excel Deliverable Engine.

## Architecture
- **Backend**: FastAPI at `backend/app/main.py`, port 8000
- **Frontend**: Streamlit at `frontend/app.py`, port 8501
- **Demo Mode**: Toggle in sidebar, serves pre-cached results, no API keys needed
- **Backend URL**: Configurable via `BACKEND_URL` env var (defaults to `http://backend:8000`)

## Cloud Run Deployment
- **Project**: `gen-lang-client-0754692302`
- **Region**: `us-central1`
- **Backend**: `tracelight-backend` → https://tracelight-backend-8822384086.us-central1.run.app
- **Frontend**: `tracelight-frontend` → https://tracelight-frontend-8822384086.us-central1.run.app
- Deploy with: `gcloud run deploy <service> --source . --region us-central1 --allow-unauthenticated`

## Demo Narrative
- **Deal**: Meridian Growth Partners evaluating $85M growth equity investment in NovaCrest Analytics
- **Due Diligence Pack**: Single consolidated PDF (`NovaCrest_Due_Diligence_Pack.pdf`) — CIM, management transcript, expert calls, customer references
- **Outputs**: IC Memo (DOCX) + Exec Deck (PPTX) with inline preview viewers

## Session Handoff — 2026-03-30
### Completed
- Removed Workflow III (compliance engine) entirely
- Added inline document preview viewers (DOCX via mammoth, PPTX via position-aware renderer)
- Removed confidence threshold slider from UI
- Made backend URL configurable via env var
- Created updated demo brief prompt V2 (`DEMO_BRIEF_PROMPT_V2.md`) for Gemini playbook generation
- Deployed both services to Cloud Run
- All committed and pushed to main

### Next Steps
- Give `DEMO_BRIEF_PROMPT_V2.md` to Gemini to regenerate the 4-part playbook (company_teardown, layman_brief, technical_brief, loom_script_and_parries)
- Record 2-minute Loom demo video using the script Gemini generates
- Review PPTX preview rendering — may need polish for specific slide layouts
- `app/` and `backend/frontend/` are orphaned untracked dirs — can be deleted

## Untracked Orphan Dirs
- `app/` — appears to be an old copy, not in use
- `backend/frontend/` — appears to be an old copy, not in use
