#!/usr/bin/env python3
"""Non-destructive ASJR Git mismatch recovery for research code.
Never reset/stash/rebase/merge/clean the live trading checkout.
Keeps latest origin/main in an isolated detached research worktree.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

LIVE = Path("/root/trading/ASJR")
RESEARCH = Path("/root/trading/ASJR-Synced")

def run(*args, cwd=LIVE, timeout=90):
    return subprocess.run(["git", *args], cwd=cwd, text=True,
                          capture_output=True, timeout=timeout, check=False)

def main():
    if not (LIVE/".git").exists():
        print("GIT SAFE SYNC | REFUSED | live repository missing")
        return 2
    lock = LIVE/".git/index.lock"
    if lock.exists():
        print("GIT SAFE SYNC | REFUSED | git index locked; possible active Chakra Git operation")
        return 2
    fetched=run("fetch","--quiet","origin","main")
    if fetched.returncode:
        print("GIT SAFE SYNC | FAILED | could not fetch origin/main")
        return 2
    ahead=run("rev-list","--left-right","--count","HEAD...origin/main")
    if ahead.returncode:
        print("GIT SAFE SYNC | FAILED | cannot compare commits")
        return 2
    stat=run("status","--porcelain","--untracked-files=normal")
    if stat.returncode:
        print("GIT SAFE SYNC | FAILED | cannot check live status")
        return 2
    print("LIVE ASJR | local-only / remote-only:",ahead.stdout.strip().replace("\t"," / "))
    print("LIVE ASJR | dirty paths:",len(stat.stdout.splitlines()))
    print("LIVE ASJR | UNCHANGED | no stash, reset, merge or deletion")
    if not RESEARCH.exists():
        done=run("worktree","add","--detach",str(RESEARCH),"origin/main",timeout=120)
        if done.returncode:
            print("RESEARCH WORKTREE | FAILED |",done.stderr.strip()[-250:])
            return 2
    else:
        same=run("rev-parse","--show-toplevel",cwd=RESEARCH)
        if same.returncode or Path(same.stdout.strip()).resolve()!=RESEARCH.resolve():
            print("RESEARCH WORKTREE | REFUSED | unexpected existing directory")
            return 2
        dirty=run("status","--porcelain","--untracked-files=all",cwd=RESEARCH)
        if dirty.returncode or dirty.stdout.strip():
            print("RESEARCH WORKTREE | REFUSED | uncommitted work; preserving files")
            return 2
        done=run("switch","--detach","origin/main",cwd=RESEARCH,timeout=120)
        if done.returncode:
            print("RESEARCH WORKTREE | FAILED | cannot checkout origin/main without overwriting work")
            return 2
    head=run("rev-parse","--short","HEAD",cwd=RESEARCH)
    print("RESEARCH WORKTREE | READY |",RESEARCH,"|",head.stdout.strip())
    print("LIVE GIT DIVERGENCE | NOT MERGED | requires separate controlled reconciliation")
    print("CHAKRA | UNCHANGED")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
