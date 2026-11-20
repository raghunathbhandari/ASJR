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

## 2026-11-20 — concurrent Git sync and large-history verification

- The VPS returned health job research-1795165868530 at 09:11 GMT. This proves a request/result round trip, not that the live checkout matches GitHub. A repeated result commit is not a new successful collection.
- The revised bridge locks service/one-shot runs together, reads requests and results at one immutable fetched commit, saves completed reports before upload, and never replaces a result that already exists on main. Local unsent reports live under the Git common directory (asjr-research-bridge); do not delete them to resolve a failure. A process killed during a job, before its report was saved, is not guaranteed exactly-once execution.
- The live Git command refuses dirty/diverged main and ignored-file collisions; it fast-forwards to a pinned SHA, not FETCH_HEAD. The detached research sync does not reconcile a diverged live main. Daily publishing remains isolated: a concurrent edit to the same day's folder is PENDING, not a reason to force a push.
- Deployment: use the operator's normal clean fast-forward, then refresh **only** the existing research bridge service. A running Python process does not reload by virtue of a git pull. The external Discord adapter and daily publisher load their changes at their next normal process start. Do not restart trading to run this check. A fresh health result reporting worker_sync_version 2 verifies the revised worker is active; its request_main and checkout_head refer to different things.
- If a legacy gitpull reports multiple branches: on the VPS check the expected repository/remote, branch main, and a clean tracked status. Fetch without writing FETCH_HEAD; pin refs/remotes/origin/main to a full SHA, check that HEAD is its ancestor, then merge that SHA with --ff-only --no-overwrite-ignore. Stop on divergence, a file collision, or an auth/policy error. Never stash/reset the trading checkout as an automatic remedy.
- Large RVOL5 CSVs may be too large for GitHub's file preview/contents interface. That is not a failed VPS push. Use a read-only Git checkout at a pinned main SHA, or GitHub's **Download ZIP at that SHA**. For a ZIP, match its commit and each input's byte count and Git blob object ID to the untruncated tree. Compare the actual cumulative profiles and raw 5m bars, not file counts, CSV lengths, or old VPS messages. Preserve the active fallback reference if durable state is not tracked.
- Snapshot 5154c36ac35348a6209c60f505e4c06eff604314: nine archived rolling references and nine raw/intraday_5m.csv files were hash-verified. The 15 November cutoff excluded newer dates from removal. The 16, 19, 20, 29, 30 October and 2, 3, 9, 10 November folders were all retained: needed profiles, unresolved raw recovery rows, or the newest tracked fallback lacked proven replacement. No data or state was removed. Re-evaluate on new input; this is not a permanent list of dates to retain.
