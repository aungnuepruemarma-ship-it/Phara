"""
Onion / Dark Web Search MCP Server

Routes all requests through the local Tor SOCKS5 proxy (127.0.0.1:9050)
to search .onion sites via Torch and other dark web search engines.

Usage: ensure Tor is running (`tor` or `service tor start`), then start
this server. Set TOR_SOCKS_PORT to override the default 9050.

For security research and educational use only.
"""
from __future__ import annotations

import os
import json
import re
from typing import Annotated, Optional

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Onion Search",
    instructions=(
        "Search .onion sites via Torch and other dark web search engines "
        "through the Tor network. Tor must be running locally. "
        "For security research and educational purposes only."
    ),
)

TOR_PORT  = int(os.environ.get("TOR_SOCKS_PORT", "9050"))
TOR_PROXY = {"http": f"socks5h://127.0.0.1:{TOR_PORT}", "https": f"socks5h://127.0.0.1:{TOR_PORT}"}
TIMEOUT   = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Accept-Language": "en-US,en;q=0.5",
}


def _tor_session() -> requests.Session:
    s = requests.Session()
    s.proxies.update(TOR_PROXY)
    s.headers.update(HEADERS)
    return s


def _check_tor() -> bool:
    try:
        s = _tor_session()
        r = s.get("https://check.torproject.org/api/ip", timeout=10)
        return r.json().get("IsTor", False)
    except Exception:
        return False


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def check_tor_connection() -> str:
    """Check whether the Tor network is reachable and this server's exit IP."""
    try:
        s = _tor_session()
        r = s.get("https://check.torproject.org/api/ip", timeout=10)
        data = r.json()
        if data.get("IsTor"):
            return f"Tor is active. Exit node IP: {data.get('IP', 'unknown')}"
        return f"Connected but NOT through Tor. IP: {data.get('IP', 'unknown')}"
    except Exception as exc:
        return f"Cannot reach Tor: {exc}\nMake sure Tor is running: `tor` or `service tor start`"


@mcp.tool()
async def torch_search(
    query: Annotated[str, "Search query for Torch dark web search engine"],
    max_results: Annotated[int, "Maximum results to return (1-20)"] = 10,
) -> str:
    """
    Search the dark web using Torch (xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion).

    Routes through Tor. Returns onion URLs, titles, and snippets.
    For security research and educational use only.
    """
    try:
        s = _tor_session()
        torch_url = "http://xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion/4a1f6b371c/search.cgi"
        r = s.get(torch_url, params={"q": query, "cmd": "Search", "ps": "10"}, timeout=TIMEOUT)
        html = r.text

        # Parse results: Torch returns basic HTML
        results = []
        # Find result blocks
        blocks = re.findall(
            r'<dt><a href="(http[^"]+)"[^>]*>([^<]+)</a>.*?<dd>(.*?)</dd>',
            html, re.DOTALL
        )
        for url, title, snippet in blocks[:max_results]:
            results.append({
                "url": url.strip(),
                "title": _strip_html(title).strip(),
                "snippet": _strip_html(snippet)[:300].strip(),
            })

        if not results:
            # Fallback: look for any links
            links = re.findall(r'href="(http://[a-z2-7]{16,56}\.onion[^"]*)"', html)
            for link in links[:max_results]:
                results.append({"url": link, "title": "", "snippet": ""})

        if not results:
            return f"No results found for '{query}' on Torch.\n\nRaw response snippet:\n{html[:500]}"

        lines = [f"Torch results for '{query}' ({len(results)} found):\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r['title'] or '(no title)'}")
            lines.append(f"    URL: {r['url']}")
            if r["snippet"]:
                lines.append(f"    {r['snippet']}")
            lines.append("")
        return "\n".join(lines)
    except Exception as exc:
        return f"Torch search failed: {exc}"


@mcp.tool()
async def ahmia_search(
    query: Annotated[str, "Search query"],
    max_results: Annotated[int, "Maximum results (1-20)"] = 10,
) -> str:
    """
    Search .onion sites via Ahmia (ahmia.fi) — a clearnet-accessible dark web search index.

    Ahmia filters illegal content and is the safer option for research.
    Does NOT require Tor (uses clearnet endpoint).
    """
    try:
        r = requests.get(
            "https://ahmia.fi/search/",
            params={"q": query},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        html = r.text

        results = []
        # Extract .onion results from Ahmia HTML
        blocks = re.findall(
            r'<h4><a[^>]*href="(/search/redirect[^"]*)"[^>]*>([^<]+)</a></h4>.*?<p[^>]*>(.*?)</p>',
            html, re.DOTALL
        )
        for href, title, snippet in blocks[:max_results]:
            # Decode the onion URL from the redirect
            onion_match = re.search(r'redirect_url=(http[^&"]+)', href)
            onion_url = onion_match.group(1) if onion_match else f"https://ahmia.fi{href}"
            results.append({
                "url": requests.utils.unquote(onion_url),
                "title": _strip_html(title).strip(),
                "snippet": _strip_html(snippet)[:300].strip(),
            })

        if not results:
            return f"No results from Ahmia for '{query}'."

        lines = [f"Ahmia results for '{query}' ({len(results)} found):\n"]
        for i, res in enumerate(results, 1):
            lines.append(f"[{i}] {res['title']}")
            lines.append(f"    URL: {res['url']}")
            if res["snippet"]:
                lines.append(f"    {res['snippet']}")
            lines.append("")
        return "\n".join(lines)
    except Exception as exc:
        return f"Ahmia search failed: {exc}"


@mcp.tool()
async def fetch_onion_page(
    url: Annotated[str, "Full .onion URL to fetch (must start with http://*.onion)"],
    max_chars: Annotated[int, "Maximum characters of content to return"] = 3000,
) -> str:
    """
    Fetch and extract readable text from a .onion page via Tor.

    Strips HTML and returns plain text content.
    For security research and educational use only.
    """
    if ".onion" not in url:
        return "Error: URL must be a .onion address."
    try:
        s = _tor_session()
        r = s.get(url, timeout=TIMEOUT)
        text = _strip_html(r.text)[:max_chars]
        return f"Content from {url} (status {r.status_code}):\n\n{text}"
    except Exception as exc:
        return f"Failed to fetch {url}: {exc}"


@mcp.tool()
async def list_search_engines() -> str:
    """List available dark web / onion search engines and their status."""
    engines = [
        ("Torch",   "xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion", "Requires Tor", "Largest onion index, no filtering"),
        ("Ahmia",   "ahmia.fi",                                                          "Clearnet",     "Filters illegal content, researcher-friendly"),
        ("Haystak", "haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxfid.onion",  "Requires Tor", "Large index with advanced search"),
        ("OnionLand","onionlandsearchengine5nktf4gxb4tpqzwpq2n7wopqvxwlqrhfxv5mf6id.onion","Requires Tor","Categorized directory + search"),
    ]
    lines = ["Available onion search engines:\n"]
    for name, addr, access, desc in engines:
        lines.append(f"  {name:<12} ({access})")
        lines.append(f"    Address: {addr}")
        lines.append(f"    Notes:   {desc}")
        lines.append("")
    lines.append("Use torch_search for Torch, ahmia_search for Ahmia.")
    lines.append("Run check_tor_connection first to verify Tor is active.")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
