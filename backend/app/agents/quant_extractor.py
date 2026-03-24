import pandas as pd
import json
import os
from app.schemas_v2 import CitedMetrics, FinancialMetric

class QuantExtractor:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def extract_from_job(self, job_id: str) -> CitedMetrics:
        csv_path = os.path.join(self.output_dir, f"{job_id}.csv")
        json_path = os.path.join(self.output_dir, f"{job_id}.json")

        df = None
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
        elif os.path.exists(json_path):
            df = pd.read_json(json_path)
        else:
            raise FileNotFoundError("Financial data job not found")

        metrics = []
        # Compute summary stats for numerical columns
        numeric_cols = df.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            mean_val = df[col].mean()
            metrics.append(FinancialMetric(
                name=f"{col}_mean",
                value=round(mean_val, 2),
                unit="",
                scenario="base",
                source_tag=f"model_export:{col}:mean"
            ))
            
            median_val = df[col].median()
            metrics.append(FinancialMetric(
                name=f"{col}_median",
                value=round(median_val, 2),
                unit="",
                scenario="base",
                source_tag=f"model_export:{col}:median"
            ))

        return CitedMetrics(
            company_name="Synthetic Target",
            deal_type="LBO",
            currency="USD",
            metrics=metrics
        )
