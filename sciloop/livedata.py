"""Live data — real-time series piped into the evidence-tiered machinery.

Four free, no-auth sources (stdlib urllib only):
  weather   — Open-Meteo daily max temperature (30 days)
  quakes    — USGS all-week earthquakes -> daily counts + magnitudes
  fx        — Frankfurter USD/EUR daily rate (30 days)
  wiki      — Wikipedia pageviews for 'Artificial_intelligence' (30 days)

Every fetch is stored as retrieved_source evidence WITH its URL + timestamp
(provenance) — real-time data enters at the promotable tier, agent talk never
does. The cross-domain analysis then treats each real series as a domain:
compute the SAME observable vector on all of them (trend, volatility, lag-1
memory, coarse-grain stability R, tail weight), report which invariants are
shared, which pairs co-move (rank correlation, honestly labeled correlation
not causation), and whether yesterday predicts today better than chance
(persistence test on a held-out half).

Offline honesty: if a source cannot be fetched, it is reported as UNAVAILABLE —
never simulated silently.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import time
import urllib.request
from typing import Dict, List, Optional, Tuple

from . import invariants

_UA = {"User-Agent": "SciLoop/0.1 (research runtime; stdlib urllib)"}


def _get_json(url: str, timeout: float = 20) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _dates(days: int = 30) -> Tuple[str, str]:
    end = _dt.date.today()
    start = end - _dt.timedelta(days=days)
    return start.isoformat(), end.isoformat()


# ── sources ───────────────────────────────────────────────────────────────────
def fetch_weather() -> Optional[dict]:
    s, e = _dates(30)
    url = ("https://api.open-meteo.com/v1/forecast?latitude=23.81&longitude=90.41"
           f"&daily=temperature_2m_max&start_date={s}&end_date={e}&timezone=UTC")
    d = _get_json(url)
    if not d:
        return None
    vals = [v for v in (d.get("daily", {}).get("temperature_2m_max") or []) if v is not None]
    return {"name": "weather_tmax_dhaka", "unit": "degC", "series": vals, "url": url}


def fetch_quakes() -> Optional[dict]:
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson"
    d = _get_json(url)
    if not d:
        return None
    feats = d.get("features") or []
    mags = [f["properties"]["mag"] for f in feats
            if f.get("properties", {}).get("mag") is not None]
    # daily counts (aligned series)
    counts: Dict[str, int] = {}
    for f in feats:
        t = f.get("properties", {}).get("time")
        if t:
            day = _dt.datetime.utcfromtimestamp(t / 1000).date().isoformat()
            counts[day] = counts.get(day, 0) + 1
    daily = [counts[k] for k in sorted(counts)]
    return {"name": "quakes_daily_count", "unit": "events/day", "series": daily,
            "magnitudes": mags[:2000], "url": url}


def fetch_fx() -> Optional[dict]:
    s, e = _dates(30)
    url = f"https://api.frankfurter.app/{s}..{e}?from=USD&to=EUR"
    d = _get_json(url)
    if not d:
        return None
    rates = d.get("rates") or {}
    vals = [rates[k]["EUR"] for k in sorted(rates) if "EUR" in rates[k]]
    return {"name": "fx_usd_eur", "unit": "EUR per USD", "series": vals, "url": url}


def fetch_wiki() -> Optional[dict]:
    s, e = _dates(30)
    s2, e2 = s.replace("-", ""), e.replace("-", "")
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"en.wikipedia/all-access/all-agents/Artificial_intelligence/daily/{s2}/{e2}")
    d = _get_json(url)
    if not d:
        return None
    vals = [it["views"] for it in (d.get("items") or [])]
    return {"name": "wiki_views_AI", "unit": "views/day", "series": vals, "url": url}


SOURCES = {"weather": fetch_weather, "quakes": fetch_quakes,
           "fx": fetch_fx, "wiki": fetch_wiki}


# ── the same observable vector for EVERY real domain ─────────────────────────
def series_observables(vals: List[float]) -> Optional[dict]:
    n = len(vals)
    if n < 8:
        return None
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / n
    std = math.sqrt(var)
    trend = invariants.spearman(list(range(n)), vals)
    # lag-1 memory (rank-based, robust)
    lag1 = invariants.spearman(vals[:-1], vals[1:])
    r_stab = invariants.coarse_grain_R(vals)
    tail = (max(vals) - min(vals)) / (std + 1e-9)
    return {"n": n, "mean": round(mean, 4), "volatility": round(std / (abs(mean) + 1e-9), 4),
            "trend": round(trend, 3), "lag1_memory": round(lag1, 3),
            "coarse_stability_R": round(r_stab, 3), "tail_span": round(tail, 2)}


def _persistence_test(vals: List[float]) -> Optional[dict]:
    """Does yesterday's DIRECTION predict today's, out of sample?
    Fit nothing; just measure sign-persistence hit-rate on the held-out half
    vs the 50% chance baseline."""
    diffs = [b - a for a, b in zip(vals, vals[1:]) if b != a]
    if len(diffs) < 10:
        return None
    half = len(diffs) // 2
    test = diffs[half:]
    hits = sum(1 for a, b in zip(test, test[1:]) if (a > 0) == (b > 0))
    trials = max(1, len(test) - 1)
    return {"hit_rate": round(hits / trials, 3), "trials": trials, "chance": 0.5}


# ── the pipeline ──────────────────────────────────────────────────────────────
def run_live(store=None) -> dict:
    fetched: Dict[str, dict] = {}
    unavailable: List[str] = []
    evidence_ids: Dict[str, str] = {}

    for key, fn in SOURCES.items():
        d = fn()
        if d and d.get("series"):
            fetched[key] = d
            if store is not None:
                eid = store.add_evidence(
                    run_id=getattr(store, "_live_run_id", ""),
                    kind="retrieved_source",
                    content=json.dumps({"name": d["name"], "n": len(d["series"]),
                                        "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                        "head": d["series"][:5]}),
                    source_ref=d["url"][:300],
                )
                evidence_ids[key] = eid
        else:
            unavailable.append(key)

    # per-domain observables + predictability
    table = {}
    for key, d in fetched.items():
        obs = series_observables(d["series"])
        pred = _persistence_test(d["series"])
        table[key] = {"name": d["name"], "observables": obs, "persistence": pred,
                      "evidence": evidence_ids.get(key)}

    # shared invariants across REAL domains
    shared = []
    obs_keys = ["trend", "lag1_memory", "coarse_stability_R", "tail_span"]
    for ok in obs_keys:
        vals = [(k, table[k]["observables"][ok]) for k in table
                if table[k]["observables"]]
        if len(vals) >= 3:
            vs = [v for _, v in vals]
            if ok == "lag1_memory" and all(v > 0.25 for v in vs):
                shared.append(f"ALL live domains show positive day-to-day memory "
                              f"(lag1 in [{min(vs):.2f},{max(vs):.2f}]) — a cross-domain invariant.")
            if ok == "coarse_stability_R" and all(v > 0.8 for v in vs):
                shared.append(f"ALL live domains are coarse-grain stable (R>0.8) — "
                              "their means survive 2x/4x/8x time-aggregation.")

    # pairwise connections (correlation, honestly labeled)
    connections = []
    keys = [k for k in table if table[k]["observables"]]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = fetched[keys[i]]["series"], fetched[keys[j]]["series"]
            m = min(len(a), len(b))
            if m < 10:
                continue
            rho = invariants.spearman(a[-m:], b[-m:])
            if abs(rho) >= 0.4:
                connections.append({
                    "pair": f"{table[keys[i]]['name']} <-> {table[keys[j]]['name']}",
                    "spearman": round(rho, 3), "n": m,
                    "caveat": "correlation over ~30 daily points; NOT causal; "
                              "shared trends/seasonality can explain it",
                })

    return {"fetched": list(fetched.keys()), "unavailable": unavailable,
            "domains": table, "shared_invariants": shared,
            "connections": connections}
