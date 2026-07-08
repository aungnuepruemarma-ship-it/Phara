"""Research-platform fetchers — official APIs, keys from env/config, legitimate.

Keyless sources work immediately (arXiv, Crossref, OpenAlex, Semantic Scholar
free tier, PubMed). Key-gated sources (CORE, Google Custom Search, and higher
Semantic-Scholar limits) activate when you provide keys via environment
variables or a git-ignored `sciloop_data/keys.json` — never in chat, never
committed. Every request identifies itself (User-Agent) and honors a small
inter-call delay; we use official endpoints only. We do NOT scrape sites behind
bot verification or attempt to defeat CAPTCHAs — that circumvents access
controls; use the platform's API instead (which these functions do).
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Callable, Dict, List, Optional

from . import config

_CONTACT = os.environ.get("SCILOOP_CONTACT", "research@example.org")
_UA = {"User-Agent": f"SciLoop/0.1 (research runtime; mailto:{_CONTACT})"}
_LAST_CALL = {"t": 0.0}
_MIN_INTERVAL = 0.34  # polite: <= ~3 req/s across the whole module


# ── key resolution (env first, then workspace keys.json) ─────────────────────
def _keys_file() -> dict:
    p = config.WORKSPACE / "keys.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def key(name: str) -> Optional[str]:
    v = os.environ.get(name)
    if v:
        return v
    return _keys_file().get(name)


# ── polite HTTP ──────────────────────────────────────────────────────────────
def _throttle():
    dt = time.time() - _LAST_CALL["t"]
    if dt < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - dt)
    _LAST_CALL["t"] = time.time()


def _get(url: str, headers: Optional[dict] = None, timeout: float = 20):
    _throttle()
    h = dict(_UA)
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _get_json(url: str, headers: Optional[dict] = None, timeout: float = 20):
    try:
        return json.loads(_get(url, headers, timeout))
    except Exception:
        return None


def _rec(title, authors, year, url, abstract, source, doi=None) -> dict:
    return {"title": (title or "").strip()[:300],
            "authors": authors[:6] if isinstance(authors, list) else [],
            "year": year, "url": url or (f"https://doi.org/{doi}" if doi else ""),
            "doi": doi, "abstract": (abstract or "")[:400], "source": source}


# ── keyless sources ──────────────────────────────────────────────────────────
def s_arxiv(q: str, n: int = 5) -> List[dict]:
    url = ("https://export.arxiv.org/api/query?search_query=all:"
           + urllib.parse.quote(q) + f"&max_results={n}&sortBy=relevance")
    try:
        root = ET.fromstring(_get(url))
    except Exception:
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in root.findall("a:entry", ns):
        t = e.find("a:title", ns); s = e.find("a:summary", ns); i = e.find("a:id", ns)
        auth = [a.find("a:name", ns).text for a in e.findall("a:author", ns)
                if a.find("a:name", ns) is not None]
        out.append(_rec(t.text if t is not None else "", auth, None,
                        i.text if i is not None else "", s.text if s is not None else "", "arxiv"))
    return out


def s_crossref(q: str, n: int = 5) -> List[dict]:
    url = ("https://api.crossref.org/works?rows=%d&query=%s&select=DOI,title,author,"
           "published,abstract,container-title" % (n, urllib.parse.quote(q)))
    if _CONTACT:
        url += "&mailto=" + urllib.parse.quote(_CONTACT)
    d = _get_json(url)
    if not d:
        return []
    out = []
    for it in d.get("message", {}).get("items", []):
        auth = [f"{a.get('given','')} {a.get('family','')}".strip()
                for a in (it.get("author") or [])]
        yr = ((it.get("published") or {}).get("date-parts") or [[None]])[0][0]
        out.append(_rec((it.get("title") or [""])[0], auth, yr, "",
                        it.get("abstract", ""), "crossref", doi=it.get("DOI")))
    return out


def s_openalex(q: str, n: int = 5) -> List[dict]:
    url = ("https://api.openalex.org/works?per-page=%d&search=%s"
           "&select=title,doi,authorships,publication_year,primary_location"
           % (n, urllib.parse.quote(q)))
    if _CONTACT:
        url += "&mailto=" + urllib.parse.quote(_CONTACT)
    d = _get_json(url)
    if not d:
        return []
    out = []
    for w in d.get("results", []):
        auth = [(a.get("author") or {}).get("display_name", "")
                for a in (w.get("authorships") or [])]
        doi = (w.get("doi") or "").replace("https://doi.org/", "") or None
        out.append(_rec(w.get("title"), auth, w.get("publication_year"), "", "",
                        "openalex", doi=doi))
    return out


def s_semantic_scholar(q: str, n: int = 5) -> List[dict]:
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?query=%s&limit=%d"
           "&fields=title,abstract,authors,year,externalIds,openAccessPdf"
           % (urllib.parse.quote(q), n))
    hdr = {}
    k = key("S2_API_KEY")
    if k:
        hdr["x-api-key"] = k
    d = _get_json(url, headers=hdr)
    if not d:
        return []
    out = []
    for p in d.get("data", []):
        auth = [a.get("name", "") for a in (p.get("authors") or [])]
        out.append(_rec(p.get("title"), auth, p.get("year"),
                        (p.get("openAccessPdf") or {}).get("url", ""),
                        p.get("abstract", ""), "semantic_scholar",
                        doi=(p.get("externalIds") or {}).get("DOI")))
    return out


def s_pubmed(q: str, n: int = 5) -> List[dict]:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    extra = "&api_key=" + key("NCBI_API_KEY") if key("NCBI_API_KEY") else ""
    d = _get_json(f"{base}/esearch.fcgi?db=pubmed&retmode=json&retmax={n}"
                  f"&term={urllib.parse.quote(q)}{extra}")
    ids = (d or {}).get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    s = _get_json(f"{base}/esummary.fcgi?db=pubmed&retmode=json&id={','.join(ids)}{extra}")
    res = (s or {}).get("result", {})
    out = []
    for pid in ids:
        p = res.get(pid)
        if not p:
            continue
        auth = [a.get("name", "") for a in (p.get("authors") or [])]
        out.append(_rec(p.get("title"), auth, (p.get("pubdate") or "")[:4],
                        f"https://pubmed.ncbi.nlm.nih.gov/{pid}/", "", "pubmed"))
    return out


# ── key-gated sources ────────────────────────────────────────────────────────
def s_core(q: str, n: int = 5) -> List[dict]:
    k = key("CORE_API_KEY")
    if not k:
        raise KeyError("CORE_API_KEY not set")
    url = "https://api.core.ac.uk/v3/search/works?limit=%d&q=%s" % (n, urllib.parse.quote(q))
    d = _get_json(url, headers={"Authorization": f"Bearer {k}"})
    out = []
    for it in (d or {}).get("results", []):
        auth = [a.get("name", "") for a in (it.get("authors") or [])]
        out.append(_rec(it.get("title"), auth, it.get("yearPublished"),
                        it.get("downloadUrl", ""), it.get("abstract", ""), "core",
                        doi=it.get("doi")))
    return out


def s_google_cse(q: str, n: int = 5) -> List[dict]:
    k, cx = key("GOOGLE_API_KEY"), key("GOOGLE_CSE_ID")
    if not (k and cx):
        raise KeyError("GOOGLE_API_KEY and GOOGLE_CSE_ID required")
    url = ("https://www.googleapis.com/customsearch/v1?key=%s&cx=%s&num=%d&q=%s"
           % (k, cx, min(n, 10), urllib.parse.quote(q)))
    d = _get_json(url)
    out = []
    for it in (d or {}).get("items", []):
        out.append(_rec(it.get("title"), [], None, it.get("link", ""),
                        it.get("snippet", ""), "google_cse"))
    return out


REGISTRY: Dict[str, dict] = {
    "arxiv": {"fn": s_arxiv, "needs": []},
    "crossref": {"fn": s_crossref, "needs": []},
    "openalex": {"fn": s_openalex, "needs": []},
    "semantic_scholar": {"fn": s_semantic_scholar, "needs": [], "optional": ["S2_API_KEY"]},
    "pubmed": {"fn": s_pubmed, "needs": [], "optional": ["NCBI_API_KEY"]},
    "core": {"fn": s_core, "needs": ["CORE_API_KEY"]},
    "google_cse": {"fn": s_google_cse, "needs": ["GOOGLE_API_KEY", "GOOGLE_CSE_ID"]},
}


def configured_sources() -> List[dict]:
    out = []
    for name, spec in REGISTRY.items():
        ready = all(key(k) for k in spec["needs"])
        enhanced = [k for k in spec.get("optional", []) if key(k)]
        out.append({"source": name, "ready": ready,
                    "needs_keys": [k for k in spec["needs"] if not key(k)],
                    "enhanced_by": enhanced})
    return out


def search_all(query: str, per_source: int = 4) -> dict:
    results: List[dict] = []
    status: Dict[str, str] = {}
    seen = set()
    for name, spec in REGISTRY.items():
        if not all(key(k) for k in spec["needs"]):
            status[name] = "needs key: " + ",".join(spec["needs"])
            continue
        try:
            recs = spec["fn"](query, per_source)
            status[name] = f"ok ({len(recs)})"
            for r in recs:
                dedup = (r.get("doi") or r["title"][:60]).lower()
                if dedup and dedup not in seen:
                    seen.add(dedup)
                    results.append(r)
        except Exception as exc:
            status[name] = f"error: {str(exc)[:80]}"
    return {"query": query, "count": len(results), "status": status, "results": results}
