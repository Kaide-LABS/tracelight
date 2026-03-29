# Layman Brief: Understanding the Tracelight "Sidecar" Demo

## The Core Concept: The Engine vs. The Factory

Think of Tracelight’s core product (their Excel AI) as a state-of-the-art, high-performance engine inside a massive manufacturing plant. It’s the most important piece of machinery, and it does its job flawlessly.

However, the factory has two major problems:
1.  **The Supply Chain is Blocked (Pre-Model):** The trucks delivering raw materials (real financial data) are stuck at the security gate for 6 months waiting for clearance. The engine sits idle.
2.  **The Shipping Department is Slow (Post-Model):** Once the engine produces the perfect finished part (the financial model), workers are taking 3 days to manually package it up into wooden crates (Word docs and PowerPoint decks) to show the boss.

**What we built:** We didn't build a new engine. We built two "sidecars" to fix the factory:
*   **Workflow I (The Supply Truck):** A system that instantly fabricates identical, highly realistic "dummy" materials so the engine can be tested and demonstrated without waiting for security clearance.
*   **Workflow II (The Shipping Robot):** A system that instantly packages the engine's output into polished, ready-to-present formats.

Crucially, **we never touch the engine itself.** We respect their territory. We only handle what goes in and what comes out.

## The Demo Narrative: The NovaCrest Deal

To make the demo feel real, everything revolves around a single, cohesive storyline.

**The Setup:** We are pretending to be an analyst at **Meridian Growth Partners** (a Private Equity firm). We are evaluating a potential $85M investment into a software company called **NovaCrest Analytics**.

NovaCrest is a B2B SaaS company that builds financial data infrastructure. They have $31M in Annual Recurring Revenue (ARR) and are growing at 72% year-over-year.

### How the Demo Works

**Workflow I (The Synthetic Data Generator)**
*   **What it looks like:** We type in a scenario like, "Generate 3 years of monthly SaaS revenue data for a company growing 72% YoY, with seasonal dips in Q3."
*   **What it does:** The system doesn't just guess numbers. It uses heavy-duty math to generate a highly realistic dataset (CSV file) that perfectly matches the statistical profile of a company like NovaCrest.
*   **Why it matters:** Tracelight can take this fake CSV, plug it into their Excel engine, and show a bank exactly how their product works on realistic data *today*, rather than waiting 6 months for real data.

**Workflow II (The Deliverable Engine)**
*   **The Input:** We upload a single PDF file called `NovaCrest_Due_Diligence_Pack.pdf`. This 11-page document contains everything the analyst knows about the deal: the company's pitch deck, transcripts of calls with management, interviews with industry experts, and a reference from a churned customer.
*   **The Action:** The system reads this entire PDF and combines it with the data we generated in Workflow I.
*   **The Output:** It automatically writes a multi-page Investment Committee (IC) Memo and builds an Executive PowerPoint deck.
*   **The Magic:** We don't just spit out a file to download. The demo has **inline preview windows**. You can scroll through the generated Word document and the PowerPoint deck directly inside the app, seeing exactly how the AI cited its sources ("According to the expert call on page 4...").

## Internal Glossary (Don't use these in the pitch, just know what they mean)
*   **Cholesky Decomposition / Gaussian Copula:** Very scary sounding math terms that simply mean "we generate fake data that statistically behaves exactly like real data, rather than just asking ChatGPT to make up random numbers."
*   **RAG (Retrieval-Augmented Generation):** Giving the AI an open-book test. Instead of relying on its memory, we force it to only read from the `NovaCrest_Due_Diligence_Pack.pdf` we uploaded.
*   **Citation Enforcement:** Forcing the AI to prove exactly where it got a piece of information by tagging the page and paragraph from the source document.
*   **Abstention Protocol:** Programming the AI to say "I cannot find this information in the provided documents" instead of guessing or hallucinating an answer.