"""Extract URLs from message body (HTML or plain text). Optional domain allowlist."""

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

# Default allowlist: common article/paper domains (extend as needed)
DEFAULT_ALLOWED_DOMAINS = frozenset({
    "sciencedirect.com", "nature.com", "springer.com", "tandfonline.com",
    "arxiv.org", "doi.org", "medium.com", "blogs.worldbank.org",
    "linkedin.com", "research.wur.nl", "india.mongabay.com",
    "idronline.org", "indianexpress.com", "theatlantic.com",
    "mongodb.com", "github.com", "wikipedia.org",
    "google.org", "discord.gg", "in.qgis.org", "greenwave.earth",
    "indianwetlands.in", "essd.copernicus.org", "scmp.com",
    "arstechnica.com",
})


def _extract_urls_from_html(html: str) -> list[str]:
    """Extract href URLs from HTML string."""
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("http://") or href.startswith("https://"):
            urls.append(href)
    return urls


def _extract_urls_from_text(text: str) -> list[str]:
    """Extract URLs using regex from plain text."""
    # Match http(s) URLs
    pattern = r"https?://[^\s<>\"'()]+"
    return list(dict.fromkeys(re.findall(pattern, text)))


def extract_links(body: str, *, allowlist: set[str] | None = None, allow_all: bool = False) -> list[str]:
    """
    Extract unique URLs from message body (HTML or plain).
    If allowlist is set, only return URLs whose netloc (domain) is in the set.
    If allow_all is True, allowlist is ignored.
    """
    if not body or not body.strip():
        return []
    # Try HTML first (common in email bodies)
    if "<" in body and ">" in body:
        urls = _extract_urls_from_html(body)
    else:
        urls = _extract_urls_from_text(body)
    if not urls:
        return []
    if allow_all:
        return list(dict.fromkeys(urls))
    allowed = allowlist or DEFAULT_ALLOWED_DOMAINS
    result = []
    for u in urls:
        try:
            parsed = urlparse(u)
            netloc = (parsed.netloc or "").lower().lstrip("www.")
            print("----------------------", netloc, parsed, "---------------")
            if not netloc:
                continue
            # Check exact domain or parent (e.g. *.nature.com)
            # @aseth - Commented out. Go to all links, i.e. no whitelisting
#            if netloc in allowed and u not in result:
            if u not in result:
                result.append(u)
                continue
            for d in allowed:
                if netloc == d or netloc.endswith("." + d) and u not in result:
                    result.append(u)
                    break
        except Exception:
            continue
    return list(dict.fromkeys(result))
