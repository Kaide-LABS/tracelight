# Tracelight: Business Intelligence Brief

## 1. Executive Summary
**Target Company:** Tracelight (https://tracelight.ai)
**Target Audience:** 
- **Peter Fuller (CEO):** Ex-McKinsey. Focused on deal velocity, top-line revenue, and go-to-market strategy.
- **Aleksander Misztal (CTO):** Ex-Jane Street. Obsessed with deterministic math, system latency, and quantitative rigor. 
- **Janek Zimoch (CPO):** Ex-Cambridge ML. Focused on RAG architecture, UX, and hallucination prevention.

## 2. The Core Product
Tracelight is a highly specialized B2B SaaS product that embeds an Artificial Intelligence engine directly into Microsoft Excel. It is designed specifically for top-tier Private Equity funds, asset managers, and elite management consultancies.
- **What it does:** It translates complex financial modeling intent into functional spreadsheet logic. It automates the mechanical, error-prone workload of building LBOs, DCFs, and cohort analyses. 
- **Technical mechanics:** It acts as a probabilistic translation layer inside the spreadsheet, reading cell structures and user intent to write and audit Excel formulas in real-time. 

## 3. The Pain Points They Solve
In high finance, analysts spend 80% of their time on "mechanical" spreadsheet formatting and formula checking, and only 20% on actual strategic thinking. Tracelight flips this ratio, allowing a PE analyst to build an LBO model in 8 minutes instead of 8 hours, massively accelerating deal velocity.

## 4. How They Make Money
Enterprise SaaS licensing. They sell high-ticket, org-wide seats to firms managing billions in AUM. Because their users deal with highly confidential financial data, enterprise security, compliance, and trust are the absolute core of their sales motion.

## 5. The Strategic Gap (Our Opening)
While Tracelight has perfected the "center" of the workflow (the Excel model), their operational periphery is broken:
- **Pre-Sales Friction:** As Aleksander noted on LinkedIn, their sales cycles have a 3-6 month dead zone. InfoSec refuses to let prospects use real portfolio data to test Tracelight's AI. 
- **Post-Sales Friction:** After using Tracelight, the analyst still has to manually copy-paste the Excel outputs into 50-page Word Investment Committee (IC) Memos and PowerPoint decks.
- **Internal Friction:** Their elite ex-Jane Street engineering team is wasting hundreds of hours answering basic SOC2 and SIG security questionnaires for bank procurement teams.

**Our Wedge:** We are building the sidecars that solve these peripheral bottlenecks. By explicitly avoiding their core product (no `.xlsx` interactions), we prove we are a complementary integration, not a competitor.