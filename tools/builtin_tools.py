"""
Built-in tool implementations — auto-registered on import.

Original five tools:
  knowledge_search        — semantic search over project knowledge base (Qdrant)
  extract_entities        — named entity extraction from text (LLM)
  find_analogies          — cross-domain structural analogies (embedding + LLM)
  arxiv_search            — live Arxiv paper search (no auth, stdlib XML parse)
  agent_run               — invoke any registered research agent

Real-time data tools (Sprint 7):
  web_search              — DuckDuckGo instant answer search (no auth)
  web_browse              — fetch any URL and extract readable text
  wikipedia_search        — Wikipedia REST API — article summaries
  semantic_scholar_search — Semantic Scholar paper search with citations
  pubmed_search           — PubMed / NCBI E-utilities for biomedical papers
  crossref_search         — CrossRef REST API — DOI + metadata lookup
  openalex_search         — OpenAlex open academic knowledge graph
"""
from __future__ import annotations

from tools.tool_registry import register_tool
from tools.tool_spec import ToolSpec


# ---------------------------------------------------------------------------
# 1. knowledge_search
# ---------------------------------------------------------------------------

async def _knowledge_search(query: str, project_id: str, top_k: int = 5) -> list[dict]:
    try:
        from memory.knowledge_memory import search_knowledge
        entries = search_knowledge(query=query, project_id=project_id, top_k=top_k)
        return [{"text": e.text, "kind": e.kind, "score": round(e.score, 3), "source_paper_id": e.source_paper_id} for e in entries]
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="knowledge_search",
        description="Semantic search over papers and knowledge entries indexed for this project. Returns the most relevant passages.",
        category="memory",
        input_schema={
            "type": "object",
            "properties": {
                "query":      {"type": "string", "description": "Search query"},
                "project_id": {"type": "string", "description": "Project UUID"},
                "top_k":      {"type": "integer", "default": 5, "description": "Number of results"},
            },
            "required": ["query", "project_id"],
        },
    ),
    _knowledge_search,
)


# ---------------------------------------------------------------------------
# 2. extract_entities
# ---------------------------------------------------------------------------

async def _extract_entities(text: str, context: str = "") -> list[dict]:
    try:
        from intelligence.entity_extractor import extract_entities
        entities = await extract_entities(text=text, context=context)
        return [{"name": e.name, "entity_type": e.entity_type, "domain": e.domain, "definition_snippet": e.definition_snippet, "confidence": e.confidence} for e in entities]
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="extract_entities",
        description="Extract named concepts, methods, and phenomena from a research question or hypothesis using LLM-powered NER.",
        category="analysis",
        input_schema={
            "type": "object",
            "properties": {
                "text":    {"type": "string", "description": "Text to extract entities from"},
                "context": {"type": "string", "default": "", "description": "Optional additional context"},
            },
            "required": ["text"],
        },
    ),
    _extract_entities,
)


# ---------------------------------------------------------------------------
# 3. find_analogies
# ---------------------------------------------------------------------------

async def _find_analogies(entities: list[dict], project_id: str) -> list[dict]:
    try:
        from intelligence.analogy_engine import find_analogies
        from intelligence.entity_extractor import ExtractedEntity
        entity_objs = [
            ExtractedEntity(
                name=e.get("name", ""),
                entity_type=e.get("entity_type", "concept"),
                domain=e.get("domain", "general"),
                definition_snippet=e.get("definition_snippet", ""),
                confidence=float(e.get("confidence", 0.8)),
            )
            for e in entities
        ]
        analogies = await find_analogies(entities=entity_objs, project_id=project_id)
        return [a.to_dict() if hasattr(a, "to_dict") else vars(a) for a in analogies]
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="find_analogies",
        description="Find structural analogies between extracted entities and cross-domain concepts in the knowledge base.",
        category="analysis",
        input_schema={
            "type": "object",
            "properties": {
                "entities":   {"type": "array", "items": {"type": "object"}, "description": "List of entity dicts from extract_entities"},
                "project_id": {"type": "string", "description": "Project UUID"},
            },
            "required": ["entities", "project_id"],
        },
    ),
    _find_analogies,
)


# ---------------------------------------------------------------------------
# 4. arxiv_search
# ---------------------------------------------------------------------------

async def _arxiv_search(query: str, max_results: int = 5) -> list[dict]:
    import xml.etree.ElementTree as ET
    import httpx

    url = "https://export.arxiv.org/api/query"
    params = {"search_query": f"all:{query}", "max_results": str(max_results), "sortBy": "relevance"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        results = []
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            id_el = entry.find("atom:id", ns)
            results.append({
                "title":   (title_el.text or "").strip() if title_el is not None else "",
                "summary": (summary_el.text or "").strip()[:300] if summary_el is not None else "",
                "arxiv_id": (id_el.text or "").split("/abs/")[-1] if id_el is not None else "",
            })
        return results
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="arxiv_search",
        description="Search Arxiv for recent papers matching a query. Returns titles, abstracts (truncated), and arxiv IDs.",
        category="research",
        input_schema={
            "type": "object",
            "properties": {
                "query":       {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 5, "description": "Number of results (max 10)"},
            },
            "required": ["query"],
        },
    ),
    _arxiv_search,
)


# ---------------------------------------------------------------------------
# 5. agent_run
# ---------------------------------------------------------------------------

async def _agent_run(agent_name: str, question: str, context: list[str] | None = None) -> dict:
    from agents.agent_registry import get_agent
    from agents.base_agent import AgentInput

    agent = get_agent(agent_name)
    output = await agent.arun(AgentInput(question=question, context=context or []))
    return {
        "hypothesis": output.hypothesis,
        "reasoning": output.reasoning,
        "confidence": output.confidence,
        "agent": agent_name,
    }


register_tool(
    ToolSpec(
        name="agent_run",
        description="Run any registered research agent and return its hypothesis and reasoning. Useful for getting a specialist perspective before the primary agent runs.",
        category="research",
        input_schema={
            "type": "object",
            "properties": {
                "agent_name": {"type": "string", "description": "Agent name from the agent registry"},
                "question":   {"type": "string", "description": "Research question"},
                "context":    {"type": "array", "items": {"type": "string"}, "description": "Optional list of context passages"},
            },
            "required": ["agent_name", "question"],
        },
    ),
    _agent_run,
)


# ===========================================================================
# Real-time data tools — Sprint 7
# All tools use only httpx (already a dependency) + stdlib; no new deps.
# ===========================================================================

import re as _re
import html as _html_module


def _strip_html(raw: str) -> str:
    """Strip HTML tags, scripts, styles and decode entities."""
    text = _re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=_re.DOTALL | _re.IGNORECASE)
    text = _re.sub(r"<style[^>]*>.*?</style>", "", text, flags=_re.DOTALL | _re.IGNORECASE)
    text = _re.sub(r"<[^>]+>", " ", text)
    text = _html_module.unescape(text)
    return _re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# 6. web_search — DuckDuckGo Instant Answer API
# ---------------------------------------------------------------------------

async def _web_search(query: str, max_results: int = 5) -> list[dict]:
    import httpx
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1", "no_redirect": "1"}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        results: list[dict] = []

        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "snippet": data["AbstractText"][:500],
                "url": data.get("AbstractURL", ""),
                "source": "DuckDuckGo Abstract",
            })

        for topic in (data.get("RelatedTopics") or []):
            if len(results) >= max_results:
                break
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic["Text"][:80],
                    "snippet": topic["Text"][:400],
                    "url": topic.get("FirstURL", ""),
                    "source": "DuckDuckGo",
                })
            elif isinstance(topic, dict) and topic.get("Topics"):
                for sub in topic["Topics"]:
                    if len(results) >= max_results:
                        break
                    if sub.get("Text"):
                        results.append({
                            "title": sub["Text"][:80],
                            "snippet": sub["Text"][:400],
                            "url": sub.get("FirstURL", ""),
                            "source": "DuckDuckGo",
                        })

        return results[:max_results]
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="web_search",
        description="Search the web using DuckDuckGo Instant Answers. Returns summaries and links for a query in real time — no API key required.",
        category="live_data",
        input_schema={
            "type": "object",
            "properties": {
                "query":       {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 5, "description": "Maximum results (1–10)"},
            },
            "required": ["query"],
        },
    ),
    _web_search,
)


# ---------------------------------------------------------------------------
# 7. web_browse — fetch URL and extract readable text
# ---------------------------------------------------------------------------

async def _web_browse(url: str, max_chars: int = 4000) -> dict:
    import httpx
    headers = {"User-Agent": "Mozilla/5.0 (compatible; UniversalIntelligenceLab/1.0; research bot)"}
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        ct = resp.headers.get("content-type", "")
        if "html" in ct:
            text = _strip_html(resp.text)
        else:
            text = resp.text
        text = text[:max_chars]

        return {
            "url": str(resp.url),
            "status_code": resp.status_code,
            "text": text,
            "char_count": len(text),
        }
    except Exception as exc:
        return {"url": url, "error": str(exc)[:300], "text": ""}


register_tool(
    ToolSpec(
        name="web_browse",
        description="Fetch the content of any public URL and return extracted readable text. Strips HTML, scripts, and styles. Ideal for reading papers, documentation, or web pages.",
        category="live_data",
        input_schema={
            "type": "object",
            "properties": {
                "url":       {"type": "string", "description": "Full URL to fetch (must start with https://)"},
                "max_chars": {"type": "integer", "default": 4000, "description": "Maximum characters to return"},
            },
            "required": ["url"],
        },
    ),
    _web_browse,
)


# ---------------------------------------------------------------------------
# 8. wikipedia_search — Wikipedia REST API
# ---------------------------------------------------------------------------

async def _wikipedia_search(query: str, top_k: int = 3) -> list[dict]:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # Find matching page titles
            search_resp = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "query", "list": "search", "srsearch": query,
                        "format": "json", "srlimit": top_k},
            )
            hits = search_resp.json().get("query", {}).get("search", [])

            results = []
            for hit in hits[:top_k]:
                title = hit["title"]
                summary_resp = await client.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}",
                    headers={"Accept": "application/json"},
                )
                if summary_resp.status_code == 200:
                    s = summary_resp.json()
                    results.append({
                        "title": s.get("title", title),
                        "summary": s.get("extract", "")[:600],
                        "url": (s.get("content_urls") or {}).get("desktop", {}).get("page", ""),
                        "description": s.get("description", ""),
                    })
        return results
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="wikipedia_search",
        description="Search Wikipedia and return article summaries in real time. Good for background knowledge on concepts, entities, and research topics.",
        category="live_data",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Wikipedia search query"},
                "top_k": {"type": "integer", "default": 3, "description": "Number of articles to fetch (1–5)"},
            },
            "required": ["query"],
        },
    ),
    _wikipedia_search,
)


# ---------------------------------------------------------------------------
# 9. semantic_scholar_search — S2 Graph API (no auth for basic queries)
# ---------------------------------------------------------------------------

async def _semantic_scholar_search(query: str, max_results: int = 5) -> list[dict]:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={
                    "query": query,
                    "fields": "title,abstract,authors,year,citationCount,externalIds,openAccessPdf",
                    "limit": min(max_results, 10),
                },
                headers={"User-Agent": "UniversalIntelligenceLab/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for p in (data.get("data") or []):
            authors = [a.get("name", "") for a in (p.get("authors") or [])[:4]]
            pdf = (p.get("openAccessPdf") or {}).get("url")
            results.append({
                "title": p.get("title", ""),
                "abstract": (p.get("abstract") or "")[:400],
                "authors": authors,
                "year": p.get("year"),
                "citation_count": p.get("citationCount"),
                "doi": (p.get("externalIds") or {}).get("DOI"),
                "arxiv_id": (p.get("externalIds") or {}).get("ArXiv"),
                "pdf_url": pdf,
            })
        return results
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="semantic_scholar_search",
        description="Search Semantic Scholar for academic papers with citation counts, abstracts, and open-access PDF links. Covers CS, physics, biology, medicine, and more.",
        category="live_data",
        input_schema={
            "type": "object",
            "properties": {
                "query":       {"type": "string", "description": "Paper search query"},
                "max_results": {"type": "integer", "default": 5, "description": "Number of papers (1–10)"},
            },
            "required": ["query"],
        },
    ),
    _semantic_scholar_search,
)


# ---------------------------------------------------------------------------
# 10. pubmed_search — NCBI E-utilities (free, no auth)
# ---------------------------------------------------------------------------

async def _pubmed_search(query: str, max_results: int = 5) -> list[dict]:
    import httpx
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    params_base = {"tool": "UniversalIntelligenceLab", "email": "research@lab.ai"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            search = await client.get(
                f"{BASE}/esearch.fcgi",
                params={**params_base, "db": "pubmed", "term": query,
                        "retmax": max_results, "retmode": "json", "sort": "relevance"},
            )
            ids = search.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

            summary = await client.get(
                f"{BASE}/esummary.fcgi",
                params={**params_base, "db": "pubmed", "id": ",".join(ids), "retmode": "json"},
            )
            rdata = summary.json().get("result", {})

        results = []
        for pmid in ids:
            p = rdata.get(pmid)
            if not p:
                continue
            authors = [a.get("name", "") for a in (p.get("authors") or [])[:4]]
            eloc = p.get("elocationid", "")
            doi = eloc.replace("doi: ", "") if "doi" in eloc.lower() else None
            results.append({
                "pmid": pmid,
                "title": p.get("title", ""),
                "authors": authors,
                "year": (p.get("pubdate") or "")[:4],
                "journal": p.get("fulljournalname", ""),
                "doi": doi,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })
        return results
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="pubmed_search",
        description="Search PubMed / NCBI for biomedical and life-science papers using the free E-utilities API. Returns title, authors, journal, year, DOI, and PubMed URL.",
        category="live_data",
        input_schema={
            "type": "object",
            "properties": {
                "query":       {"type": "string", "description": "PubMed search query (supports boolean AND/OR/NOT)"},
                "max_results": {"type": "integer", "default": 5, "description": "Number of results (1–10)"},
            },
            "required": ["query"],
        },
    ),
    _pubmed_search,
)


# ---------------------------------------------------------------------------
# 11. crossref_search — CrossRef REST API (free, no auth)
# ---------------------------------------------------------------------------

async def _crossref_search(query: str, max_results: int = 5) -> list[dict]:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://api.crossref.org/works",
                params={
                    "query": query,
                    "rows": min(max_results, 10),
                    "select": "DOI,title,abstract,author,published,type,container-title",
                },
                headers={"User-Agent": "UniversalIntelligenceLab/1.0 (mailto:research@lab.ai)"},
            )
            resp.raise_for_status()
            items = resp.json().get("message", {}).get("items", [])

        results = []
        for item in items:
            title = (item.get("title") or [""])[0]
            authors = [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in (item.get("author") or [])[:4]
            ]
            pub = item.get("published") or item.get("published-print") or {}
            parts = (pub.get("date-parts") or [[None]])[0]
            year = parts[0] if parts else None
            doi = item.get("DOI", "")
            abstract = _strip_html(item.get("abstract") or "")[:400]
            results.append({
                "title": title,
                "doi": doi,
                "authors": authors,
                "year": year,
                "type": item.get("type", ""),
                "journal": (item.get("container-title") or [""])[0],
                "abstract": abstract,
                "url": f"https://doi.org/{doi}" if doi else "",
            })
        return results
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="crossref_search",
        description="Search CrossRef for academic papers and retrieve DOIs, abstracts, and publication metadata. Covers all disciplines. Free and no authentication required.",
        category="live_data",
        input_schema={
            "type": "object",
            "properties": {
                "query":       {"type": "string", "description": "Paper title or keyword query"},
                "max_results": {"type": "integer", "default": 5, "description": "Number of results (1–10)"},
            },
            "required": ["query"],
        },
    ),
    _crossref_search,
)


# ---------------------------------------------------------------------------
# 12. openalex_search — OpenAlex open academic knowledge graph (free, no auth)
# ---------------------------------------------------------------------------

async def _openalex_search(query: str, max_results: int = 5) -> list[dict]:
    import httpx

    def _reconstruct_abstract(inv_index: dict | None) -> str:
        if not inv_index:
            return ""
        positions = [
            (pos, word)
            for word, pos_list in inv_index.items()
            for pos in pos_list
        ]
        positions.sort()
        return " ".join(w for _, w in positions)[:500]

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://api.openalex.org/works",
                params={
                    "search": query,
                    "per-page": min(max_results, 10),
                    "select": (
                        "title,doi,authorships,publication_year,"
                        "cited_by_count,primary_location,abstract_inverted_index"
                    ),
                },
                headers={"User-Agent": "UniversalIntelligenceLab/1.0 (mailto:research@lab.ai)"},
            )
            resp.raise_for_status()
            works = resp.json().get("results", [])

        results = []
        for w in works:
            authors = [
                (a.get("author") or {}).get("display_name", "")
                for a in (w.get("authorships") or [])[:4]
            ]
            doi = (w.get("doi") or "").replace("https://doi.org/", "")
            source = ((w.get("primary_location") or {}).get("source") or {})
            results.append({
                "title": w.get("title", ""),
                "doi": doi,
                "authors": authors,
                "year": w.get("publication_year"),
                "cited_by_count": w.get("cited_by_count"),
                "journal": source.get("display_name", ""),
                "abstract": _reconstruct_abstract(w.get("abstract_inverted_index")),
                "url": f"https://doi.org/{doi}" if doi else "",
            })
        return results
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="openalex_search",
        description="Search OpenAlex — the free, open academic knowledge graph covering 250M+ scholarly works. Returns titles, abstracts, citation counts, authors, and DOIs.",
        category="live_data",
        input_schema={
            "type": "object",
            "properties": {
                "query":       {"type": "string", "description": "Research topic or paper title"},
                "max_results": {"type": "integer", "default": 5, "description": "Number of results (1–10)"},
            },
            "required": ["query"],
        },
    ),
    _openalex_search,
)


# ===========================================================================
# 13. code_sandbox — run Python in an isolated subprocess (experiment/test env)
# ===========================================================================

async def _code_sandbox(code: str, timeout: int = 10) -> dict:
    """Execute a self-contained Python snippet in a locked-down subprocess and
    return its output. Used by agents to run numerical experiments, simulations,
    and quick tests.

    Safety: a scrubbed environment (no secrets are exposed), CPU/memory/file-size
    rlimits, a hard wall-clock timeout, and a throwaway working directory.
    """
    import asyncio
    import os
    import shutil
    import sys
    import tempfile

    timeout = max(1, min(int(timeout or 10), 30))
    code = (code or "").strip()
    if not code:
        return {"stdout": "", "stderr": "No code provided.", "exit_code": -1, "timed_out": False}

    workdir = tempfile.mkdtemp(prefix="sandbox_")
    script = os.path.join(workdir, "main.py")
    try:
        with open(script, "w") as fh:
            fh.write(code)

        # Minimal env — deliberately omit all secrets (API keys, SECRET_KEY, ...).
        safe_env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "PYTHONUNBUFFERED": "1",
            "HOME": workdir,
            "TMPDIR": workdir,
            "LANG": "C.UTF-8",
        }

        def _limits():  # pragma: no cover — runs in the child process (Linux)
            try:
                import resource
                cpu = timeout + 1
                resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
                mem = 512 * 1024 * 1024  # 512 MB address space
                resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
                fsize = 10 * 1024 * 1024  # 10 MB max file size
                resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
            except Exception:
                pass

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-I", "-E", "-B", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workdir,
            env=safe_env,
            preexec_fn=_limits if os.name == "posix" else None,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            timed_out = False
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await proc.communicate()
            except Exception:
                pass
            return {"stdout": "", "stderr": f"Execution timed out after {timeout}s.",
                    "exit_code": -1, "timed_out": True}

        return {
            "stdout": (out or b"").decode("utf-8", "replace")[:4000],
            "stderr": (err or b"").decode("utf-8", "replace")[:2000],
            "exit_code": proc.returncode,
            "timed_out": timed_out,
        }
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc)[:500], "exit_code": -1, "timed_out": False}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


register_tool(
    ToolSpec(
        name="code_sandbox",
        description=(
            "Run a self-contained Python 3 snippet in an isolated sandbox and return its "
            "stdout/stderr. Use for numerical experiments, simulations, quick calculations, "
            "and tests. Standard library only; the code MUST print() its results. No network "
            "secrets are available; CPU, memory, and time are limited."
        ),
        category="compute",
        input_schema={
            "type": "object",
            "properties": {
                "code":    {"type": "string", "description": "Python source to execute. Must print() any output you want back."},
                "timeout": {"type": "integer", "default": 10, "description": "Max seconds to run (1–30)."},
            },
            "required": ["code"],
        },
    ),
    _code_sandbox,
)
