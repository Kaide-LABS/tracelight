import aiosqlite
import json
import os
from typing import Optional

DB_PATH = "/tmp/synth_output/jobs.db"

async def init_db():
    """Create jobs table if not exists. Called on startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                phase TEXT NOT NULL,           -- 'v1', 'v2', 'v3'
                status TEXT NOT NULL DEFAULT 'pending',
                request_json TEXT,             -- serialized request
                result_json TEXT,              -- serialized response
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await db.commit()

async def create_job(job_id: str, phase: str, request_data: dict) -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO jobs (job_id, phase, status, request_json, created_at, updated_at) VALUES (?, ?, 'pending', ?, ?, ?)",
            (job_id, phase, json.dumps(request_data), now, now)
        )
        await db.commit()

async def update_job(job_id: str, status: str, result_data: dict = None, error: str = None) -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE jobs SET status = ?, result_json = ?, error = ?, updated_at = ? WHERE job_id = ?",
            (status, json.dumps(result_data) if result_data else None, error, now, job_id)
        )
        await db.commit()

async def get_job(job_id: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = await cursor.fetchone()
        if row:
            return {
                "job_id": row["job_id"],
                "phase": row["phase"],
                "status": row["status"],
                "request": json.loads(row["request_json"]) if row["request_json"] else None,
                "result": json.loads(row["result_json"]) if row["result_json"] else None,
                "error": row["error"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        return None
