"""Evidence Store — SQLite, provenance-tiered. The no-hallucination mechanism.

Evidence kinds (tiered):
  executed_result   — output of code that actually ran in the sandbox (top tier)
  retrieved_source  — external source content (papers, docs)
  agent_claim       — something an agent said (NEVER sufficient for promotion)

Hypothesis statuses: candidate -> supported/falsified/undecided (loop verdicts)
                     -> accepted/rejected (human review).
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid

from . import config

PROMOTABLE_KINDS = ("executed_result", "retrieved_source")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, question TEXT NOT NULL, status TEXT DEFAULT 'running',
  compiled TEXT, report_path TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS hypotheses (
  id TEXT PRIMARY KEY, run_id TEXT, text TEXT NOT NULL,
  status TEXT DEFAULT 'candidate', cycle INTEGER DEFAULT 0, reason TEXT,
  created_at REAL
);
CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY, run_id TEXT, hypothesis_id TEXT,
  kind TEXT NOT NULL, content TEXT NOT NULL, source_ref TEXT,
  geometry TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS operators (
  id TEXT PRIMARY KEY, name TEXT UNIQUE, domain TEXT, sequence TEXT,
  status TEXT DEFAULT 'certified', uses INTEGER DEFAULT 0,
  wins INTEGER DEFAULT 0, cost REAL DEFAULT 0.0, fitness REAL DEFAULT 0.0,
  evidence_id TEXT, created_at REAL
);
"""


def _connect() -> sqlite3.Connection:
    config.ensure_workspace()
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(_SCHEMA)
    return con


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class Store:
    def __init__(self):
        self.con = _connect()

    # ── runs ──────────────────────────────────────────────────────────────
    def create_run(self, question: str, compiled: dict | None = None) -> str:
        rid = _new_id()
        self.con.execute(
            "INSERT INTO runs (id, question, compiled, created_at) VALUES (?,?,?,?)",
            (rid, question, json.dumps(compiled or {}), time.time()),
        )
        self.con.commit()
        return rid

    def finish_run(self, run_id: str, status: str = "done", report_path: str | None = None):
        self.con.execute("UPDATE runs SET status=?, report_path=? WHERE id=?",
                         (status, report_path, run_id))
        self.con.commit()

    def get_run(self, run_id: str) -> dict | None:
        row = self.con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def latest_run(self) -> dict | None:
        row = self.con.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    # ── hypotheses ────────────────────────────────────────────────────────
    def add_hypothesis(self, run_id: str, text: str, cycle: int = 0) -> str:
        hid = _new_id()
        self.con.execute(
            "INSERT INTO hypotheses (id, run_id, text, cycle, created_at) VALUES (?,?,?,?,?)",
            (hid, run_id, text, cycle, time.time()),
        )
        self.con.commit()
        return hid

    def set_hypothesis_status(self, hyp_id: str, status: str, reason: str = ""):
        self.con.execute("UPDATE hypotheses SET status=?, reason=? WHERE id=?",
                         (status, reason, hyp_id))
        self.con.commit()

    def hypotheses(self, run_id: str | None = None, status: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM hypotheses WHERE 1=1", []
        if run_id:
            q += " AND run_id=?"; args.append(run_id)
        if status:
            q += " AND status=?"; args.append(status)
        return [dict(r) for r in self.con.execute(q + " ORDER BY created_at", args)]

    # ── evidence ──────────────────────────────────────────────────────────
    def add_evidence(self, run_id: str, kind: str, content: str,
                     source_ref: str = "", hypothesis_id: str | None = None,
                     geometry: dict | None = None) -> str:
        eid = _new_id()
        self.con.execute(
            "INSERT INTO evidence (id, run_id, hypothesis_id, kind, content, source_ref, geometry, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (eid, run_id, hypothesis_id, kind, content[:20000], source_ref,
             json.dumps(geometry) if geometry else None, time.time()),
        )
        self.con.commit()
        return eid

    def evidence(self, run_id: str | None = None, hypothesis_id: str | None = None,
                 promotable_only: bool = False) -> list[dict]:
        q, args = "SELECT * FROM evidence WHERE 1=1", []
        if run_id:
            q += " AND run_id=?"; args.append(run_id)
        if hypothesis_id:
            q += " AND hypothesis_id=?"; args.append(hypothesis_id)
        if promotable_only:
            q += " AND kind IN (?,?)"; args.extend(PROMOTABLE_KINDS)
        return [dict(r) for r in self.con.execute(q + " ORDER BY created_at", args)]

    def get_evidence(self, eid: str) -> dict | None:
        row = self.con.execute("SELECT * FROM evidence WHERE id=?", (eid,)).fetchone()
        return dict(row) if row else None

    # ── operators (ecology ledger) ────────────────────────────────────────
    def add_operator(self, name: str, domain: str, sequence: list[str],
                     evidence_id: str | None = None) -> str:
        oid = _new_id()
        self.con.execute(
            "INSERT OR IGNORE INTO operators (id, name, domain, sequence, evidence_id, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (oid, name, domain, json.dumps(sequence), evidence_id, time.time()),
        )
        self.con.commit()
        return oid

    def record_operator_use(self, name: str, win: bool, cost: float = 0.0):
        self.con.execute(
            "UPDATE operators SET uses=uses+1, wins=wins+?, cost=cost+? WHERE name=?",
            (1 if win else 0, cost, name),
        )
        self.con.execute(
            "UPDATE operators SET fitness = CASE WHEN uses>0 THEN (CAST(wins AS REAL)/uses) - (cost/(uses*100.0)) ELSE 0 END WHERE name=?",
            (name,),
        )
        self.con.commit()

    def retire_weak_operators(self, min_uses: int = 5, min_fitness: float = 0.3) -> list[str]:
        rows = self.con.execute(
            "SELECT name FROM operators WHERE status='certified' AND uses>=? AND fitness<?",
            (min_uses, min_fitness),
        ).fetchall()
        names = [r["name"] for r in rows]
        for n in names:
            self.con.execute("UPDATE operators SET status='retired' WHERE name=?", (n,))
        self.con.commit()
        return names

    def operators(self, status: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM operators", []
        if status:
            q += " WHERE status=?"; args.append(status)
        return [dict(r) for r in self.con.execute(q + " ORDER BY fitness DESC", args)]

    def close(self):
        self.con.close()
