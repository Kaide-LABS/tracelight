# Architectural Blueprint: Pre- and Post-Model Orchestration Sidecars

## 1. System Overview & IP Boundary Stricture

This architectural brief details the design and implementation of two isolated, containerized microservices ("sidecars") designed to operate adjacently to Tracelight's core in-spreadsheet AI engine. 

The fundamental design constraint of this system is strict adherence to the defined IP Boundary. This architecture is entirely decoupled from the spreadsheet layer.

| Permitted Operations (Our Scope) | Restricted Operations (Tracelight IP) |
| :--- | :--- |
| Generate synthetic time-series data via statistical modeling | Read, write, or manipulate `.xlsx` files or internal structures |
| Natural language translation to statistical parameter vectors | Generate or audit spreadsheet formulas / cell logic |
| Output strictly formatted `.csv` / `.json` payload ingestible by Excel | Execute within the Excel COM/VSTO or Office.js layer |
| Auto-compile `.docx` / `.pptx` deliverables via RAG over static docs | Replicate Tracelight's proprietary model auditing or error-checking |
| Enforce strict provenance tracking and statistical validation (KS-tests) | Access, interface with, or reverse-engineer Tracelight backend systems |

The system comprises a FastAPI backend orchestrator and a Streamlit frontend, containerized for immediate deployment. The architecture currently supports two distinct workflows threaded via a unified deal narrative (the "NovaCrest Analytics" growth equity transaction).

---

## 2. Workflow I: Synthetic Financial Data Generator (Pre-Model)

**Objective:** Eliminate InfoSec-induced sales cycles by providing a deterministic, mathematically rigorous synthetic data generation pipeline.

**Architecture & Data Flow:**
1.  **Semantic Parameter Extraction:** The system ingests a natural language description of the target financial profile (e.g., "B2B SaaS, $31M ARR, 72% YoY growth, high Q4 seasonality"). An LLM strictly extracts these inputs into a structured JSON payload defining the statistical parameters (mean, variance, target correlation matrix). **Crucially, the LLM does not generate the data.**
2.  **Deterministic Generation Engine:** The statistical parameters are passed to a Python-based quantitative engine. We employ **Cholesky Decomposition** on the target correlation matrix to generate correlated standard normal variables, which are then mapped to target marginal distributions using a **Gaussian Copula**.
3.  **Statistical Validation:** The generated multivariate time-series data undergoes rigorous internal validation. We execute two-sample **Kolmogorov-Smirnov (KS) tests** to ensure the synthetic marginal distributions do not significantly deviate from the requested parameters, alongside Frobenius norm checks on the resulting correlation matrix.
4.  **Privacy Guarantee:** A Differential Privacy layer (Laplace mechanism) is applied to ensure structural anonymity, mathematically guaranteeing zero possibility of reverse-engineering any underlying proprietary models if seeded with historical data.
5.  **Output:** The validated dataset is serialized to a clean `.csv` or `.json` payload, ready for seamless ingestion into Tracelight’s modeling environment. The frontend visualizes the distribution shapes and correlation heatmaps to prove statistical rigor.

---

## 3. Workflow II: Post-Excel Deliverable Engine (Post-Model)

**Objective:** Automate the "final mile" translation of quantitative model outputs and qualitative due diligence into standardized, highly-formatted Investment Committee (IC) Memos and Executive Decks.

**Architecture & Data Flow:**
1.  **Unified Ingestion:** The engine ingests the generated financial data alongside a composite PDF artifact (`NovaCrest_Due_Diligence_Pack.pdf`, encompassing the CIM, management transcripts, and expert network calls).
2.  **Semantic Embedding & Provenance:** The PDF is chunked via a structural-aware parser. Chunks are embedded using an `instruct-large` embedding model and stored in an ephemeral vector index. Each chunk is tagged with an immutable **Provenance Vector** (Document ID, Page Number, Section Header).
3.  **Retrieval-Augmented Generation (RAG) with Strict Abstention:** The generation agent operates under a highly constrained prompt architecture. It queries the vector index to draft specific sections of the IC Memo.
    *   **Citation Enforcement:** Every factual claim must be explicitly linked to a Provenance Vector, rendered as an inline citation tag.
    *   **Abstention Protocol:** If the semantic similarity of retrieved chunks falls below the dynamic confidence threshold, or if the context is insufficient, the agent is forced to execute an Abstention Protocol, outputting: *"Insufficient data in source documents to evaluate this claim,"* flagging the section amber in the review dashboard.
4.  **Document Compilation:** The validated text and quantitative insights are passed to the formatting engine (`python-docx` and `python-pptx`). 
    *   It structurally generates the `.docx` IC Memo, mapping markdown to native Word styles.
    *   It constructs the `.pptx` Executive Deck, dynamically building KPI cards, numbered thesis slides, and tabular financial summaries based on pre-defined corporate templates.
5.  **Inline Review:** The generated artifacts are rendered via server-side conversion into the frontend's inline, scrollable preview windows, allowing the analyst to audit the citations and formatting prior to local download.