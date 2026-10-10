"""Save the two discovery CSVs and diagnostics under the existing DataLake."""

import csv
import json
import os
from pathlib import Path

from .discovery import AI_FIELDS, IBKR_FIELDS, merge_candidates, read_ai_csv, run_ibkr_scans, utc_text


def _atomic(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _csv_text(fields, rows):
    import io
    fh = io.StringIO(newline="")
    writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return fh.getvalue()


def save_discovery(app, trade_date, *, repo_root, timeout=5.0, now=None):
    """Isolated manual/test entry point. NOT invoked by the production job.

    The AI input is read-only for Chakra. Copy the exact bytes used, including
    disabled/expired rows, before validating; never write the AI-owned file.
    """
    root = Path(repo_root)
    canonical = root / "ASJR_Analyst" / "config" / "ai_scanner_list.csv"
    raw = root / "ASJR_Analyst" / "DataLake" / str(trade_date) / "raw"
    processed = raw.parent / "processed"
    raw.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    ai_rows, ai_status = read_ai_csv(canonical, now=now)
    _atomic(raw / "ai_scanner_list.csv",
            canonical.read_text(encoding="utf-8-sig") if canonical.is_file()
            else _csv_text(AI_FIELDS, []))
    ibkr_rows, scan_status = run_ibkr_scans(app, timeout=timeout, now=now)
    candidates = merge_candidates(ai_rows, ibkr_rows)
    _atomic(raw / "ibkr_scanner_list.csv", _csv_text(IBKR_FIELDS, ibkr_rows))
    _atomic(raw / "scanner_status.json", json.dumps({
        "generated_at_utc": utc_text(now), "ai": ai_status, "ibkr": scan_status,
        "candidate_count": len(candidates)
    }, indent=2) + "\n")
    _atomic(processed / "scalp_radar_candidates.csv", _csv_text(
        ("ticker", "sources", "scan_codes", "ai_bias", "ai_freshness"),
        [{**r, "sources": "+".join(r["sources"]),
          "scan_codes": "+".join(r["scan_codes"])} for r in candidates]))
    return {"candidates": candidates, "ai": ai_status, "ibkr": scan_status}


def read_saved_report(repo_root, trade_date):
    """Read, never recompute, the future authoritative mechanical output."""
    day = Path(repo_root) / "ASJR_Analyst" / "DataLake" / str(trade_date)
    report = day / "reports" / "scalp_radar.txt"
    if not report.is_file():
        return f"RUDRA RADAR | {trade_date} | DATA NOT READY (no saved report)"
    return report.read_text(encoding="utf-8")
