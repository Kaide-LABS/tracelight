# Gemini Prompt: Generate Updated 4-Part Sales & Execution Playbook

Act as an elite Lead AI Architect creating a 4-part "Sales & Execution Playbook" for my non-technical co-founder.

I have just built a containerized, proof-of-concept AI demo to pitch to Tracelight (https://tracelight.ai). My co-founder is responsible for recording the 2-minute Loom screen-share and sending it to the prospect's executive team.

**CRITICAL STRATEGY**: My co-founder needs a layman explanation internally to understand the concept, BUT the actual pitch script and technical brief MUST use highly complex, accurate architectural jargon. We are pitching elite CTOs; we cannot dumb down the final presentation or we will sound like generic salespeople. We must prove deep domain expertise.

---

## INPUT CONTEXT

* **Reference Material**: Carefully review `PRD.md` in this repo. It is the ground truth for the architecture, IP boundaries, and agent pipeline details. Also review the existing `technical_brief.md`, `layman_brief.md`, `company_teardown.md`, and `loom_script_and_parries.md` in the repo root — these are the **previous versions** that need to be updated to reflect the current state described below.

* **Target Company**: Tracelight (https://tracelight.ai)

* **Target Audience**:
  - **Peter Fuller** (CEO, ex-McKinsey): Cares about deal velocity, revenue expansion, MECE frameworks. Lead with business impact.
  - **Aleksander Misztal** (CTO, ex-Jane Street): Cares about mathematical rigor, determinism, testing. Will scrutinize the Cholesky implementation and synthetic data pipeline. This is an elite quant — every technical claim must be defensible.
  - **Janek Zimoch** (CPO, ex-Cambridge ML researcher): Cares about agentic orchestration, RAG architecture, hallucination prevention. Will evaluate the citation enforcement and abstention protocol.

* **Their Core Product**: Tracelight builds an AI engine embedded directly inside Microsoft Excel that helps financial professionals (PE analysts, investment bankers) build, audit, and interpret complex financial models. Their clients are banks, PE funds, and asset managers.

* **The Problem We Are Solving**: Two bottlenecks that bracket Tracelight's core product:
  1. **Pre-model**: Enterprise deal velocity is blocked by InfoSec approvals. Clients can't share real financial data for PoCs, creating a 3-6 month dead zone. Aleksander has publicly complained about this on LinkedIn.
  2. **Post-model**: After an analyst builds a financial model in Tracelight's Excel engine, they spend 48-72 hours manually copy-pasting outputs into IC memos (Word) and executive decks (PowerPoint). This is the "final mile" bottleneck.

* **What I Built (The Demo)**: A containerized web app (FastAPI backend + Streamlit frontend) with **two** adjacent "sidecar" workflows. The demo uses a cohesive deal narrative — a fictional growth equity investment in **NovaCrest Analytics** by **Meridian Growth Partners** — to show both workflows working together on a single realistic deal.

  **Workflow I — Synthetic Financial Data Generator**: Takes a natural-language financial scenario, translates it to statistical parameters via LLM, generates correlated synthetic time-series using Cholesky decomposition + Gaussian copula (zero-LLM math), validates with KS-tests, applies differential privacy. Outputs CSV/JSON.

  **Workflow II — Post-Excel Deliverable Engine**: Ingests a **NovaCrest Due Diligence Pack** (a single consolidated PDF containing a CIM, management presentation transcript, expert call transcripts, and customer references — 11 pages total) plus financial data from Workflow I. Uses RAG with citation enforcement to auto-generate:
    - A fully cited IC Memo (DOCX) with inline source tags
    - An Executive Deck (PPTX) with KPI cards, numbered thesis slides, and financial tables
    - Both are viewable in **inline document preview windows** (scrollable, dark-themed) directly in the UI before downloading

* **The IP Boundary (Crucial)**:
  | We DO | We DO NOT |
  |-------|-----------|
  | Generate synthetic CSV/JSON test data | Touch, read, write, or manipulate `.xlsx` files |
  | Use LLM to interpret financial scenarios into statistical params | Use LLM to generate formulas or spreadsheet logic |
  | Output data that can be *imported into* Excel models | Operate within the spreadsheet layer in any way |
  | Auto-generate IC Memos (DOCX) and Exec Decks (PPTX) from model outputs | Replicate Tracelight's in-Excel AI, error-checking, or formula generation |
  | Validate statistical properties of generated data | Access or modify any Tracelight proprietary systems |

---

## CRITICAL CHANGES FROM PREVIOUS VERSION

The previous playbook files reference **three workflows**. The demo now has **two workflows only**. Workflow III (InfoSec & Vendor Risk Compliance Engine) has been removed entirely. Do NOT reference it anywhere.

**Other key changes to reflect:**
1. **NovaCrest deal narrative**: The entire demo is now threaded through a single cohesive deal — Meridian Growth Partners evaluating an $85M growth equity investment in NovaCrest Analytics (B2B SaaS findata infrastructure, $31M ARR, 72% YoY growth). The due diligence pack is a single consolidated PDF (not separate files).
2. **Document preview viewers**: Workflow II now has inline preview windows for both the DOCX memo and PPTX deck. Users see the generated documents in a scrollable viewer panel with tabs ("IC Memo" / "Exec Deck"), with download buttons below each preview. No fullscreen button.
3. **No confidence threshold slider**: The confidence threshold input was removed from the UI — the AI determines confidence per section after generation and displays it in the review dashboard. Users don't set it.
4. **Demo Mode**: Toggle in sidebar serves pre-cached results with simulated processing delays. No API keys needed. This is what the co-founder uses for recording.
5. **The Loom script should be ~2 minutes**, not 5. Only two workflows to cover.
6. **The due diligence source material** is a single PDF called `NovaCrest_Due_Diligence_Pack.pdf` containing: CIM (Feb 2026), Management Presentation Transcript (Feb 2026), Expert Call with Dr. Sarah Chen (former CDO, EuroBank Corp), Expert Call with James Park (former NovaCrest customer who churned), and Customer Reference from Lisa Torres (Avalon Asset Management). The demo shows uploading this single file.

---

## YOUR TASK

Generate a comprehensive, 4-part playbook. Format your response into **four distinct Markdown files** that will replace the existing ones in the repo root:

### FILE 1: `company_teardown.md` (The Business Intelligence Brief)
* **Goal**: Provide my co-founder with a deep, comprehensive understanding of Tracelight.
* **Content**: Based on `PRD.md`, detail exactly what Tracelight is, what their core Excel AI product does, how it works technically on a high level, the specific pain points it solves for their enterprise clients (banks, PE funds), and how they make money. Profile each founder (Peter, Aleksander, Janek) with their backgrounds and what they care about. This ensures my co-founder fully grasps their business model before attempting to pitch an adjacent solution.

### FILE 2: `layman_brief.md` (The Internal Translation)
* **The Analogy**: Create a dead-simple, real-world analogy to explain why our custom sidecar software exists and what our AI agents are doing. This bridges the gap between Tracelight's core product and our demo. This is strictly for his internal understanding so he grasps the business value before hitting record.
* **Include**: Walk through the NovaCrest deal narrative in plain English — what the due diligence pack is, why a single PDF makes sense, what the generated memo and deck actually look like, and why the inline preview matters for the pitch.

### FILE 3: `technical_brief.md` (The Master Architecture Document)
* **Goal**: Write a highly technical, uncompromising breakdown of our demo's architecture. Use accurate engineering and industry-specific terminology (Cholesky Decomposition, Gaussian Copula, Kolmogorov-Smirnov, Differential Privacy, Retrieval-Augmented Generation, citation enforcement, abstention protocol, provenance vectors, semantic embedding). Explain the exact data flow, the AI models used, and how it strictly respects the IP Boundary.
* **This must read like an ex-Jane Street / ex-Palantir senior engineer wrote it.** Aleksander will read this or hear it paraphrased — every term must be precise and defensible.
* **IMPORTANT**: Only two workflows. Do not reference Workflow III.

### FILE 4: `loom_script_and_parries.md` (The Execution)
* **Goal**: Provide a step-by-step guide for the **2-minute** Loom video.
* **The Script**: Blend the operational screen clicks with the complex technical wording from File 3. The voiceover must sound like a confident Lead Architect presenting their team's work to peers. Do NOT dumb down the vocabulary. Frame it as "My Lead Architect, Hafeedh, built this..." and reference Aleksander's LinkedIn post about InfoSec bottlenecks.
* **Screen flow**:
  1. Landing page (~10 sec): Two workflow cards, explain the sidecar concept
  2. Workflow I (~40 sec): Select preset → Generate → show data table, distribution charts, correlation heatmap, KS test results → mention CSV download
  3. Workflow II (~55 sec): Upload NovaCrest Due Diligence Pack PDF → Process → Configure memo (Meridian Growth Partners) → Generate → Walk through section-by-section review dashboard (highlight confidence scores, citation tags, amber-flagged sections) → Switch to IC Memo preview tab (show the inline viewer) → Switch to Exec Deck preview tab → mention download
  4. Wrap (~15 sec): Back to landing. Two sidecars, zero IP overlap, entire deal lifecycle.
* **The Parries**: List 3 highly technical objections the founders might have (one from each: Aleksander/CTO on math rigor, Janek/CPO on RAG hallucination, Peter/CEO on build-vs-buy), and provide exact, pre-written "Parries" (rebuttals) using the advanced terminology so my co-founder can confidently defend the architecture on a follow-up call.

---

## OUTPUT FORMAT

Output each file as a complete, standalone Markdown document with proper headers, formatting, and structure. Each file should be self-contained and immediately usable.
