"""Web search and page fetching for the assistant."""

from __future__ import annotations

import json
import logging
import re
from html.parser import HTMLParser
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlparse

from rewatch.utils.requests_session import UnacceptableAddressException, requests_session

logger = logging.getLogger(__name__)

MAX_FETCH_BYTES = 500_000
MAX_TEXT_CHARS = 14_000
MAX_JSON_PREVIEW_CHARS = 8_000
USER_AGENT = "Mozilla/5.0 (compatible; RewatchAssistant/1.0)"

_SEARCH_TYPES = frozenset({"general", "api", "dataset", "docs", "openapi"})
_JSON_URL_RE = re.compile(
    r"https?://[^\s\"'<>]+(?:\.json(?:\?[^\s\"'<>]*)?|/api/[^\s\"'<>]+|openapi\.json|swagger\.json)",
    re.I,
)
_HTTP_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
_API_SIGNAL_RE = re.compile(
    r"\b(api|endpoint|openapi|swagger|graphql|rest|json|csv|dataset|open\s*data|download)\b",
    re.I,
)


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


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    text = parser.text()
    if len(text) > MAX_TEXT_CHARS:
        return text[: MAX_TEXT_CHARS - 3] + "..."
    return text


def _augment_search_query(query: str, search_type: str = "general", site: Optional[str] = None) -> str:
    query = (query or "").strip()
    if not query:
        return query

    search_type = (search_type or "general").lower()
    if search_type not in _SEARCH_TYPES:
        search_type = "general"

    suffixes = {
        "api": "API documentation endpoint JSON",
        "dataset": "open data dataset download API JSON CSV",
        "docs": "official documentation",
        "openapi": "openapi swagger specification json",
    }
    if search_type != "general":
        query = f"{query} {suffixes[search_type]}"

    site = (site or "").strip()
    if site:
        site = site.removeprefix("site:")
        query = f"site:{site} {query}"

    return query.strip()


def _score_search_result(result: dict[str, str], topic: str, data_kind: str = "json") -> int:
    score = 0
    haystack = " ".join(
        filter(None, [result.get("title"), result.get("snippet"), result.get("url")])
    ).lower()
    topic_terms = [term for term in re.split(r"\W+", topic.lower()) if len(term) > 2]
    for term in topic_terms:
        if term in haystack:
            score += 3

    url = (result.get("url") or "").lower()
    if data_kind == "json" and (url.endswith(".json") or "/api/" in url or "openapi" in url):
        score += 12
    if any(token in haystack for token in ("open data", "open-data", "opendata", "public api", "rest api")):
        score += 8
    if any(token in haystack for token in ("swagger", "openapi", "graphql", "endpoint", "documentation")):
        score += 5
    if any(token in url for token in ("github.com", "data.gouv", "opendata", "api.", "/api/", "swagger")):
        score += 4
    if any(token in url for token in ("wikipedia.org", "reddit.com", "stackoverflow.com/questions")):
        score -= 2
    return score


def _dedupe_results(results: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for item in results:
        url = (item.get("url") or "").strip()
        if not url.startswith("http") or url in seen:
            continue
        seen.add(url)
        deduped.append(item)
    return deduped


def _parse_ddg_html_results(html: str, max_results: int) -> list[dict[str, str]]:
    patterns = [
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>\s*'
        r'(?:<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>)?',
        r'class="result-link"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>.*?'
        r'class="result__snippet"[^>]*>([^<]*)</',
        r'<a[^>]*class="[^"]*result[^"]*"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
    ]
    results: list[dict[str, str]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, html, re.I | re.S):
            href = _unwrap_ddg_redirect(match.group(1))
            title = _clean_text(match.group(2))
            snippet = _clean_text(match.group(3) if match.lastindex and match.lastindex >= 3 else "")
            if href.startswith("http"):
                results.append({"title": title, "url": href, "snippet": snippet})
            if len(results) >= max_results:
                return results
        if results:
            break
    return results


def _parse_ddg_lite_results(html: str, max_results: int) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for match in re.finditer(
        r'<a[^>]*class="result-link"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
        html,
        re.I,
    ):
        href = _unwrap_ddg_redirect(match.group(1))
        title = _clean_text(match.group(2))
        if href.startswith("http"):
            results.append({"title": title, "url": href, "snippet": ""})
        if len(results) >= max_results:
            break
    return results


def _parse_ddg_instant_answer(payload: dict[str, Any], max_results: int) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    abstract_url = (payload.get("AbstractURL") or "").strip()
    if abstract_url.startswith("http"):
        results.append(
            {
                "title": _clean_text(payload.get("Heading") or payload.get("AbstractSource") or "DuckDuckGo"),
                "url": abstract_url,
                "snippet": _clean_text(payload.get("Abstract") or ""),
                "source": "instant_answer",
            }
        )

    def walk_topics(topics: Any) -> None:
        if not isinstance(topics, list):
            return
        for topic in topics:
            if len(results) >= max_results:
                return
            if not isinstance(topic, dict):
                continue
            if "Topics" in topic:
                walk_topics(topic.get("Topics"))
                continue
            url = (topic.get("FirstURL") or "").strip()
            if url.startswith("http"):
                text = _clean_text(topic.get("Text") or "")
                title = text.split(" - ", 1)[0] if text else url
                results.append({"title": title, "url": url, "snippet": text, "source": "instant_answer"})

    walk_topics(payload.get("RelatedTopics"))
    return results[:max_results]


def _search_duckduckgo_html(query: str, max_results: int) -> list[dict[str, str]]:
    response = requests_session.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query, "b": "", "kl": ""},
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Web search failed (HTTP {response.status_code})")
    return _parse_ddg_html_results(response.text, max_results)


def _search_duckduckgo_lite(query: str, max_results: int) -> list[dict[str, str]]:
    response = requests_session.post(
        "https://lite.duckduckgo.com/lite/",
        data={"q": query},
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Web search lite failed (HTTP {response.status_code})")
    return _parse_ddg_lite_results(response.text, max_results)


def _search_duckduckgo_instant_answer(query: str, max_results: int) -> list[dict[str, str]]:
    response = requests_session.get(
        "https://api.duckduckgo.com/",
        params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1, "skip_disambig": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Instant answer search failed (HTTP {response.status_code})")
    payload = response.json()
    if not isinstance(payload, dict):
        return []
    return _parse_ddg_instant_answer(payload, max_results)


def _discovery_queries(topic: str, data_kind: str = "json") -> list[str]:
    topic = topic.strip()
    queries = [
        _augment_search_query(topic, "api" if data_kind == "json" else data_kind),
        _augment_search_query(topic, "dataset"),
        _augment_search_query(topic, "openapi"),
    ]
    if data_kind == "csv":
        queries.append(f"{topic} open data CSV download API")
    return list(dict.fromkeys(q.strip() for q in queries if q.strip()))


def _extract_candidate_endpoints(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: str, reason: str, source_url: str) -> None:
        url = url.strip().rstrip(".,);]")
        if not url.startswith("http") or url in seen:
            return
        seen.add(url)
        candidates.append({"url": url, "reason": reason, "source_page": source_url})

    for result in results:
        source_url = result.get("url") or ""
        blob = " ".join(filter(None, [result.get("title"), result.get("snippet"), source_url]))
        for match in _JSON_URL_RE.findall(blob):
            add(match, "json_or_api_url_in_snippet", source_url)
        if source_url.endswith(".json") or "/api/" in source_url.lower():
            add(source_url, "result_url_looks_like_api", source_url)

    return candidates[:12]


def _json_structure_preview(value: Any, depth: int = 0) -> Any:
    if depth >= 3:
        if isinstance(value, dict):
            return {"...": f"{len(value)} keys"}
        if isinstance(value, list):
            return [f"... {len(value)} items ..."]
        return value
    if isinstance(value, dict):
        preview: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 12:
                preview["..."] = f"{len(value) - 12} more keys"
                break
            preview[str(key)] = _json_structure_preview(item, depth + 1)
        return preview
    if isinstance(value, list):
        if not value:
            return []
        sample = [_json_structure_preview(value[0], depth + 1)]
        if len(value) > 1:
            sample.append(f"... {len(value) - 1} more items ...")
        return sample
    if isinstance(value, str) and len(value) > 240:
        return value[:240] + "..."
    return value


def _extract_urls_from_text(text: str) -> list[str]:
    urls = []
    seen: set[str] = set()
    for match in _HTTP_URL_RE.findall(text or ""):
        url = match.rstrip(".,);]")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls[:20]


def web_search(
    query: str,
    max_results: int = 5,
    search_type: str = "general",
    site: Optional[str] = None,
) -> dict[str, Any]:
    """Search the public web for documentation, APIs, datasets, or current information."""
    query = (query or "").strip()
    if not query:
        raise ValueError("Search query is required.")

    max_results = max(1, min(max_results, 10))
    effective_query = _augment_search_query(query, search_type=search_type, site=site)
    backends_tried: list[str] = []
    results: list[dict[str, str]] = []

    try:
        backends_tried.append("duckduckgo_html")
        results = _search_duckduckgo_html(effective_query, max_results)
    except UnacceptableAddressException:
        raise
    except Exception as exc:
        logger.warning("Assistant web search backend duckduckgo_html failed: %s", exc)
        results = []

    if len(results) < max_results:
        try:
            backends_tried.append("duckduckgo_lite")
            lite_results = _search_duckduckgo_lite(effective_query, max_results)
            results = _dedupe_results(results + lite_results)
        except UnacceptableAddressException:
            raise
        except Exception as exc:
            logger.warning("Assistant web search backend duckduckgo_lite failed: %s", exc)

    if len(results) < max_results:
        try:
            backends_tried.append("duckduckgo_instant_answer")
            instant_results = _search_duckduckgo_instant_answer(effective_query, max_results)
            results = _dedupe_results(results + instant_results)
        except UnacceptableAddressException:
            raise
        except Exception as exc:
            logger.warning("Assistant web search backend duckduckgo_instant_answer failed: %s", exc)

    results = results[:max_results]
    for item in results:
        item["score"] = _score_search_result(item, query, data_kind=search_type)

    results.sort(key=lambda item: item.get("score", 0), reverse=True)

    return {
        "query": query,
        "effective_query": effective_query,
        "search_type": search_type,
        "result_count": len(results),
        "results": results,
        "backend": backends_tried[-1] if backends_tried else None,
        "backends_tried": backends_tried,
    }


def discover_public_sources(
    topic: str,
    data_kind: str = "json",
    max_results: int = 8,
) -> dict[str, Any]:
    """Run targeted searches to find public APIs, datasets, and JSON endpoints for a topic."""
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("Topic is required.")

    data_kind = (data_kind or "json").lower()
    if data_kind not in {"json", "csv", "api", "dataset", "openapi"}:
        data_kind = "json"

    max_results = max(3, min(max_results, 12))
    search_type = "openapi" if data_kind == "openapi" else ("dataset" if data_kind in {"csv", "dataset"} else "api")
    queries = _discovery_queries(topic, data_kind=data_kind)
    combined: list[dict[str, Any]] = []

    for query in queries:
        try:
            batch = web_search(query, max_results=max(3, max_results // 2), search_type=search_type)
        except UnacceptableAddressException as exc:
            raise RuntimeError(f"Search blocked for security reasons: {exc}") from exc
        except Exception:
            continue
        for item in batch.get("results") or []:
            if not isinstance(item, dict):
                continue
            enriched = dict(item)
            enriched["matched_query"] = query
            enriched["score"] = _score_search_result(enriched, topic, data_kind=data_kind)
            combined.append(enriched)

    combined = _dedupe_results(combined)
    combined.sort(key=lambda item: item.get("score", 0), reverse=True)
    top_results = combined[:max_results]
    candidate_endpoints = _extract_candidate_endpoints(top_results)

    return {
        "topic": topic,
        "data_kind": data_kind,
        "search_queries": queries,
        "result_count": len(top_results),
        "results": top_results,
        "candidate_endpoints": candidate_endpoints,
        "recommended_workflow": [
            "list_data_sources and pick a type `json` data source (or another API runner if documented).",
            "fetch_url on the best documentation page or probe candidate_endpoints with fetch_url.",
            "run_query with ad-hoc YAML query_text to inspect columns.",
            "create_query and build visualizations once validation passes.",
        ],
        "assistant_note": (
            "Prefer candidate_endpoints and high-score results. Use fetch_url on docs pages to extract exact "
            "API base URLs, then validate with run_query before create_query."
        ),
    }


def fetch_url(url: str, mode: str = "auto") -> dict[str, Any]:
    """Fetch a public web page or JSON endpoint and return readable content."""
    url = _normalize_url(url)
    mode = (mode or "auto").lower()
    if mode not in {"auto", "text", "json"}:
        mode = "auto"

    try:
        response = requests_session.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json,text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
            },
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
    decoded = raw.decode(response.encoding or "utf-8", errors="replace")
    looks_like_json = (
        mode == "json"
        or "json" in content_type
        or decoded.lstrip().startswith(("{", "["))
    )

    title_match = re.search(r"<title[^>]*>([^<]+)</title>", decoded, re.I)
    title = title_match.group(1).strip() if title_match else None

    payload: dict[str, Any] = {
        "url": url,
        "title": title,
        "content_type": content_type,
    }

    if looks_like_json and mode != "text":
        try:
            parsed = json.loads(decoded)
            preview = _json_structure_preview(parsed)
            preview_text = json.dumps(preview, indent=2, default=str)
            if len(preview_text) > MAX_JSON_PREVIEW_CHARS:
                preview_text = preview_text[: MAX_JSON_PREVIEW_CHARS - 3] + "..."
            payload.update(
                {
                    "format": "json",
                    "json_preview": preview,
                    "text": preview_text,
                    "is_valid_json": True,
                }
            )
            if isinstance(parsed, dict) and any(key in parsed for key in ("openapi", "swagger", "paths", "info")):
                payload["openapi_detected"] = True
                payload["assistant_note"] = "OpenAPI/Swagger spec detected — inspect paths and servers for base URLs."
            return payload
        except json.JSONDecodeError:
            if mode == "json":
                raise RuntimeError(f"URL did not return valid JSON: {url}") from None

    if "html" in content_type or raw.lstrip().startswith(b"<"):
        text = _html_to_text(decoded)
        # Scan the raw HTML too: API links usually live in href attributes,
        # which the text extraction drops.
        discovered_urls = _extract_urls_from_text(f"{text}\n{decoded}")
        api_urls = [item for item in discovered_urls if _API_SIGNAL_RE.search(item) or item.endswith(".json")]
        payload.update(
            {
                "format": "html",
                "text": text,
                "discovered_urls": discovered_urls[:12],
                "candidate_api_urls": api_urls[:8],
            }
        )
        if api_urls:
            payload["assistant_note"] = (
                "candidate_api_urls were extracted from the page — fetch_url or run_query to validate them."
            )
        return payload

    text = decoded
    if len(text) > MAX_TEXT_CHARS:
        text = text[: MAX_TEXT_CHARS - 3] + "..."
    payload.update({"format": "text", "text": text})
    return payload
