# Loom Execution Playbook: The Tracelight Pitch

## The Setup
*   **Target Length:** 2:00 - 2:30 maximum.
*   **Tone:** Elite, confident, deeply technical. You are not a salesperson; you are a peer presenting architectural work.
*   **Prerequisites:** Start the app in **Demo Mode** (toggle in the sidebar). This uses pre-cached, deterministic data with simulated processing delays so the demo is lightning fast and never breaks on camera.
*   **Concept to Keep in Mind:** We are framing this around Aleksander's recent LinkedIn post regarding InfoSec delays.

---

## The Script & Screen Flow

### Part 1: The Hook & Architecture (0:00 - 0:20)
*(Screen: App Landing Page showing the two Workflow cards. Mouse hovering near the center.)*

**Voiceover:** "Peter, Aleksander, Janek. I saw Aleksander’s post about the 6-month InfoSec dead zone killing enterprise deal velocity. My Lead Architect, Hafeedh, and I spent the weekend looking at Tracelight's architecture, and we built a containerized proof-of-concept to solve exactly that, plus the post-model formatting bottleneck. We built two sidecars that wrap around your core Excel engine without touching a single line of your proprietary spreadsheet IP. Let me show you."

### Part 2: Workflow I - Pre-Model Synthetic Data (0:20 - 1:05)
*(Screen: Click into Workflow I. Select the "NovaCrest Analytics" preset. Hit Generate.)*

**Voiceover:** "Workflow I is a pre-model synthetic data generator. We need realistic test data to run PoCs without waiting for bank clearance. Crucially, the LLM does *not* generate the math—that’s a recipe for hallucination."

*(Screen: Scroll down to show the generated data table, the distribution charts, and the correlation heatmap.)*

**Voiceover:** "Instead, the LLM just extracts the semantic parameters. We then use a Cholesky decomposition and a Gaussian copula to generate a highly correlated multivariate time-series. The backend automatically runs two-sample Kolmogorov-Smirnov tests to validate the statistical properties. The result is a mathematically rigorous CSV payload, fully sanitized with differential privacy, ready to drop straight into the Tracelight Excel engine today."

### Part 3: Workflow II - Post-Model Deliverables (1:05 - 2:00)
*(Screen: Click back to Home, then into Workflow II. Upload the `NovaCrest_Due_Diligence_Pack.pdf`. Hit Process, then Generate.)*

**Voiceover:** "Workflow II handles the 'final mile.' Once the analyst finishes the model in Tracelight, they upload the financial outputs alongside the raw due diligence pack—in this case, an 11-page PDF for the NovaCrest deal."

*(Screen: Walk through the section-by-section review dashboard. Point out a high confidence score and hover over an inline citation tag. Point out an amber-flagged section if visible.)*

**Voiceover:** "We use a RAG architecture with strict citation enforcement and an abstention protocol. If the context isn't in the docs, it refuses to hallucinate and flags the section amber. Every claim is tied to an immutable provenance vector."

*(Screen: Click the 'IC Memo' preview tab. Scroll through the inline document viewer briefly. Click the 'Exec Deck' preview tab and scroll.)*

**Voiceover:** "The engine automatically compiles the quantitative data and qualitative analysis into a fully formatted Word IC Memo and a native PowerPoint Executive Deck, viewable right here in the inline viewer before downloading."

### Part 4: The Wrap (2:00 - 2:15)
*(Screen: Return to the landing page.)*

**Voiceover:** "Two sidecars. Zero IP overlap with your core engine. We unblock the top of your funnel and automate the bottom. I’ll send over the architectural brief. Let’s find 15 minutes next week to dig into the copula implementation."

---

## The Parries (Handling Objections on the Follow-Up Call)

When you get them on the phone, they will stress-test the architecture. Use these exact rebuttals.

### Objection 1: Aleksander (CTO) on Math Rigor
**The Attack:** *"I don't trust LLMs to generate financial data. They hallucinate numbers, and the covariance structures are always wrong. Our clients will laugh at it."*
**The Parry:** "We completely agree, Aleksander. That's why the LLM is strictly isolated to semantic parameter extraction. It reads the prompt and outputs a JSON config. The actual data generation uses zero LLMs. We map a Cholesky decomposition of the target correlation matrix to standard normals, and apply a Gaussian copula to fit the marginal distributions. We validate every batch with internal KS-tests before it ever reaches the UI. It's deterministic quant math, not a prompt engineering trick."

### Objection 2: Janek (CPO) on RAG Hallucination
**The Attack:** *"Automatically writing an IC Memo is dangerous. RAG pipelines constantly make up citations or blend facts from different expert calls. How do you prevent that?"*
**The Parry:** "We enforce a strict abstention protocol governed by provenance vectors. During the embedding phase, every chunk is tagged with an immutable tuple of Document ID, Page, and Header. The generation agent is prompted to abstain if semantic similarity drops below our dynamic threshold. If it can't cite the specific provenance vector, it outputs 'Insufficient Data' and flags the section amber in the review dashboard for human intervention. It fails safe, not silently."

### Objection 3: Peter (CEO) on Build vs. Buy
**The Attack:** *"This is interesting, but we have a world-class engineering team. If we wanted this, we could just build it internally."*
**The Parry:** "You absolutely could, Peter. But your engineering bandwidth is your most constrained resource, and it needs to be laser-focused on your core IP: the in-spreadsheet COM architecture and formula auditing. Building secure, containerized sidecars requires a completely different tech stack—vector databases, document parsing pipelines, and copula math. We’ve already built it, it respescts your IP boundary entirely, and we can integrate it via API next week to start unblocking your stalled enterprise PoCs immediately."