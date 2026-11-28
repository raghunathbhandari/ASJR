"""Point-in-time research archive. Runs on Chakra's existing IBKR connection."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import xml.etree.ElementTree as ETXML
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

UTC = timezone.utc
UK = ZoneInfo("Europe/London")
NY = ZoneInfo("America/New_York")
CODES = ("MOST_ACTIVE", "HOT_BY_VOLUME", "TOP_PERC_GAIN", "TOP_PERC_LOSE",
         "HIGH_OPEN_GAP", "LOW_OPEN_GAP", "TOP_OPEN_PERC_GAIN", "TOP_OPEN_PERC_LOSE")
SECTORS = ("XLK", "XLC", "XLY", "XLF", "XLI", "XLV", "XLE", "XLU", "XLP", "XLB", "XLRE", "SPY")
ARCHIVE = Path("Rudra-HotSectorHotStock/data/live_scan_history")
# Published NYSE cash-equity holiday/early-close calendar; fail closed outside coverage.
HOLIDAYS = set(("2026-01-01 2026-01-19 2026-02-16 2026-04-03 2026-05-25 "
                "2026-06-19 2026-07-03 2026-09-07 2026-11-26 2026-12-25 "
                "2027-01-01 2027-01-18 2027-02-15 2027-03-26 2027-05-31 "
                "2027-06-18 2027-07-05 2027-09-06 2027-11-25 2027-12-24").split())
EARLY = {"2026-11-27", "2026-12-24", "2027-11-26"}
SCAN_FIELDS = ("session_date", "interval_end_utc", "interval_end_uk", "scan_code",
               "rank", "ticker", "conid", "exchange", "request_utc", "received_utc",
               "received_uk", "response_state", "after_close")
BAR_FIELDS = ("session_date", "ticker", "bar_start_utc", "bar_end_utc", "bar_end_uk",
              "collected_utc", "collected_uk", "open", "high", "low", "close", "volume",
              "source", "response_state")


def now():
    return datetime.now(UTC)


def stamp(t):
    return t.astimezone(UTC).isoformat()


def uk(t):
    return t.astimezone(UK).isoformat()


def clean(value):
    # Repository may be public: preserve broker error descriptions but redact
    # account identifiers and embedded credentials.
    s = str(value).replace("\n", " ").replace("\r", " ")
    s = re.sub(r"(?i)(https?://)[^/\s@]+@", r"\1[REDACTED]@", s)
    s = re.sub(r"\b(?:DU|U)\d{5,}\b", "[ACCOUNT]", s)
    s = re.sub(r"(?i)\b(token|password|authorization|api[_-]?key)\s*[:=]\s*\S+", r"\1=[REDACTED]", s)
    return s[:1500]


def session_slot(t):
    """Latest completed RTH interval; final candle allowed up to 4:59 after close."""
    et = t.astimezone(NY)
    day = et.date().isoformat()
    if et.year not in (2026, 2027) or et.weekday() >= 5 or day in HOLIDAYS:
        return None
    start = et.replace(hour=9, minute=30, second=0, microsecond=0)
    end = et.replace(hour=13 if day in EARLY else 16, minute=0, second=0, microsecond=0)
    slot = et.replace(minute=(et.minute // 5) * 5, second=0, microsecond=0)
    if not start < slot <= end:
        return None
    return slot, end


def csv_text(fields, rows):
    f = io.StringIO(newline="")
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return f.getvalue()


def synced_write(path, content):
    with path.open("x", encoding="utf-8", newline="") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())


def syncdir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def bundle(spool, relative, files):
    """Immutable, atomic per-interval folder. Retain the local copy after publish."""
    target = spool / "rounds" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return False
    tmp = Path(tempfile.mkdtemp(prefix=".building-", dir=target.parent))
    try:
        for name, content in files.items():
            synced_write(tmp / name, content)
        synced_write(tmp / ".ready", "1\n")
        syncdir(tmp)
        os.rename(tmp, target)
        syncdir(target.parent)
        return True
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


class Capture:
    """Observe only owned requests; unrelated Chakra callbacks remain untouched.

    A single existing EClient is used under the pipeline's process lock.
    Keep retired request IDs to swallow late/cancelled callbacks, not reroute
    them into the old scanner/history dictionaries.
    """
    def __init__(self, app):
        self.app = app
        self.lock = threading.RLock()
        self.active = {}
        self.retired = set()
        self.params = None
        self.param_day = None
        self.param_try = 0.0
        self.param_wait = False
        self.param_event = threading.Event()
        for name in ("scannerData", "scannerDataEnd", "historicalData",
                     "historicalDataEnd", "scannerParameters", "error"):
            old = getattr(app, name, None)
            setattr(app, name, self.wrap(name, old))

    def wrap(self, name, old):
        def callback(*args, **kwargs):
            with self.lock:
                if name == "scannerParameters" and self.param_wait and args:
                    self.params = str(args[0])
                    self.param_event.set()
                    return
                if args and name != "scannerParameters":
                    rid = args[0]
                    req = self.active.get(rid)
                    if rid in self.retired:
                        return
                    if req is not None:
                        try:
                            if name == "error":
                                # Support both older and newer EWrapper.error signatures.
                                offset = 2 if len(args) >= 4 and isinstance(args[2], int) else 1
                                code = int(args[offset])
                                msg = clean(args[offset + 1])
                                req["errors"].append({"code": code, "message": msg, "at_utc": stamp(now())})
                                if code in (200, 321, 354, 420, 10167, 10168):
                                    req["event"].set()
                            elif name in ("scannerDataEnd", "historicalDataEnd"):
                                req["done"] = True
                                req["event"].set()
                            elif not req["done"] and name == "scannerData":
                                c = args[2].contract
                                rank = int(args[1]) + 1
                                if 1 <= rank <= 50:
                                    req["rows"].setdefault(rank, {"rank": rank,
                                        "ticker": str(c.symbol), "conid": getattr(c, "conId", ""),
                                        "exchange": getattr(c, "primaryExchange", "") or getattr(c, "exchange", ""),
                                        "received_utc": stamp(now()), "received_uk": uk(now())})
                            elif not req["done"] and name == "historicalData":
                                bar = args[1]
                                t = datetime.fromtimestamp(int(bar.date), UTC)
                                req["rows"][t] = tuple(float(getattr(bar, k)) for k in
                                                        ("open", "high", "low", "close", "volume"))
                        except Exception as exc:
                            req["errors"].append({"code": "CALLBACK", "message": clean(exc), "at_utc": stamp(now())})
                        return
            if callable(old):
                return old(*args, **kwargs)
        return callback

    def request(self, rid, label):
        req = {"label": label, "rows": {}, "done": False, "errors": [],
               "event": threading.Event(), "started": now()}
        with self.lock:
            self.retired.discard(rid)
            self.active[rid] = req
        return req

    def finish(self, rid):
        with self.lock:
            req = self.active.pop(rid)
            self.retired.add(rid)
            # Bounded memory; existing IBKR allocator is monotonic.
            if len(self.retired) > 10000:
                self.retired = set(sorted(self.retired)[-5000:])
            return req

    def catalogue(self, day, seconds):
        if self.param_day != day:
            self.param_day, self.params, self.param_try = day, None, 0.0
        if self.params is None and seconds > 0 and (not self.param_try or time.monotonic() - self.param_try > 60):
            self.param_try = time.monotonic()
            self.param_event.clear()
            self.param_wait = True
            try:
                self.app.reqScannerParameters()
                self.param_event.wait(seconds)
            finally:
                self.param_wait = False
        if not self.params:
            return None
        root = ETXML.fromstring(self.params)
        codes = {str(n.text).strip() for n in root.iter()
                 if n.tag.rsplit("}", 1)[-1].lower() == "scancode" and n.text}
        return codes or None


def state(req):
    if req["done"]:
        if req["errors"]:
            return "SUCCESS_WITH_WARNINGS" if req["rows"] else "ERROR"
        return "SUCCESS" if req["rows"] else "EMPTY"
    return "ERROR" if req["errors"] else "TIMEOUT"


def collect(app, slot, close, *, budget=48, diagnostic=False):
    from ASJR_Analyst.Utils import asjr_ibkr as ibkr
    from ibapi.scanner import ScannerSubscription
    capture = getattr(app, "_hotsector_archive_capture", None)
    if capture is None:
        capture = Capture(app)
        app._hotsector_archive_capture = capture
    deadline = time.monotonic() + max(0, budget)
    day = slot.date().isoformat()
    base = {"session_date": day, "interval_end_utc": stamp(slot), "interval_end_uk": uk(slot)}
    events, stocks, bars = [], [], []
    def event(kind, **fields):
        events.append({**base, "type": kind, "at_utc": stamp(now()), "at_uk": uk(now()), **fields})
    try:
        codes = capture.catalogue(day, min(3, max(0, deadline - time.monotonic())))
        event("CATALOGUE", status="RECEIVED" if codes else "UNAVAILABLE",
              sha256=hashlib.sha256(capture.params.encode()).hexdigest() if capture.params else None,
              selected_advertised=[c for c in CODES if codes and c in codes])
    except Exception as exc:
        codes = None
        event("CATALOGUE", status="ERROR", error=clean(exc))

    def run_batch(labels, kind):
        active = []
        for label in labels:
            if kind == "SCAN" and codes is not None and label not in codes:
                event(kind, code=label, status="NOT_ADVERTISED", row_count=0)
                continue
            if time.monotonic() >= deadline or (kind == "SCAN" and not diagnostic and now() >= slot.astimezone(UTC) + timedelta(minutes=5)):
                event(kind, **({"code": label} if kind == "SCAN" else {"ticker": label}),
                      status="SKIPPED_BUDGET_OR_LATE", row_count=0)
                continue
            rid = ibkr._next_req_id(app)
            req = capture.request(rid, label)
            active.append((rid, req))
            try:
                if kind == "SCAN":
                    sub = ScannerSubscription()
                    sub.instrument, sub.locationCode, sub.stockTypeFilter = "STK", "STK.US.MAJOR", "CORP"
                    sub.scanCode, sub.numberOfRows = label, 50
                    # No hidden fundamental or price constraints; archive raw native ranks.
                    app.reqScannerSubscription(rid, sub, [], [])
                else:
                    app.reqHistoricalData(rid, ibkr.stock_contract(label),
                                          slot.astimezone(UTC).strftime("%Y%m%d-%H:%M:%S") if diagnostic else "", "1 D", "5 mins",
                                          "TRADES", 1, 2, False, [])
            except Exception as exc:
                req["errors"].append({"code": "REQUEST", "message": clean(exc), "at_utc": stamp(now())})
                req["event"].set()
        batch_end = min(deadline, time.monotonic() + (5 if kind == "SCAN" else 7))
        for _, req in active:
            req["event"].wait(max(0, batch_end - time.monotonic()))
        for rid, req in active:
            # Remove ownership atomically before cancel; late callbacks are ignored.
            req = capture.finish(rid)
            finished = now()
            try:
                if kind == "SCAN":
                    app.cancelScannerSubscription(rid)
                elif not req["done"]:
                    app.cancelHistoricalData(rid)
            except Exception as exc:
                req["errors"].append({"code": "CANCEL", "message": clean(exc), "at_utc": stamp(now())})
            label, status = req["label"], state(req)
            request = stamp(req["started"])
            if kind == "SCAN":
                for rank, row in sorted(req["rows"].items()):
                    stocks.append({**base, **row, "scan_code": label, "request_utc": request,
                                   "response_state": status,
                                   "after_close": datetime.fromisoformat(row["received_utc"]) >= close})
                event(kind, code=label, req_id=rid, status=status, request_utc=request,
                      finished_utc=stamp(finished), row_count=len(req["rows"]), errors=req["errors"],
                      instrument="STK", location="STK.US.MAJOR", stock_type="CORP", filters=[])
            else:
                target = slot.astimezone(UTC) - timedelta(minutes=5)
                values = req["rows"].get(target)
                valid = (values is not None and all(math.isfinite(v) and abs(v) < 1e20 for v in values)
                         and min(values[:4]) > 0 and values[4] >= 0 and
                         values[1] >= max(values[0], values[3], values[2]) and
                         values[2] <= min(values[0], values[3], values[1]))
                if valid:
                    bars.append({"session_date": day, "ticker": label, "bar_start_utc": stamp(target),
                                 "bar_end_utc": stamp(slot), "bar_end_uk": uk(slot),
                                 "collected_utc": stamp(finished), "collected_uk": uk(finished),
                                 **dict(zip(("open","high","low","close","volume"), values)),
                                 "source": "IBKR_TRADES_RTH", "response_state": status})
                event(kind, ticker=label, req_id=rid, status=status if valid else "MISSING_TARGET_BAR",
                      broker_state=status, request_utc=request, finished_utc=stamp(finished),
                      expected_start_utc=stamp(target), row_count=len(req["rows"]), errors=req["errors"],
                      latest_bar_utc=stamp(max(req["rows"])) if req["rows"] else None)
    for offset in range(0, len(CODES), 3):
        run_batch(CODES[offset:offset + 3], "SCAN")
    for offset in range(0, len(SECTORS), 4):
        run_batch(SECTORS[offset:offset + 4], "SECTOR")
    errors = [e for e in events if e["status"] not in ("SUCCESS", "RECEIVED") or e.get("errors")]
    files = {"ibkr_scan_results.csv": csv_text(SCAN_FIELDS, stocks),
             "sector_5m.csv": csv_text(BAR_FIELDS, bars),
             "scan_rounds.jsonl": "".join(json.dumps(e, default=str) + "\n" for e in events),
             "errors.log": "".join(e["at_uk"] + " | " + json.dumps(e, default=str) + "\n" for e in errors)}
    # Save exact XML once per session (first available interval), not on every round.
    if capture.params and getattr(capture, "saved_catalogue_day", None) != day:
        files["scanner_parameters.xml"] = capture.params
    return files, len(stocks), len(bars), len(errors)


def git(cwd, *args, env=None, timeout=12):
    try:
        r = subprocess.run(["git", *map(str, args)], cwd=cwd, capture_output=True,
                           text=True, timeout=max(1, timeout), env={**os.environ,
                           "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C", **(env or {})})
    except subprocess.TimeoutExpired:
        raise RuntimeError("Git " + str(args[0]) + " timed out") from None
    if r.returncode:
        # Do not expose raw remote URL, credentials, or argv in a public log.
        msg = r.stderr.lower()
        reason = ("authentication/permission" if any(x in msg for x in ("authentication", "permission denied", "username"))
                  else "remote policy" if any(x in msg for x in ("protected branch", "hook declined", "repository rule"))
                  else "non-fast-forward" if any(x in msg for x in ("non-fast-forward", "fetch first", "cannot lock ref"))
                  else "connection" if any(x in msg for x in ("resolve host", "connection", "timed out"))
                  else "unclassified")
        raise RuntimeError(f"Git {args[0]} failed: exit={r.returncode}, reason={reason}")
    return r.stdout.strip()


def publish(repo, spool, *, budget=30, priority=None):
    """Fast-forward only, isolated bare Git index, immutable paths, retry pending."""
    queue = spool / "rounds"
    pending = sorted(p.parent for p in queue.rglob(".ready") if not (p.parent / ".published").exists())
    if priority is not None and queue / priority in pending:
        pending.remove(queue / priority)
        pending.insert(0, queue / priority)
    pending = pending[:12]
    if not pending:
        return "NO_PENDING"
    end = time.monotonic() + budget
    bare = spool / "publisher.git"
    bare.mkdir(parents=True, exist_ok=True)
    def g(*args, env=None):
        remaining = end - time.monotonic()
        if remaining < 1:
            raise RuntimeError("Git publication time budget exhausted")
        return git(bare, *args, env=env, timeout=min(12, remaining))
    if not (bare / "HEAD").exists():
        g("init", "--bare")
    url = git(repo, "remote", "get-url", "origin", timeout=3)
    g("config", "remote.origin.url", url)
    g("config", "remote.origin.promisor", "true")
    g("config", "remote.origin.partialclonefilter", "blob:none")
    g("fetch", "--no-tags", "--depth=1", "--filter=blob:none", "origin", "refs/heads/main")
    parent = g("rev-parse", "FETCH_HEAD")
    with tempfile.TemporaryDirectory(prefix="index-", dir=spool) as td:
        env = {"GIT_INDEX_FILE": str(Path(td) / "index")}
        g("read-tree", parent, env=env)
        # Never replace an ancestor file/symlink or an existing research file.
        for ancestor in reversed(ARCHIVE.parents):
            if str(ancestor) == ".":
                continue
            existing = g("ls-tree", parent, "--", str(ancestor))
            if existing and not existing.startswith("040000 tree "):
                raise RuntimeError("Archive ancestor is not a directory")
        existing = g("ls-tree", parent, "--", str(ARCHIVE))
        if existing and not existing.startswith("040000 tree "):
            raise RuntimeError("Archive root is not a directory")
        for directory in pending:
            rel = ARCHIVE / directory.relative_to(queue)
            listing = g("ls-tree", "-r", parent, "--", str(rel))
            known = {line.split("\t", 1)[1]: line.split("\t", 1)[0].split()[2]
                     for line in listing.splitlines() if "\t" in line}
            for f in sorted(directory.iterdir()):
                if f.name.startswith("."):
                    continue
                if not f.is_file() or f.is_symlink():
                    raise RuntimeError("Unexpected archive entry")
                dest = str(rel / f.name)
                sha = g("hash-object", "-w", str(f))
                if dest in known:
                    if known[dest] != sha:
                        raise RuntimeError("Immutable archive conflict: " + dest)
                    continue
                g("update-index", "--add", "--cacheinfo", "100644," + sha + "," + dest, env=env)
        tree = g("write-tree", "--missing-ok", env=env)
        if tree != g("rev-parse", parent + "^{tree}"):
            commit = g("-c", "user.name=ASJR Research Publisher", "-c",
                       "user.email=asjr-research@localhost", "commit-tree", tree, "-p", parent,
                       "-m", "Archive IBKR HotSectorHotStock research " + uk(now()))
            g("push", "origin", commit + ":refs/heads/main")
        else:
            commit = parent
    for d in pending:
        if not (d / ".published").exists():
            synced_write(d / ".published", commit + "\n")
    return "PUSHED " + commit + " bundles=" + str(len(pending))


def run(app, cycle_started, repo_root):
    """Called once per existing DDB cycle, after DDB signal computation."""
    repo = Path(repo_root).resolve()
    spool = repo.parent / "ASJR_research_logs" / "hot_sector" / "live_scan_history"
    spool.mkdir(parents=True, exist_ok=True)
    planned = session_slot(cycle_started)
    rel = None
    if planned:
        slot, close = planned
        rel = Path(slot.date().isoformat()) / slot.strftime("%H%M_ET")
        if not (spool / "rounds" / rel).exists():
            try:
                remaining = (slot.astimezone(UTC) + timedelta(minutes=5) - now()).total_seconds()
                # Prefer point-in-time scans; preserve an explicit missed-round record.
                files, n, b, e = collect(app, slot, close, budget=min(48, max(0, remaining - 12)))
                if bundle(spool, rel, files):
                    if "scanner_parameters.xml" in files:
                        app._hotsector_archive_capture.saved_catalogue_day = slot.date().isoformat()
                    print(f"HOTSECTOR ARCHIVE | {uk(now())} | {rel} | scans={n} | sector_bars={b} | issues={e}", flush=True)
            except Exception as exc:
                message = clean(f"{type(exc).__name__}: {exc}")
                err = {"status":"COLLECTOR_ERROR","at_uk":uk(now()),"interval_end_utc":stamp(slot),"error":message}
                bundle(spool, rel, {"ibkr_scan_results.csv":csv_text(SCAN_FIELDS, []),
                    "sector_5m.csv":csv_text(BAR_FIELDS, []), "scan_rounds.jsonl":json.dumps(err)+"\n",
                    "errors.log":json.dumps(err)+"\n"})
                print("HOTSECTOR ARCHIVE | COLLECTOR_ERROR | " + message, flush=True)
    # Attempt publication in this cycle even if collection was partial or failed.
    # Outside RTH, retry any existing backlog; no new broker calls.
    try:
        status = publish(repo, spool, priority=rel)
        if status != "NO_PENDING":
            print("HOTSECTOR ARCHIVE | " + uk(now()) + " | " + status, flush=True)
        return status
    except Exception as exc:
        msg = clean(f"{type(exc).__name__}: {exc}")
        t = now()
        err = {"status":"PUBLISH_PENDING","at_uk":uk(t),"at_utc":stamp(t),"error":msg}
        bundle(spool, Path(t.astimezone(NY).date().isoformat()) / "publish_errors" / uuid.uuid4().hex,
               {"errors.log":json.dumps(err)+"\n"})
        print("HOTSECTOR ARCHIVE | PUBLISH_PENDING | " + msg, flush=True)
        return "PUBLISH_PENDING"


def diagnostic_probe(app, repo_root):
    """One real collector pass; out-of-session snapshots are NEVER research rounds."""
    repo = Path(repo_root).resolve()
    spool = repo.parent / "ASJR_research_logs" / "hot_sector" / "live_scan_history"
    t = now()
    planned = session_slot(t)
    if planned is None:
        et = t.astimezone(NY)
        for offset in range(8):
            day = et - timedelta(days=offset)
            date = day.date().isoformat()
            if day.year not in (2026, 2027) or day.weekday() >= 5 or date in HOLIDAYS:
                continue
            close = day.replace(hour=13 if date in EARLY else 16, minute=0, second=0, microsecond=0)
            if close <= et:
                planned = (close, close)
                break
    if planned is None:
        raise RuntimeError("No completed session in supported calendar")
    slot, close = planned
    rel = Path("diagnostics") / (t.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    meta = {"kind": "MANUAL_DIAGNOSTIC_NOT_RESEARCH", "scan_time_utc": stamp(t),
            "scan_time_uk": uk(t), "sector_historical_target_end_utc": stamp(slot),
            "warning": "Live scanner response at actual request time; may be empty/stale outside RTH. Sector bars may be historical. Never use this bundle in point-in-time backtests."}
    try:
        files, n, b, e = collect(app, slot, close, diagnostic=True)
    except Exception as exc:
        err = {**meta, "status": "COLLECTOR_ERROR", "error": clean(f"{type(exc).__name__}: {exc}")}
        files = {"errors.log": json.dumps(err)+"\n", "scan_rounds.jsonl": json.dumps(err)+"\n",
                 "ibkr_scan_results.csv": csv_text(SCAN_FIELDS, []), "sector_5m.csv": csv_text(BAR_FIELDS, [])}
        n, b, e = 0, 0, 1
    files["diagnostic.json"] = json.dumps(meta, indent=2)+"\n"
    bundle(spool, rel, files)
    for line in files["scan_rounds.jsonl"].splitlines():
        record = json.loads(line)
        if record.get("type") == "SCAN":
            print("HOTSECTOR PROBE |", record.get("code"), record.get("status"), "rows=", record.get("row_count"), flush=True)
    print(f"HOTSECTOR PROBE | DIAGNOSTIC ONLY | scan_rows={n} | sector_bars={b}/12 | issues={e}", flush=True)
    print("HOTSECTOR PROBE | ARCHIVE |", ARCHIVE / rel, flush=True)
    try:
        status = publish(repo, spool, priority=rel)
    except Exception as exc:
        msg = clean(f"{type(exc).__name__}: {exc}")
        bundle(spool, Path("diagnostics") / ("publish_error_" + uuid.uuid4().hex),
               {"errors.log": json.dumps({**meta, "status":"PUBLISH_PENDING","error":msg})+"\n"})
        print("HOTSECTOR PROBE | PUBLISH_PENDING |", msg, flush=True)
        return 2
    print("HOTSECTOR PROBE |", status, flush=True)
    return 0 if b == 12 and n > 0 and not e else 2
