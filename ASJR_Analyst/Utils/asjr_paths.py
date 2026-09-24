from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
DATALAKE = ROOT / "DataLake"

def trading_day(value=None):
    if value is None:
        return date.today().isoformat()
    return value.isoformat() if hasattr(value, "isoformat") else str(value)

def day_dir(value=None, create=True):
    p = DATALAKE / trading_day(value)
    if create:
        for name in ("config", "raw", "processed", "reports"):
            (p / name).mkdir(parents=True, exist_ok=True)
    return p

def raw_path(filename, value=None):
    return day_dir(value) / "raw" / filename

def processed_path(filename, value=None):
    return day_dir(value) / "processed" / filename

def report_path(filename, value=None):
    return day_dir(value) / "reports" / filename

def config_path(filename, value=None):
    return day_dir(value) / "config" / filename
