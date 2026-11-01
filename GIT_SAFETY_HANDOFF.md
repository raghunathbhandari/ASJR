# ASJR Git Safety Handoff — 2026-11-01

## Non-negotiable rules
1. **Never force-push** `main`, run `git reset --hard`, or delete/stash broad runtime directories to fix a sync problem.
2. **Preserve user data:** untracked CSVs, research results, IBKR market data, DataLake logs, bot state and locks may be live. Inspect `git status -sb` before operations; never clean them blindly.
3. **Multiple writers:** Windows PC, VPS production, research worktrees, GitHub automation and DataLake cleanup update the same repository. A non-fast-forward rejection means remote `main` advanced. Fetch, inspect, integrate safely; never overwrite remote history.
4. **Worktree mapping:** `/root/trading/ASJR` owns checked-out `main`; `/root/trading/ASJR-Synced` and `/root/trading/ASJR-Gann` may be detached. `git push origin main` from a detached worktree pushes the *other* worktree's local `main`, not the current HEAD. Always inspect `git worktree list`, `git branch -avv`, `git status -sb`.
5. **Production code updates:** `git fetch origin`; when local `main` has no unique commits and files do not conflict, `git pull --ff-only origin main`. If Git blocks an update, stop and inspect; do not force it.
6. **PC development:** fetch/pull before edits; commit only intended files; integrate remote changes before push. A rebase requires a clean or deliberately preserved worktree.
7. **ASJR Analyst DataLake publishing:** `ASJR_Analyst/Utils/asjr_git.py` was replaced by Git Publisher v2 in commit `62468a216`. It uses an isolated temporary clone, stages only the daily DataLake folder, and retries push races up to 3 times. Do not regress to direct `git push origin main` from production. The callable entry point remains `submit_datalake(...)`.
8. **Result semantics:** `PUSHED` = published; `NO_CHANGES` = no commit needed; `PENDING` = publish not completed and must be investigated/retried. Never treat `PENDING` as successfully published.
9. **Testing:** syntax/import checks have passed on VPS. End-to-end DataLake publishing under a concurrent update has **not yet been verified**; monitor the next scheduled run.
10. **No editor requirement:** user prefers explicit non-interactive commands/patches and wants UK time in logs/reports.

## 2026-11-01 incident
- Production `main` was 106 commits behind `origin/main`, with zero local-only commits and many valuable untracked runtime files.
- `/root/trading/ASJR-Synced` was detached at `f83c76500`; its untracked research files blocked checkout. Four files were preserved under `/root/trading/ASJR-Synced-local-backup/`; Synced then checked out `origin/main` detached.
- Production safely fast-forwarded to `0e9a3f6af`, then pulled Git Publisher v2 commit `62468a216`.
- VPS `python3 -m py_compile ASJR_Analyst/Utils/asjr_git.py` and Python import smoke test passed.
- Future automation/tooling must distinguish Git publisher errors from data collection success, avoid modifying live production working trees during publication, and stop on actual file conflicts.
