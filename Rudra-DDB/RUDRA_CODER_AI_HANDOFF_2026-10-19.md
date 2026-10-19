# Rudra Coder — AI Handoff and Maintenance Playbook
**Date:** 19 October 2026 · **System:** ASJR / Chakra / Rudra-DDB

## Who am I in the next session?
**Rudra Coder** is the ASJR maintenance and coding assistant. Responsibilities: protect Chakra's live five-minute IBKR pipeline, DataLake, alert state, research datasets, and GitHub/VPS synchronization; inspect GitHub source and actual VPS logs; distinguish *committed to GitHub*, *deployed to VPS*, and *verified running*. Never claim Discord or VPS commands executed by ChatGPT when merely editing GitHub. Primary operating instructions: `ASJR_Analyst/OPERATIONAL_HANDOFF.md`; this page is the incident recovery handoff in `Rudra-DDB/`.

## Incident on 19 October 2026 — evidence and resolution
- Spidey repeatedly reported `git pull --rebase origin main` blocked by unstaged tracked DataLake changes every ~5 minutes.
- VPS had **126 local-only vs 124 remote-only** commits while on main. About **21 tracked DataLake files** were modified; many untracked backtesting, research and alert-state files also existed.
- The bot was stopped before recovery. User created Git bundle (177 MB) and working files archive (50 MB) at `/root/trading/asjr-recovery-20261019-164252`.
- `git branch backup-vps-20261019`; `git stash push -u`; `git merge --no-edit origin/main` **succeeded**. Stash apply partially failed on already-existing untracked research files; **all 21 tracked DataLake files were restored** and committed (`fe127e78b`).
- Later VPS/GitHub returned `0 0`; user elected to delete the temporary 227 MB archive. Backup Git branch and `stash@{0}` were kept.
- User's `asjr_git.py` lines 103–104 confirmed removal of automatic `pull --rebase`, leaving `git push origin main`. Commit shown by the bot as `b4524e681 Fix recurring Chakra Git rebase error`. Python compilation passed.
- `!mbdstart` succeeded at **16:52 BST** and `!runSCommand bot` returned running. Early latest log showed 64 movers, 79-ticker universe, Yahoo daily 2,315 rows, IBKR 5m fetch started. **Completed post-restart five-minute cycle and successful automatic Git push were not yet established in shared logs.**
- `!runSCommand logs errors 20` at 16:53 had no output, but this alone is not end-to-end proof.
- Don't repeat failed diagnoses: the attempted exact-string and regex source patches returned assertion/no-match on one pass because the code had already changed. **Inspect current source first**.

## Architectural root cause
`ASJR_Analyst/Utils/asjr_git.py::submit_datalake` used to commit today's DataLake and then rebase the entire live checkout before pushing. Chakra and other workflows continually write tracked DataLake files, making that rebase unsafe. Removing live rebase prevents the *specific* recurrent error, but can still produce non-fast-forward push rejection when GitHub changes concurrently. Future permanent design: isolated publication worktree/clone, selective DataLake snapshots, serialized publishing, non-destructive retries, and bounded retention. Git failure must never prevent IBKR data capture or alerts. Do not implement that architecture by silently rewriting Chakra's external launcher.

## Supported Discord commands and limitations
| Command | Purpose | Status |
|---|---|---|
| `!runSCommand bot` | tmux session status | confirmed working |
| `!runSCommand git` | tracked changes (read-only) | confirmed working |
| `!runSCommand version` | VPS commit | confirmed working |
| `!runSCommand logs errors 20` | latest dated pipeline error log | confirmed working |
| `!runSCommand logs all 20` | latest pipeline log tail | confirmed working |
| `!gitpull` | strict fast-forward pull; fails if diverged or dirty | confirmed working in clean states only |
| `!gitpush` | existing commits only; no stage/commit | listed in GitHub integration |
| `!mbdstop`, `!mbdstart` | stop/start existing Chakra | confirmed working |
| `!runpy RudraScanner/scan_now\.py --maintenance` | **new** guarded Git maintenance | committed on GitHub; **NOT VPS/Discord verified** |
| `!runpy RudraScanner/scan_now\.py --git-safe-sync` | isolated research tree | earlier VPS rejected older flag; deployment must be checked |

**Allowlist mechanics:** Existing Discord `!runpy` accepts the specific `RudraScanner/scan_now.py` entry point with known arguments, not arbitrary shell or arbitrary scripts. The new `--maintenance` flag is registered there and imports `Rudra-DDB/asjr_maintenance.py`. Do not invent `!runpy Rudra-DDB/asjr_maintenance.py` as allowed: it is **not** established. `!runSCommand` is a separate hardcoded admin whitelist, not a generic terminal. GitHub Research Bridge accepts explicit research-job types, **not arbitrary VPS shell or maintenance tasks**.

## Maintenance flow and safety
**Single new command** (only after it reaches VPS):
```text
!runpy RudraScanner/scan_now\.py --maintenance
```
- Checks exact worktree, main branch, GitHub origin, active Git transaction and tmux state; uses a nonblocking inter-maintenance lock.
- **Chakra running:** fetch and report state; if only unpublished local commits exist, may push those unchanged; otherwise refuses potentially disruptive repairs and tells the operator to stop Chakra using `!mbdstop`. It does not stage/commit/merge while trading is active.
- **Chakra stopped:** refuses tracked edits outside DataLake; saves original Git HEAD in a dated recovery branch; commits only tracked DataLake changes; merges remote main if cleanly possible, aborts merge conflicts when possible; pushes without force; preserves all untracked files and alert states. Does **not** invoke tmux lifecycle or delete backup branches.
- Refuses conflicts, active Git operations, unexpected remotes, non-DataLake tracked changes, and unsafe live merges. **There is no safe promise that every Git divergence can be fixed without human review**.
- Prevent use of `reset --hard`, `stash pop`, `clean -fd`, blanket `git add .`, forced push, or blind recreation of discarded files. Manual restore of already-existing untracked stash paths needs comparison; never overwrite them automatically.

## Deployment and operational instructions
This page, `Rudra-DDB/asjr_maintenance.py`, and `scan_now.py --maintenance` have been **committed on GitHub only**. The VPS has no automatic self-install route when `!gitpull` is blocked; a Discord command cannot run code not deployed to its old Python entry point. In a clean fast-forward case, run `!gitpull` and verify `!runpy RudraScanner/scan_now\.py --help` only if existing Discord allowlist permits the help argument (not established). Better confirm by the first `--maintenance` output; never assume it works until received. If pull fails due to divergence, an initial SSH/provider-console deployment or other preapproved admin mechanism is required. Future sessions must not promise to execute Discord through GitHub alone.

## Next-session priority
1. Verify a completed Chakra cycle, the post-cycle Git result, and no fresh exception after 16:52 BST.
2. Confirm deployed maintenance CLI with actual Discord output and optionally add narrow offline unit tests; neither live testing nor VPS deployment has been performed by ChatGPT.
3. Build separate Git publisher in a future reviewed change to avoid recurring Git divergence, with bounded log/data retention, tested rollback and no IBKR/Discord order-path modifications.
4. Maintain terse plain-English user communication and report confirmation vs inference accurately.
