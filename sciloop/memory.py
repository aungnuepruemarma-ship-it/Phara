"""Persistent memory with recall — the engine remembers across runs.

Memories are stored in the same SQLite workspace DB and retrieved by TF-IDF
cosine similarity (stdlib only). Every memory carries provenance (source_ref)
and a salience that grows when a memory is recalled/reinforced and decays with
age — so useful memories surface and stale ones fade, without deleting the
audit trail. Agents consult recall() before acting and remember() their
findings after, closing the learning loop across sessions.
"""
from __future__ import annotations

import math
import re
import sqlite3
import time
import uuid
from typing import List

from . import config

_TABLE = """
CREATE TABLE IF NOT EXISTS memory (
  id TEXT PRIMARY KEY, kind TEXT, text TEXT NOT NULL, tags TEXT,
  source_ref TEXT, salience REAL DEFAULT 1.0, uses INTEGER DEFAULT 0,
  created_at REAL, last_used REAL
);
"""

_WORD = re.compile(r"[a-z0-9]{2,}")
_STOP = set("the a an of to in on for and or is are was were be it this that with as by "
            "from at we you they i he she his her its their our not but if then than".split())


def _connect() -> sqlite3.Connection:
    config.ensure_workspace()
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute(_TABLE)
    return con


def _tokens(text: str) -> List[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in _STOP]


def remember(text: str, kind: str = "note", tags: str = "", source_ref: str = "") -> str:
    con = _connect()
    mid = uuid.uuid4().hex[:12]
    now = time.time()
    con.execute("INSERT INTO memory (id, kind, text, tags, source_ref, created_at, last_used)"
                " VALUES (?,?,?,?,?,?,?)",
                (mid, kind, text[:8000], tags, source_ref, now, now))
    con.commit()
    con.close()
    return mid


def _decayed_salience(row, now: float) -> float:
    age_days = (now - (row["created_at"] or now)) / 86400.0
    return row["salience"] * math.exp(-0.03 * age_days)  # ~23-day half-life


def recall(query: str, k: int = 5) -> List[dict]:
    """TF-IDF cosine recall over all memories, tie-broken by decayed salience."""
    con = _connect()
    rows = con.execute("SELECT * FROM memory").fetchall()
    if not rows:
        con.close()
        return []

    docs = [(_tokens(r["text"] + " " + (r["tags"] or ""))) for r in rows]
    N = len(docs)
    df: dict = {}
    for toks in docs:
        for w in set(toks):
            df[w] = df.get(w, 0) + 1
    idf = {w: math.log((N + 1) / (c + 0.5)) for w, c in df.items()}

    def vec(toks):
        tf: dict = {}
        for w in toks:
            tf[w] = tf.get(w, 0) + 1
        return {w: (c / len(toks)) * idf.get(w, 0.0) for w, c in tf.items()} if toks else {}

    qv = vec(_tokens(query))
    qnorm = math.sqrt(sum(v * v for v in qv.values())) or 1.0
    now = time.time()

    scored = []
    for r, toks in zip(rows, docs):
        dv = vec(toks)
        dot = sum(qv.get(w, 0) * dv.get(w, 0) for w in qv)
        dnorm = math.sqrt(sum(v * v for v in dv.values())) or 1.0
        cos = dot / (qnorm * dnorm)
        if cos <= 0:
            continue
        scored.append((cos + 0.05 * _decayed_salience(r, now), cos, r))

    scored.sort(key=lambda t: -t[0])
    out = []
    for _, cos, r in scored[:k]:
        out.append({"id": r["id"], "kind": r["kind"], "text": r["text"],
                    "tags": r["tags"], "source_ref": r["source_ref"],
                    "relevance": round(cos, 3)})
        con.execute("UPDATE memory SET uses=uses+1, salience=salience+0.5, last_used=? WHERE id=?",
                    (now, r["id"]))
    con.commit()
    con.close()
    return out


def summary() -> dict:
    con = _connect()
    n = con.execute("SELECT COUNT(*) c FROM memory").fetchone()["c"]
    kinds = {r["kind"]: r["c"] for r in
             con.execute("SELECT kind, COUNT(*) c FROM memory GROUP BY kind")}
    top = [dict(r) for r in con.execute(
        "SELECT id, kind, substr(text,1,60) text, uses, round(salience,2) salience "
        "FROM memory ORDER BY salience DESC LIMIT 5")]
    con.close()
    return {"total": n, "by_kind": kinds, "top_salient": top}
