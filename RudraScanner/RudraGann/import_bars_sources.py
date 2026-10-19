#!/usr/bin/env python3
"""Copy the public BARS stitched NQ 1m 2025/2026 CSVs into ASJR GitHub safely.
Run in /root/trading/ASJR-Gann detached worktree. No Chakra/live-tree changes.
Original source unchanged; resampling, merging and futures-roll reconciliation are separate.
"""
from __future__ import annotations
import csv
import hashlib
import subprocess
import tempfile
import urllib.request
from pathlib import Path

REPO=Path("/root/trading/ASJR")
OUT=Path("RudraScanner/ResearchData/Gann/Source/BARS")
BASE="https://raw.githubusercontent.com/kfccolonel1/BARS/main/NQ/1min/"
FILES=[
 "NQ_1min_2025-01-01_2025-12-31_stitched.csv",
 "NQ_1min_2026-01-01_2026-10-08_stitched.csv",
]
def git(cwd,*args):
    return subprocess.run(["git",*args],cwd=cwd,capture_output=True,text=True,timeout=120)

def main():
    origin=git(REPO,"remote","get-url","origin")
    if origin.returncode or "github.com" not in origin.stdout:
        print("BARS IMPORT | FAILED | ASJR origin missing");return 2
    with tempfile.TemporaryDirectory(prefix="rudra_bars_") as t:
        root=Path(t)
        paths=[]
        for filename in FILES:
            url=BASE+filename
            target=root/filename
            digest=hashlib.sha256()
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"ASJR-Gann-Research/1.0"}),timeout=100) as response, target.open("wb") as f:
                while True:
                    b=response.read(1024*1024)
                    if not b:break
                    digest.update(b);f.write(b)
            with target.open(newline="") as f:
                reader=csv.DictReader(f)
                headers=set(reader.fieldnames or [])
                if not {"datetime","open","high","low","close"}.issubset(headers):
                    raise ValueError(f"invalid OHLC headers for {filename}: {headers}")
                first=next(reader,None)
                last=first
                n=1 if first else 0
                for row in reader:
                    last=row;n+=1
            if n<100000:raise ValueError(f"unexpectedly small download {filename}: {n}")
            print(f"BARS SOURCE | {filename} | rows={n} | {first['datetime']} -> {last['datetime']} | sha256={digest.hexdigest()}",flush=True)
            paths.append((filename,target))
        folder=root/"repo"
        cp=subprocess.run(["git","clone","-q","--no-checkout","--shared",str(REPO),str(folder)],capture_output=True,text=True,timeout=120)
        if cp.returncode:print("BARS IMPORT | FAILED | clone");return 2
        git(folder,"remote","set-url","origin",origin.stdout.strip())
        git(folder,"config","user.name","ASJR Research Import")
        git(folder,"config","user.email","asjr-research-import@users.noreply.github.com")
        for attempt in range(4):
            if git(folder,"fetch","-q","origin","main").returncode:continue
            if git(folder,"checkout","-q","-B","bars-import-temp","FETCH_HEAD").returncode:continue
            rels=[]
            for name,source in paths:
                dest=folder/OUT/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                import shutil
                shutil.copyfile(source,dest)
                rels.append(str(OUT/name))
            if git(folder,"add","--",*rels).returncode:continue
            if git(folder,"diff","--cached","--quiet").returncode==0:
                print("BARS IMPORT | SUCCESS | ALREADY SAVED");return 0
            if git(folder,"commit","-qm","Research: archive public BARS NQ 1m 2025 and 2026 source files").returncode:continue
            push=git(folder,"push","-q","origin","HEAD:refs/heads/main")
            if push.returncode==0:
                print("BARS IMPORT | SUCCESS | PUSHED TO ASJR | "+", ".join(rels))
                return 0
            print(f"BARS IMPORT | push retry {attempt+1}/4",flush=True)
    print("BARS IMPORT | FAILED | GitHub push not confirmed");return 2

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print("BARS IMPORT | FAILED |",type(e).__name__,str(e)[:240])
        raise SystemExit(2)
