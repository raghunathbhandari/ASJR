#!/usr/bin/env python3
"""Non-destructive ASJR Git mismatch recovery for research code.
Never reset/stash/rebase/merge/clean the live trading checkout.
Keeps latest origin/main in an isolated detached research worktree.
"""
from __future__ import annotations
import subprocess
import re
from pathlib import Path

LIVE = Path("/root/trading/ASJR")
RESEARCH = Path("/root/trading/ASJR-Synced")

def run(*args, cwd=None, timeout=90):
    return subprocess.run(["git", *args], cwd=LIVE if cwd is None else cwd, text=True,
                          capture_output=True, timeout=timeout, check=False)

def main():
    if not (LIVE/".git").exists():
        print("GIT SAFE SYNC | REFUSED | live repository missing")
        return 2
    lock = LIVE/".git/index.lock"
    if lock.exists():
        print("GIT SAFE SYNC | REFUSED | git index locked; possible active Chakra Git operation")
        return 2
    ref = "refs/remotes/origin/main"
    fetched=run("fetch","--quiet","--no-write-fetch-head","--no-tags","--refmap=",
                "origin","refs/heads/main:" + ref)
    if fetched.returncode:
        print("GIT SAFE SYNC | FAILED | could not fetch origin/main")
        return 2
    pinned = run("rev-parse", "--verify", ref + "^{commit}")
    target = pinned.stdout.strip()
    if pinned.returncode or not re.fullmatch(r"(?:[a-f0-9]{40}|[a-f0-9]{64})", target):
        print("GIT SAFE SYNC | FAILED | no verified remote commit")
        return 2
    ahead=run("rev-list","--left-right","--count","HEAD..." + target)
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
        done=run("worktree","add","--detach",str(RESEARCH),target,timeout=120)
        if done.returncode:
            print("RESEARCH WORKTREE | FAILED |",done.stderr.strip()[-250:])
            return 2
    else:
        same=run("rev-parse","--show-toplevel",cwd=RESEARCH)
        if same.returncode or Path(same.stdout.strip()).resolve()!=RESEARCH.resolve():
            print("RESEARCH WORKTREE | REFUSED | unexpected existing directory")
            return 2
        common=run("rev-parse","--path-format=absolute","--git-common-dir",cwd=RESEARCH)
        live_common=run("rev-parse","--path-format=absolute","--git-common-dir",cwd=LIVE)
        if (common.returncode or live_common.returncode
                or Path(common.stdout.strip()).resolve()!=Path(live_common.stdout.strip()).resolve()
                or run("symbolic-ref","--quiet","HEAD",cwd=RESEARCH).returncode != 1):
            print("RESEARCH WORKTREE | REFUSED | not the detached ASJR research worktree")
            return 2
        dirty=run("status","--porcelain","--untracked-files=all",cwd=RESEARCH)
        if dirty.returncode or dirty.stdout.strip():
            print("RESEARCH WORKTREE | REFUSED | uncommitted work; preserving files")
            return 2
        done=run("switch","--detach","--no-overwrite-ignore",target,cwd=RESEARCH,timeout=120)
        if done.returncode:
            print("RESEARCH WORKTREE | FAILED | cannot checkout origin/main without overwriting work")
            return 2
    head=run("rev-parse","--verify","HEAD",cwd=RESEARCH)
    if head.returncode or head.stdout.strip() != target:
        print("RESEARCH WORKTREE | FAILED | HEAD differs from the fetched commit")
        return 2
    print("RESEARCH WORKTREE | READY |",RESEARCH,"|",head.stdout.strip())
    print("LIVE GIT DIVERGENCE | NOT MERGED | requires separate controlled reconciliation")
    print("CHAKRA | UNCHANGED")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
