# Prompt for Gemini: Generate a Demo Brief

> **Context**: You are drafting a comprehensive demo brief for a non-technical co-founder who will screen-record and narrate the demo for enterprise prospects. The demo is a pitch to Tracelight (https://tracelight.ai), a seed-stage AI startup that embeds AI into Microsoft Excel for financial modeling. Read `CONTEXT.MD` (renamed `tracelight_CONTEXT.MD` in repo) and `PRD.md` in this repo for full strategic context.

---

## What You're Looking At

This repo (`tracelight/`) is a **containerized microservice demo** consisting of three AI-powered "sidecar" workflows designed to plug into Tracelight's ecosystem. The key constraint: **we never touch Excel, write formulas, or replicate Tracelight's core product**. Everything we build operates strictly *around* the spreadsheet — before and after the financial model.

The demo runs as two services:
- **Backend**: FastAPI (Python) on port 8000 — API endpoints + 4-agent pipelines per workflow
- **Frontend**: Streamlit on port 8501 — visual demo UI with dark green Tracelight-branded theme

There is a **Demo Mode** toggle (on by default) that serves pre-cached results with zero latency and no API keys needed. This is what the co-founder should use for recording.

---

## The Three Workflows

### Workflow I: Synthetic Financial Data Generator
**The problem it solves**: When Tracelight tries to run a Proof of Concept with a bank or PE fund, the client can't share real financial data due to InfoSec/GDPR restrictions. This creates a 3-6 month dead zone in the sales cycle while legal teams negotiate data agreements. Tracelight's CTO has publicly complained about this exact problem on LinkedIn.

**What it does**: Takes a natural-language description of a financial scenario (e.g., "Distressed PE LBO, mid-market European industrials, high leverage") and generates mathematically realistic synthetic test data that clients can immediately import into their Excel models to evaluate Tracelight.

**How it works under the hood**:
1. **LLM Profiler Agent** (Gemini 3.1 Pro Preview): Interprets the natural language into statistical parameters — which probability distributions to use, what correlations between variables, etc.
2. **Deterministic Math Engine** (NumPy/SciPy): Generates the actual data using Cholesky decomposition and Gaussian copula to maintain realistic cross-asset correlations. No LLM touches the numbers.
3. **Differential Privacy Validator**: Runs Kolmogorov-Smirnov statistical tests to verify the data matches target distributions, then optionally applies Laplace noise for privacy certification.
4. **Export**: Outputs CSV or JSON. Never `.xlsx`.

**What the demo shows**: User selects a preset (e.g., "PE LBO"), clicks generate, sees a data preview table, distribution histograms, correlation heatmap, and KS test validation results. Downloads the CSV.

### Workflow II: Post-Excel Deliverable Engine
**The problem it solves**: After an analyst builds a financial model in Tracelight's Excel engine, they spend 48-72 hours manually copy-pasting outputs into 15-50 page Investment Committee memos (Word) and executive PowerPoint decks. This is the "final mile" bottleneck.

**What it does**: Ingests financial data (from Workflow I or any CSV/JSON) plus qualitative source documents (CIMs, management presentations, expert call transcripts), then auto-generates a fully cited IC memo and exec deck.

**How it works under the hood**:
1. **Context Harvester Agent**: Uploads and vectorizes source documents (PDF/DOCX/TXT) into a semantic search database (ChromaDB) using local AI embeddings.
2. **Quantitative Extraction Agent**: Pulls financial metrics from the data and tags every single number with a source reference (e.g., "model_export:ebitda_margin:p50").
3. **Narrative Drafting Agent** (Gemini 3.1 Pro Preview): Drafts each memo section using Retrieval-Augmented Generation (RAG) with **mandatory citation enforcement** — every claim must cite a source. If evidence is insufficient, it flags the section for human review instead of hallucinating.
4. **Citation & Formatting Agent**: Renders the narrative into a professional Word document and PowerPoint deck with an audit trail appendix mapping every claim to its source.

**What the demo shows**: User uploads source docs, configures the memo (firm name, sections, confidence threshold), generates deliverables. Sees a section-by-section review dashboard with confidence scores, citation highlights, and amber flags on low-confidence sections. Downloads DOCX and PPTX.

### Workflow III: InfoSec & Vendor Risk Compliance Engine
**The problem it solves**: As a startup selling to banks and PE funds, Tracelight's engineering team (ex-Jane Street engineers) wastes hundreds of hours hand-completing vendor security questionnaires — SIG Core (800+ questions), CAIQ (260+ questions), and bespoke bank questionnaires. This drains engineering capacity from product development.

**What it does**: Ingests an inbound security questionnaire, matches each question against Tracelight's security knowledge base (SOC 2 reports, policies, prior responses), auto-generates responses with confidence scoring, and routes low-confidence answers to a human reviewer.

**How it works under the hood**:
1. **Intake & Parsing Agent**: Detects the questionnaire format (SIG Core/Lite, CAIQ, or custom), parses questions from CSV/DOCX/PDF, and classifies each as boolean, narrative, or multiple-choice. No LLM — pure regex/heuristic parsing.
2. **Knowledge Retrieval Agent**: Searches Tracelight's indexed security documentation (SOC 2 reports, pentest summaries, incident response plans) using semantic similarity to find the most relevant evidence for each question.
3. **Response Drafting Agent** (Gemini 3.1 Pro Preview): Generates a cited response per question. Boolean questions get Yes/No + justification. Narrative questions get 50-200 word responses citing specific policies. Citation enforcement ensures no fabricated claims.
4. **Routing & Export Agent**: Auto-approves high-confidence responses (≥90%), flags low-confidence (<80%) for human review. Exports completed questionnaire as CSV, DOCX, or JSON.

**What the demo shows**: User uploads a security KB + questionnaire, generates responses. Sees a dashboard with summary metrics (total questions, auto-approved, needs review), expandable per-question review with editable responses, approve/override buttons, and domain-level progress. Downloads completed questionnaire.

---

## Demo Flow for Screen Recording

**Recommended recording order** (matches the pitch narrative):

1. **Landing Page** (~15 seconds): Show the three workflow cards. Explain the sidecar concept — "these tools wrap around Tracelight's core product without touching Excel."

2. **Workflow I** (~90 seconds): Launch → select "PE LBO" preset → click Generate → show the data table, distribution charts, correlation heatmap, KS test results → download CSV. Key talking point: "This collapses your PoC timeline from 6 months to 6 minutes."

3. **Workflow II** (~90 seconds): Launch → click Process Documents (demo mode auto-loads) → configure memo for "Acme Capital" → click Generate → walk through the section-by-section review, point out the citation tags and the amber-flagged Market Analysis section → download DOCX. Key talking point: "This turns your product into the system of record for the entire deal lifecycle."

4. **Workflow III** (~90 seconds): Launch → click Index to KB + Parse Questionnaire (demo mode auto-loads) → click Generate Responses → show the dashboard metrics (20 questions, 16 auto-approved, 4 needs review) → open one needs-review item, show the editable response → click Approve → download DOCX. Key talking point: "Your engineers stop wasting time on procurement paperwork."

5. **Wrap** (~15 seconds): Back to landing page. "Three sidecar workflows. Zero overlap with your core IP. Immediate ROI."

**Total recording time**: ~5 minutes.

---

## Technical Details the Co-Founder Should Know (But Not Say in the Pitch)

- **Demo Mode**: The toggle in the sidebar serves pre-cached results. No live API calls happen. This means the recording will be consistent across takes and won't break.
- **The math is real**: The synthetic data generator uses Cholesky decomposition and Gaussian copula — these are the same methods used by quantitative trading desks. The CTO (ex-Jane Street) will recognize and respect this.
- **Citation enforcement**: The deliverable engine and compliance engine both refuse to generate unsupported claims. If the AI can't find evidence, it writes "[INSUFFICIENT DATA — REQUIRES ANALYST INPUT]" instead of making something up. This is a key differentiator.
- **No `.xlsx` anywhere**: The entire system is designed to never touch Excel files. This is deliberate — it proves we understand and respect Tracelight's IP boundary.
- **LLM is the brain, not the muscle**: The LLM (Gemini 3.1 Pro Preview) is only used for interpretation and drafting. All numerical generation is deterministic math. This matters for the CTO.

---

## Who We're Pitching To (Read CONTEXT.MD for Full Profiles)

- **Peter Fuller (CEO, ex-McKinsey)**: Cares about deal velocity, revenue expansion, MECE frameworks. Lead with business impact.
- **Aleksander Misztal (CTO, ex-Jane Street)**: Cares about mathematical rigor, determinism, testing. Will poke at the Cholesky implementation.
- **Janek Zimoch (CPO, ex-Cambridge ML)**: Cares about agentic orchestration, RAG architecture, hallucination prevention. Will evaluate the citation enforcement.

---

## Task for Gemini

Using all of the above, plus `tracelight_CONTEXT.MD` and `PRD.md` from this repo, draft a **comprehensive Demo Brief** document that includes:

1. **One-page executive overview** — what this demo is, who it's for, and the key value proposition (written for a non-technical reader)
2. **Workflow-by-workflow walkthrough** — what to show, what to say, where to click, what to highlight (written as a step-by-step script the co-founder can follow while recording)
3. **Talking points per audience member** — what resonates with the CEO vs. CTO vs. CPO (3-4 bullets each)
4. **FAQ / Objection handling** — likely questions from the Tracelight team and recommended responses
5. **Technical cheat sheet** — one-page reference the co-founder can review before recording so he understands the key terms (Cholesky, copula, KS-test, RAG, citation enforcement, differential privacy) at a high level

Output as a single markdown document: `DEMO_BRIEF.md`
