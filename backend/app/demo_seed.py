"""
Demo data seed script.

NOTE: phase2_sample_response.json, phase2_sample_memo.docx, and phase2_sample_deck.pptx
are hand-crafted NovaCrest demo assets. This script only regenerates Phase 1 fixtures.
Run from project root: python -m app.demo_seed
"""
import os
import json
import numpy as np
import pandas as pd

DEMO_DIR = "frontend/demo_data"
os.makedirs(DEMO_DIR, exist_ok=True)

# Phase 1: Synthetic Data — NovaCrest financial scenario
# 50 entities (comparable SaaS companies) × 20 quarters × 5 variables
np.random.seed(42)

n_entities = 50
n_quarters = 20
quarters = [f"Q{(q % 4) + 1}-{2021 + q // 4}" for q in range(n_quarters)]

rows = []
for entity_id in range(1, n_entities + 1):
    base_rev = np.random.uniform(5, 40)  # $M ARR
    growth_rate = np.random.uniform(0.03, 0.12)  # quarterly growth
    base_margin = np.random.uniform(0.65, 0.85)
    base_nrr = np.random.uniform(1.05, 1.50)
    base_cac = np.random.uniform(8, 20)  # months

    for q in range(n_quarters):
        rev = base_rev * (1 + growth_rate) ** q + np.random.normal(0, base_rev * 0.03)
        margin = base_margin + np.random.normal(0, 0.02)
        nrr = base_nrr + np.random.normal(0, 0.03)
        cac = base_cac + np.random.normal(0, 1.5)
        rule40 = (growth_rate * 4 * 100) + (margin * 100 - 100) + np.random.normal(0, 3)

        rows.append({
            "entity_id": entity_id,
            "quarter": quarters[q],
            "ARR_M": round(max(rev, 0.5), 2),
            "Gross_Margin": round(np.clip(margin, 0.4, 0.95), 4),
            "Net_Retention_Rate": round(np.clip(nrr, 0.8, 1.8), 4),
            "CAC_Payback_Months": round(max(cac, 2), 1),
            "Rule_of_40": round(rule40, 1),
        })

df = pd.DataFrame(rows)
df.to_csv(f"{DEMO_DIR}/phase1_sample_data.csv", index=False)

with open(f"{DEMO_DIR}/phase1_sample_response.json", "w") as f:
    json.dump({
        "job_id": "demo_job_123",
        "scenario": {
            "natural_language": "Growth-stage B2B SaaS, financial data infrastructure vertical, high NRR, land-and-expand model",
            "use_llm_profiler": True
        },
        "privacy": {"enabled": True, "epsilon": 1.0},
        "output_format": "csv",
        "profile_used": {
            "name": "B2B SaaS Growth Equity",
            "asset_class": "growth_equity",
            "num_entities": n_entities,
            "time_horizon_years": 5,
            "frequency": "quarterly",
            "variables": {
                "ARR_M": {
                    "distribution": "lognormal",
                    "mean": 18.5,
                    "std": 8.2,
                    "type": "continuous"
                },
                "Gross_Margin": {
                    "distribution": "beta",
                    "mean": 0.78,
                    "std": 0.05,
                    "type": "continuous"
                },
                "Net_Retention_Rate": {
                    "distribution": "normal",
                    "mean": 1.25,
                    "std": 0.12,
                    "type": "continuous"
                },
                "CAC_Payback_Months": {
                    "distribution": "lognormal",
                    "mean": 14,
                    "std": 3.5,
                    "type": "continuous"
                },
                "Rule_of_40": {
                    "distribution": "normal",
                    "mean": 42,
                    "std": 12,
                    "type": "continuous"
                }
            }
        },
        "validation_report": {
            "row_count": len(df),
            "correlation_rmse": 0.042,
            "dp_applied": True,
            "dp_epsilon": 1.0,
            "post_dp_ks_all_passed": True,
            "ks_tests": {
                "ARR_M": {"statistic": 0.018, "p_value": 0.97, "passed": True},
                "Gross_Margin": {"statistic": 0.024, "p_value": 0.93, "passed": True},
                "Net_Retention_Rate": {"statistic": 0.021, "p_value": 0.95, "passed": True},
                "CAC_Payback_Months": {"statistic": 0.029, "p_value": 0.91, "passed": True},
                "Rule_of_40": {"statistic": 0.015, "p_value": 0.98, "passed": True}
            }
        }
    }, f, indent=2)

print(f"Phase 1 fixtures created: {len(df)} rows ({n_entities} entities × {n_quarters} quarters × 5 variables)")
print("Phase 2 fixtures are hand-crafted — not overwritten.")
