# Rudra-Downloader & Rudra-Coder — VPS, IBKR, Bridge and Git Handoff

Updated: 2026-11-03 (UK time). Repository target: `three_candle/RUDRA_DOWNLOADER_GUIDE.md`.

## 1. Known environment

| Component | Known setting |
|---|---|
| VPS | IONOS AlmaLinux, host prompt `nostalgic-mirzakhani` |
| Repository | `/root/trading/ASJR`, branch `main` |
| IBKR Python | `/root/trading/venv_new/bin/python` |
| IBKR Gateway | `127.0.0.1:4002` (paper account, verified listening 2026-11-03) |
| Research bridge systemd unit | `asjr-research-bridge.service` (verified active 2026-11-03) |
| Bridge documentation | `three_candle/BRIDGE_GUIDE.md` |
| Existing range downloader | `three_candle/ibkr_bridge_range_download.py` |
| MES monthly downloader | `three_candle/download_mes_ibkr_months.py` (appeared in Git update 2026-11-03) |

Do not assume this document establishes the bridge's HTTP route, authorization, or connectivity from ChatGPT. Inspect the implementation and `BRIDGE_GUIDE.md` before calling it remotely. Never expose an unauthenticated research bridge to the internet.

## 2. Immediate MES download

The script's confirmed `--help` options are `--host`, `--port`, `--client-id`, and `--pause`. It does **not** accept date, month, contract, or timeframe flags; inspect its code to confirm the configured months/contract before running.

```bash
cd /root/trading/ASJR
sed -n '1,240p' three_candle/download_mes_ibkr_months.py
/root/trading/venv_new/bin/python three_candle/download_mes_ibkr_months.py --help
/root/trading/venv_new/bin/python three_candle/download_mes_ibkr_months.py --host 127.0.0.1 --port 4002 --client-id 89
find three_candle/data -type f -iname '*MES*' -print
```

Target for this research run: `MESZ2026`, September and October 2026, 5-minute OHLCV, include overnight and regular trading hours, with separate monthly files. **Target is not proof of what the current script actually downloads.** Verify contract, date coverage, timezone, `useRTH`, bar count and gaps from the output.

Do not touch previously downloaded NQZ2026 and GCZ2026 September/October CSVs. Use new MES filenames. Record the source, instrument contract ID, exchange, bar size, timezone, earliest/latest timestamp and count in a manifest or coverage report.

## 3. Healthy VPS checks

```bash
cd /root/trading/ASJR
/root/trading/venv_new/bin/python -c "import ib_insync; print('IBKR Python OK')"
ss -ltnp | grep 4002
sudo systemctl is-active asjr-research-bridge.service
sudo systemctl status asjr-research-bridge.service --no-pager
sudo journalctl -u asjr-research-bridge.service -n 50 --no-pager
```

On 2026-11-03, `ib_insync` imported, Java listened on port 4002, and the bridge returned `active` after restart. This does not by itself confirm a historical-data request succeeded.

Restart only when appropriate, and recheck logs:

```bash
sudo systemctl restart asjr-research-bridge.service
sudo systemctl is-active asjr-research-bridge.service
sudo journalctl -u asjr-research-bridge.service -n 30 --no-pager
```

## 4. Git fast-forward failure — actual incident and recovery

On 2026-11-03, `git fetch origin` succeeded but `git merge --ff-only origin/main` was blocked by untracked DataLake paths for `2026-11-02`, then `2026-11-03`. A tracked October 30 log was also modified. Git protected these files from overwrite. Do not use `git reset --hard`, broad `git clean -fd`, force pull, or blindly delete DataLake.

Inspect first:

```bash
cd /root/trading/ASJR
git status --short --untracked-files=no
git ls-files ASJR_Analyst/DataLake/2026-11-03 | head -20
git fetch origin
```

Actual safe recovery used (the 2026-11-02 and 2026-11-03 folders were confirmed untracked before moving):

```bash
mkdir -p /root/trading/DataLake_Backups
mv ASJR_Analyst/DataLake/2026-11-02 /root/trading/DataLake_Backups/2026-11-02
git stash push -m "VPS log backup 2026-11-03" -- ASJR_Analyst/DataLake/2026-10-30/reports/asjr_pipeline_20261030_214616_GMT.log
mv ASJR_Analyst/DataLake/2026-11-03 /root/trading/DataLake_Backups/2026-11-03
git merge --ff-only origin/main
```

The user subsequently reported many `create mode` lines from the merge, including the MES downloader, and the bridge restarted as `active`. The copied-off daily data remain outside Git; the changed log remains in the stash. **Do not automatically `stash pop` or move backup files on top of tracked Git files.** Review diffs and selectively recover data if needed.

Validation:

```bash
git status --short --untracked-files=no
git log -1 --oneline
git stash list -n 3
du -sh /root/trading/DataLake_Backups/2026-11-02 /root/trading/DataLake_Backups/2026-11-03
```

### Prevent repeat conflicts

- The live scanner generates daily DataLake files while the Git repository also tracks files at the same paths. This is the underlying design conflict.
- Coder task: propose a separate runtime data directory outside the tracked worktree, or a versioned-data sync process that does not collide with local outputs. Do **not** simply add `.gitignore`: ignored files already tracked remain tracked.
- If a live scanner recreates an untracked date folder during a merge, coordinate a brief pause of the responsible writer rather than racing it; first identify the process/service and assess impact on live alerts.
- Use `git fetch origin` then `git merge --ff-only origin/main`, and investigate failures. No interactive merge editor, force push, or destructive reset.

## 5. Rudra-Coder download implementation standards

1. Use `ib_insync` from the configured virtualenv, `127.0.0.1:4002`, an unused client ID and dated contract (avoid ambiguous continuous futures).
2. Qualify the IBKR contract and capture `conId`, exchange, currency, contract month, and trading class. Confirm actual CME MES contract definition from IBKR before download.
3. Request 5-minute OHLCV in IBKR-compliant batches. Respect historical request pacing, retry transient errors with bounded backoff, and log each batch's start/end and errors. Avoid duplicated bars at chunk boundaries.
4. For extended coverage, explicitly set `useRTH=False`; do not infer it from the label 'extended'. Preserve source timezone and consistently normalize timestamps to UTC, reporting UK-local time in summaries.
5. Sort by timestamp, deduplicate, validate OHLC (`low <= open/close <= high`), volume nonnegative, and flag session gaps. Do not fill real market closures with fabricated bars.
6. Keep source 5-minute data immutable. Resample copies to 15m/30m/1H/4H with explicit candle boundary and exchange session rules. Avoid look-ahead and partially closed candles.
7. Write output atomically (temp file then rename), not directly over canonical CSV. Never overwrite NQ/GC historical files. Add checksums and a per-month coverage report.
8. Keep code readable, document major functions, provide `--help`, and ideally offer flags for symbol, contract month, start/end, output, RTH mode, and dry run; retain backwards-compatible defaults.
9. Treat an IBKR socket listener, running service, and completed historical data download as **three separate checks**.

## 6. Bridge remote execution and access

Known: `asjr-research-bridge.service` exists and is active. Not yet verified here: listener address, HTTP endpoints, authentication, external reachability, or whether this ChatGPT execution environment has a path to the VPS. To make assistant-driven downloads possible, review:

```bash
cd /root/trading/ASJR
sed -n '1,240p' three_candle/BRIDGE_GUIDE.md
systemctl cat asjr-research-bridge.service
ss -ltnp
rg -n 'route|token|auth|listen|bind|host|port|download|IBKR' RudraScanner/ResearchBridge three_candle/BRIDGE_GUIDE.md
```

Redact API tokens, credentials and private addresses before sharing outputs. Prefer a private authenticated route or SSH tunnel. Do not bind the bridge publicly merely for convenience. Once the interface is verified, document actual request and response formats and test a small read-only historical request before a large download.

## 7. Data QA and three-candle handoff

After download, for each month print: rows, first bar, last bar, timezone, 5-minute duplicates, missing expected session slots, zero/invalid OHLC values, and estimated RTH vs overnight bars. Check contract rollover and exchange holidays before interpreting gaps.

Use the same Three-Candle strategy code and settings across NQ and MES for a fair comparison; do not silently substitute a newer experimental strategy. Report qualifying signals, wins, stop-outs, target hits at 1R/2R/3R, points gained/lost, maximum adverse excursion, maximum drawdown, gross/net result, commissions, and the exact strategy version. For MES, point value is $5 per index point per micro contract (confirm current IBKR contract specification before financial use).

## 8. Next actions checklist

- [x] Recover Git fast-forward merge without discarding local runtime data.
- [x] Verify IBKR Python and port 4002.
- [x] Restart research bridge; service active.
- [x] Confirm MES downloader script exists and its available CLI flags.
- [ ] Inspect script to verify actual contract, period, timezone and `useRTH`.
- [ ] Execute MES monthly download and collect logs.
- [ ] Verify September and October coverage, then publish a manifest.
- [ ] Test authenticated private bridge route from assistant-accessible environment.
- [ ] Implement durable separation between scanner runtime data and Git-tracked DataLake.

## 9. One-line operational rule

**Protect local data → fast-forward Git only → verify Gateway and bridge → inspect download settings → download in batches → validate candles → backtest with a frozen strategy version.**

## 10. Verified assistant-to-VPS bridge (2026-11-03)

The GitHub queue was actually verified from this ChatGPT session, without SSH: created `RudraScanner/ResearchBridge/requests/research-1793722403289.json` with the allowlisted `three_candle_ibkr_one_candle` operation. VPS published `RudraScanner/ResearchBridge/results/research-1793722403289.json` with `status=SUCCESS`, `exit_code=0`, and an MSFT 5m historical candle on 2026-10-30 at 18:55 UTC (open 518.58, high 519.81, low 518.58, close 519.63, volume 124625). This verifies ChatGPT → GitHub → VPS → IBKR → GitHub for approved operations. It **does not** prove futures download operation is currently allowlisted.

## 11. One-year MES/MNQ historical request (pending bridge extension)

User reports MES and MNQ September/October 2026 5m data downloaded on VPS; the data's completeness has **not** yet been independently audited. Proposed one-year window is 2025-11-01 through 2026-10-31 (12 calendar months) and existing Sep/Oct files must not be overwritten. One must use the appropriate quarterly futures contract for each historical period with an explicit rollover policy, not December 2026 for all dates. Preserve raw contract identifiers, roll mapping and gap reports; do not fabricate continuous bars or mix contracts without labels. Existing stock-only `ibkr_range_download` must never be used for futures. Implement a separate reviewed, allowlisted, read-only futures operation and deploy worker code on VPS before queuing work. Break the request into bounded monthly jobs, report individual results, and limit pacing and Git output size. No futures year download was initiated by this document update.
