# The Execution: Loom Script & Parries

## The 2-Minute Loom Script

**[0:00 - Screen sharing the Landing Page]**
"Peter, Aleksander, Janek. My Lead Architect, Hafeedh, and I have been closely following Tracelight’s trajectory. You’ve successfully solved the probabilistic interpretation bottleneck inside the spreadsheet. But in enterprise, the friction before and after the model is killing deal velocity. Hafeedh built a containerized microservice demonstrating three out-of-band 'sidecar' workflows. Crucially, we maintain a strict DMZ: we never touch an `.xlsx` file. We operate exclusively on the periphery."

**[0:25 - Click into Workflow I: Synthetic Data Generator, hit Generate]**
"Aleksander, I saw your LinkedIn post about PoC InfoSec bottlenecks. Banks won't give you real data. Instead of waiting six months, we generate mathematically rigorous synthetic time-series data. Hafeedh decoupled the architecture: we use Gemini 3.1 Pro purely as a semantic profiler to map natural language into a statistical schema. But the actual generation is zero-LLM. We use pure NumPy, applying Cholesky decomposition and a Gaussian Copula to maintain precise cross-asset correlations while preserving marginal distributions. We validate it with KS-tests and apply differential privacy. Prospects import this CSV into Tracelight on day one."

**[1:05 - Click into Workflow II: Deliverable Engine, hit Generate]**
"Second, the post-Excel mechanical workload. After your engine runs, analysts waste 72 hours pasting outputs into IC Memos. Hafeedh built a citation-enforced RAG pipeline. We embed source CIMs into ChromaDB and map your quantitative model exports to exact provenance tags. The drafting agent is constrained by a strict abstention protocol—every claim requires a verified `[source_tag]`. If it lacks data, it refuses to hallucinate and flags the section for human review. It exports audit-ready Word and PowerPoint files."

**[1:40 - Click into Workflow III: Compliance Engine, show the dashboard]**
"Finally, your ex-Jane Street engineers shouldn't be wasting cycles answering 800-question SIG security questionnaires. Hafeedh built a compliance engine that parses vendor assessments deterministically, retrieves your SOC 2 policies via semantic search, and auto-drafts cited responses with strict confidence routing. High confidence is auto-approved; edge cases go to human review."

**[1:55 - Wrap Up]**
"Three sidecars. Zero overlap with your core Excel IP. Massive expansion of your ACV by owning the entire deal lifecycle. Let's get on a call to discuss the architecture."

---

## The Parries (Follow-Up Call Defense)

When you get on the call, Aleksander (CTO) and Janek (CPO) will test your technical depth. Use these exact rebuttals.

### Objection 1 (from Aleksander, CTO)
*"LLMs are notoriously bad at math and maintaining cross-sectional consistency over time. If I give this synthetic data to a quant fund, they're going to realize the correlations are broken immediately."*

**The Parry:** 
"We completely agree, which is why the LLM has zero involvement in the mathematical generation. Hafeedh explicitly designed this so the LLM acts solely as a translation layer—it outputs a strictly typed JSON schema of target marginals and correlation matrices. The actual instantiation is handled by a deterministic NumPy engine using Cholesky decomposition to factor the correlation matrix, applied via a Gaussian Copula. The math is completely isolated from the probabilistic language model."

### Objection 2 (from Janek, CPO)
*"RAG for IC Memos is incredibly dangerous for private equity. If the context window drops a key risk factor, or the LLM hallucinates a revenue multiple, the whole deal is compromised."*

**The Parry:** 
"That’s exactly why we don't rely on standard generative RAG. We implemented a strict citation-enforcement protocol. The LLM is instructed via a source-first architecture: every factual claim *must* be accompanied by an exact provenance vector tag. Post-generation, a deterministic script parses the output and cross-references those tags against the ChromaDB metadata and the extracted financial JSON. If a tag is fabricated or missing, the system defaults to an explicit abstention—it outputs `[INSUFFICIENT DATA]` and drops the confidence score, routing it to a human. We prioritize abstention over hallucination."

### Objection 3 (from Peter, CEO)
*"This is cool, but why shouldn't we just build this directly into our Excel add-in so the user never has to leave the spreadsheet?"*

**The Parry:** 
"Because forcing qualitative workflows into a quantitative environment degrades the user experience and bloats your core IP. The inputs for an IC memo—like 100-page PDF CIMs and management presentations—and the outputs—Word documents and PowerPoint decks—inherently exist outside of Excel. By deploying this as an out-of-band sidecar, you maintain the pristine latency of your Excel engine while capturing the final-mile enterprise value. You own the whole lifecycle without compromising the core product."