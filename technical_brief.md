# The Master Architecture Document

*This is the uncompromising breakdown of the architecture. You must use these exact terms in the script and follow-up calls. We are speaking to elite quants and ML researchers; precision is mandatory.*

## Architectural Paradigm: The Decoupled "Sidecar" Microservice
We have engineered a containerized, event-driven FastAPI microservice operating entirely out-of-band from Tracelight’s core Excel add-in. By establishing a hard DMZ at the `.xlsx` boundary, we avoid any replication of Tracelight’s proprietary in-sheet formula execution or probabilistic interpretation of financial logic. We are strictly operating on pre-ingestion inputs and post-model structured JSON exports.

## Workflow I: Deterministic Synthetic Time-Series Generation
To bypass the enterprise InfoSec dead-zones that block your PoCs, we decoupled the semantic interpretation layer from the mathematical generation layer:
- **Probabilistic Profiling:** We utilize Gemini 3.1 Pro Preview exclusively as a semantic translation heuristic. It maps unstructured natural language ("Distressed European LBO") into a strictly typed JSON schema defining marginal distributions (e.g., Lognormal for revenue, Beta for margins) and target cross-sectional correlations.
- **Deterministic Generation (Zero-LLM):** The LLM is strictly prohibited from generating numerical values. The payload is passed to a deterministic NumPy/SciPy engine. We apply **Cholesky Decomposition** to the target correlation matrix (utilizing Higham’s alternating projections for nearest positive semi-definite correction if necessary). We then execute a **Gaussian Copula** transformation to inject the target correlation structure while perfectly preserving the arbitrary marginal distributions of the underlying assets.
- **Privacy Certification:** We run rigorous Kolmogorov-Smirnov (KS) tests to validate distributional integrity, followed by the application of calibrated Laplace noise to provide formal (ε, 0)-Differential Privacy guarantees.

## Workflow II: Citation-Enforced RAG Deliverable Engine
To resolve the post-model mechanical workload (IC Memos and Executive Decks), we engineered a highly constrained Retrieval-Augmented Generation (RAG) pipeline:
- **Semantic Ingestion:** Qualitative source documents (CIMs, transcripts) are parsed, chunked, and embedded via local `all-MiniLM-L6-v2` models into an ephemeral ChromaDB vector index.
- **Quantitative Provenance:** Financial outputs exported from Tracelight models are deterministically extracted and tagged with exact provenance vectors (e.g., `model_export:ebitda_margin:p50`).
- **Citation Enforcement:** The LLM drafts the narrative via a source-first prompting architecture. It is mathematically constrained to inject exact `[source_tag]` citations for every factual claim. A post-generation deterministic parser validates these citations against the vector index. If the retrieval step yields insufficient evidence, the agent defaults to an explicit abstention protocol (`[INSUFFICIENT DATA]`), entirely mitigating hallucination risk. 

## Workflow III: InfoSec Automation Pipeline
To reclaim engineering capacity from vendor risk assessments (SIG Core, CAIQ):
- **Deterministic Intake:** Inbound questionnaires are parsed deterministically via regex heuristics—no LLMs are used for intake structure detection.
- **Semantic Retrieval & Routing:** Questions are vectorized against a persistent ChromaDB index containing your SOC 2 and architecture docs. A drafting agent generates cited responses with a calculated confidence score.
- **Confidence Routing:** Responses scoring >0.90 are auto-approved. Edge cases are deterministically routed to a human-in-the-loop interface, preventing hallucinated security claims from reaching bank procurement teams.