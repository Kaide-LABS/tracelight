# Tracelight Sidecar Demo Brief

## 1. Executive Overview

**What this is:** A working, pitch-ready prototype demonstrating how AI-driven "sidecar" applications can extend Tracelight's value proposition beyond the spreadsheet. The demo features three self-contained workflows that address massive operational bottlenecks for enterprise clients.

**Who we are pitching:** The founding team of Tracelight — Peter Fuller (CEO, ex-McKinsey), Aleksander Misztal (CTO, ex-Jane Street), and Janek Zimoch (CPO, ex-Cambridge ML). 

**The Key Constraint (The "DMZ" Rule):** This demo intentionally **never touches Excel files (`.xlsx`)** or tries to write formulas. It respects Tracelight's core IP boundaries, proving we understand their product and can build complementary—not competitive—technology. 

**The Core Value Proposition:** Tracelight perfected the "center" of the workflow (financial modeling). These sidecar apps automate the "periphery" (pre-model data generation, post-model document drafting, and vendor risk compliance), turning Tracelight from an Excel plugin into the system of record for the entire deal lifecycle, increasing deal velocity and reducing enterprise friction.

---

## 2. Workflow-by-Workflow Walkthrough (Recording Script)

*Ensure **Demo Mode** is toggled ON in the sidebar before recording. This guarantees instant, error-free results with zero live API latency.*

**1. Landing Page (0:00 - 0:15)**
- **Action:** Start on the landing page showing the three workflow cards.
- **Narration:** "Tracelight has solved the core computational bottleneck in Excel. Today, I want to show you three 'sidecar' workflows we've built that operate entirely around the spreadsheet. These address the massive operational friction before and after the financial model, without ever touching your core Excel IP."

**2. Workflow I: Synthetic Financial Data Generator (0:15 - 1:45)**
- **Action:** Click "Launch" on Workflow I. Select the "PE LBO" preset. Click "Generate Synthetic Data". 
- **Narration:** "When you pitch top-tier funds, InfoSec prevents them from sharing real portfolio data for PoCs, stalling sales cycles for months. We built a mathematically rigorous synthetic data generator to solve this. It translates natural language scenarios into deterministic statistical parameters."
- **Action:** Scroll through the Data Preview table and the Distribution/Correlation charts. Open the Validation Report expander.
- **Narration:** "Using Cholesky decomposition and Gaussian copulas, we generate highly correlated, realistic time-series data. It even runs Kolmogorov-Smirnov tests to prove statistical validity and applies differential privacy."
- **Action:** Click the "Download CSV" button. 
- **Narration:** "Clients can instantly download this CSV and import it into Tracelight models to evaluate your product. We collapse PoC timelines from six months to six minutes."

**3. Workflow II: Post-Excel Deliverable Engine (1:45 - 3:15)**
- **Action:** Navigate to Workflow II. Click "Process Documents" (Demo Mode will auto-load). Enter "Acme Capital" for Firm Name, click "Generate Deliverables".
- **Narration:** "After an analyst builds a model in Tracelight, they still spend 72 hours manually copying outputs into 50-page Investment Committee memos. This is the final mile bottleneck. This engine ingests source documents and financial data, drafting the IC memo via citation-enforced RAG."
- **Action:** Slowly scroll through the generated sections. Pause on the "Market Analysis" section that is flagged amber. Point out a `[source_tag]` citation.
- **Narration:** "Notice these tags—every single claim is tied to source evidence. If the AI lacks data, like in this flagged section, it refuses to hallucinate and requires analyst input instead."
- **Action:** Click "Download DOCX".
- **Narration:** "This turns Tracelight into the system of record for the entire deal lifecycle, producing audit-ready deliverables."

**4. Workflow III: InfoSec & Vendor Risk Compliance Engine (3:15 - 4:45)**
- **Action:** Navigate to Workflow III. Click "Index to KB + Parse Questionnaire", then click "Generate Responses".
- **Narration:** "Finally, as you sell into enterprise, your ex-Jane Street engineers are wasting hundreds of hours filling out 800-question SIG security assessments. This compliance engine automates it. It ingests the questionnaire, semantically searches your internal SOC 2 reports and policies, and auto-drafts cited responses."
- **Action:** Point out the dashboard metrics (e.g., 16 Auto-Approved, 4 Needs Review). Open a "Needs Review" row to show the editable response. Click "Approve".
- **Narration:** "High-confidence answers are auto-approved, while edge cases are routed to a human reviewer with the exact source documents attached."
- **Action:** Click "Download Completed Questionnaire".
- **Narration:** "Your engineers get back to building product, and you pass enterprise procurement effortlessly."

**5. Wrap Up (4:45 - 5:00)**
- **Action:** Navigate back to the Landing Page.
- **Narration:** "Three agentic sidecar workflows. Zero overlap with your core Excel IP. Immediate ROI. Let's discuss bringing this to production."

---

## 3. Talking Points per Audience Member

### Peter Fuller (CEO, ex-McKinsey)
*Focus: Revenue, Deal Velocity, Go-To-Market*
- **Accelerated Sales Cycles:** The synthetic data generator bypasses the 6-month legal/InfoSec dead zone so prospects can trial Tracelight immediately.
- **Expanding ACV (Annual Contract Value):** By generating the final IC Memos and Pitch Decks, you capture the entire analyst workflow, not just the spreadsheet layer. You can charge a premium for final-mile deliverables.
- **McKinsey Framing:** The narrative engine is structured precisely around the Pyramid Principle—leading with the recommendation and following with MECE (Mutually Exclusive, Collectively Exhaustive) supporting data.

### Aleksander Misztal (CTO, ex-Jane Street)
*Focus: Mathematical Rigor, Determinism, IP Protection*
- **Strict DMZ Rule:** We explicitly designed this to never read, write, or parse `.xlsx` files. Your in-Excel AI engine is your moat; these sidecars plug into the periphery without stepping on your IP.
- **Math over LLMs:** The synthetic data isn't hallucinated by an LLM. The LLM only acts as a profiler; the actual generation uses pure NumPy/SciPy deterministic math (Cholesky decomposition, Gaussian copulas).
- **Engineering Efficiency:** The compliance engine gets your engineers out of procurement spreadsheets so they can focus on shipping features.

### Janek Zimoch (CPO, ex-Cambridge ML)
*Focus: RAG Architecture, Hallucination Prevention, UX*
- **Citation-Enforced RAG:** The deliverable engine uses a source-first prompting architecture. It doesn't just draft text; it maps every single claim to an exact document and page number.
- **Abstention over Hallucination:** If the retrieval step fails to find supporting evidence, the agent is programmed to explicitly abstain (inserting `[INSUFFICIENT DATA]`) and flag the section for human review.
- **Differential Privacy:** The synthetic engine doesn't just generate data; it validates it against target distributions using KS-tests and applies calibrated Laplace noise for mathematical privacy guarantees.

---

## 4. FAQ / Objection Handling

**Objection (Peter/CEO):** *"Why are you building outside of Excel? Our whole value prop is that analysts never have to leave the spreadsheet."*
**Response:** "Your core IP is the in-Excel experience, and we respect that. But the data required for an IC memo (e.g., PDFs of management presentations) and the outputs (Word/PowerPoint) inherently exist *outside* Excel. By owning the 'last mile' export, you capture more of the firm's overall workflow without cluttering your core Excel add-in."

**Objection (Aleksander/CTO):** *"LLMs are terrible at math and consistency. How can I trust synthetic financial data generated by an AI?"*
**Response:** "You shouldn't. That's why the LLM doesn't generate the data. The LLM only translates the user's scenario into a JSON statistical profile. A deterministic math engine (NumPy) takes that profile and uses Cholesky decomposition to draw the samples. The math is completely isolated from the language model."

**Objection (Janek/CPO):** *"RAG is notoriously leaky. How do you prevent the memo generator from inventing numbers that look plausible but are wrong?"*
**Response:** "Strict citation enforcement. The prompt instructions require every factual claim to be followed by a `[source_tag]`. Post-generation, a deterministic script parses those tags and verifies they exist in the grounded input data. If a tag is missing or fabricated, the section's confidence score plummets and it is routed for human review."

---

## 5. Technical Cheat Sheet (For the Co-Founder)

*Keep this handy while recording in case you need to speak to the underlying tech.*

- **Cholesky Decomposition & Gaussian Copula:** The math techniques used in Workflow I to ensure the synthetic variables (like Revenue and Margin) move together realistically, rather than just generating random, unconnected numbers. (Standard practice in quantitative finance).
- **Kolmogorov-Smirnov (KS) Test:** A statistical test used to prove that the synthetic data we generated actually matches the shape of real-world data distributions.
- **Differential Privacy (Laplace Noise):** A mathematical guarantee that you cannot reverse-engineer the original data from the synthetic data. We achieve this by adding a tiny, calculated amount of statistical "noise" to the numbers.
- **RAG (Retrieval-Augmented Generation):** Instead of relying on the AI's general knowledge, we force the AI to read specific documents (like a SOC 2 report) and only answer questions based on what it finds in those documents.
- **ChromaDB / Embeddings:** How we store documents so the AI can search them. We break PDFs into chunks, convert them into mathematical vectors (embeddings), and store them in ChromaDB for instant similarity searching.
- **Citation Enforcement:** A safety mechanism where the AI is banned from writing a fact unless it explicitly tags the document and page number it got the fact from.