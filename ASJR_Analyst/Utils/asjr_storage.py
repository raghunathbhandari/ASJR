import json
from pathlib import Path
import pandas as pd

def save_csv(df, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return str(path)

def load_csv(path):
    return pd.read_csv(path)

def save_json(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return str(path)

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
