"""Web search and page fetching for the assistant."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from rewatch.utils.requests_session import UnacceptableAddressException, requests_session

MAX_FETCH_BYTES = 500_000
MAX_TEXT_CHARS = 14_000
USER_AGENT = "Mozilla/5.0 (compatible; RewatchAssistant/1.0)"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._pieces: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        elif tag in ("p", "br", "div", "li", "h1", "h2", "h3", "h4", "tr", "section", "article"):
            self._pieces.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if text:
            self._pieces.append(text + " ")

    def text(self) -> str:
        raw = "".join(self._pieces)
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are supported.")
    if not parsed.netloc:
        raise ValueError("URL must include a host.")
    return url.strip()


def _unwrap_ddg_redirect(href: str) -> str:
    if "duckduckgo.com/l/" in href and "uddg=" in href:
        params = parse_qs(urlparse(href).query)
        uddg = params.get("uddg", [None])[0]
        if uddg:
            return unquote(uddg)
    return href


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    text = parser.text()
    if len(text) > MAX_TEXT_CHARS:
        return text[: MAX_TEXT_CHARS - 3] + "..."
    return text


def fetch_url(url: str) -> dict[str, Any]:
    """Fetch a public web page and return extracted plain text."""
    url = _normalize_url(url)
    try:
        response = requests_session.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8"},
            timeout=25,
            stream=True,
        )
    except UnacceptableAddressException as exc:
        raise RuntimeError(f"URL blocked for security reasons: {exc}") from exc

    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code} fetching {url}")

    content_type = (response.headers.get("Content-Type") or "").lower()
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_content(chunk_size=32_768):
        if not chunk:
            continue
        size += len(chunk)
        if size > MAX_FETCH_BYTES:
            break
        chunks.append(chunk)

    raw = b"".join(chunks)
    if "html" in content_type or raw.lstrip().startswith(b"<"):
        text = _html_to_text(raw.decode(response.encoding or "utf-8", errors="replace"))
    else:
        text = raw.decode(response.encoding or "utf-8", errors="replace")
        if len(text) > MAX_TEXT_CHARS:
            text = text[: MAX_TEXT_CHARS - 3] + "..."

    title_match = re.search(r"<title[^>]*>([^<]+)</title>", raw.decode("utf-8", errors="replace"), re.I)
    title = title_match.group(1).strip() if title_match else None

    return {"url": url, "title": title, "content_type": content_type, "text": text}


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the public web via DuckDuckGo HTML results."""
    query = (query or "").strip()
    if not query:
        raise ValueError("Search query is required.")

    max_results = max(1, min(max_results, 8))
    try:
        response = requests_session.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "b": "", "kl": ""},
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
    except UnacceptableAddressException as exc:
        raise RuntimeError(f"Search blocked for security reasons: {exc}") from exc

    if response.status_code >= 400:
        raise RuntimeError(f"Web search failed (HTTP {response.status_code})")

    html = response.text
    results: list[dict[str, str]] = []
    for match in re.finditer(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>\s*'
        r'(?:<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>)?',
        html,
        re.I,
    ):
        href = _unwrap_ddg_redirect(match.group(1))
        title = re.sub(r"\s+", " ", match.group(2)).strip()
        snippet = re.sub(r"\s+", " ", (match.group(3) or "")).strip()
        if href.startswith("http"):
            results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= max_results:
            break

    return {"query": query, "result_count": len(results), "results": results}
