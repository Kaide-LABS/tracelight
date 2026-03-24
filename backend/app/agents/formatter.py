import pandas as pd
import os

def export(df: pd.DataFrame, output_format: str, job_id: str, output_dir: str) -> str:
    """Write to disk, return file path. NEVER writes .xlsx."""
    ext = output_format  # "csv" or "json"
    os.makedirs(output_dir, exist_ok=True)
    path = f"{output_dir}/{job_id}.{ext}"
    if output_format == "csv":
        df.to_csv(path, index=False)
    else:
        df.to_json(path, orient="records", indent=2)
    return path
