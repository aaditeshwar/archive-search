"""Fetch linked content: HTML (trafilatura) or PDF (pymupdf4llm)."""

import io
from urllib.parse import urlparse

import httpx
import trafilatura
from trafilatura import fetch_url, extract

# PDF content-type or URL path
PDF_INDICATORS = (".pdf", "application/pdf")


def _is_pdf_url(url: str, content_type: str | None) -> bool:
    if content_type and "pdf" in content_type.lower():
        return True
    path = (urlparse(url).path or "").lower()
    return path.endswith(".pdf") or ".pdf?" in path

# @aseth - not used, moved to selenium
def fetch_and_extract(url: str, *, timeout: int = 30) -> tuple[str, str]:
    """
    Fetch URL and extract main text. Returns (title_or_url, extracted_text).
    Uses trafilatura for HTML and pymupdf4llm for PDF.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ArchiveSearch/1.0; +https://github.com/archive-search)",
    }
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        raw = resp.content

    if _is_pdf_url(url, content_type):
        return _extract_pdf(raw, url)
    return _extract_html(raw, url, content_type)


# @aseth - fetching through selenium with head to bypass 403 Forbidden errors by website
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import requests

def fetch_with_selenium(url, timeout=20) -> tuple[str, str]:

    options = Options()
    # @aseth - do not go headless
#    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        final_url = driver.current_url
        print("----- final_url -----", final_url)

        # Use HEAD request to detect content-type
#        head = requests.head(final_url, allow_redirects=True, timeout=timeout)
#        content_type = head.headers.get("content-type", "")

        # @aseth - using HEAD is probably redundant. getting it directly from the selenium driver
        content_type = driver.execute_script("return document.contentType;")
        print("----- content_type -----", content_type)

        if _is_pdf_url(final_url, content_type):
            # @aseth - removing redundant call to get the pdf again using requests.get
#            for request in driver.requests:
#                if request.response and 'application/pdf' in request.response.headers.get('Content-Type', ''):
#                   return _extract_pdf(request.response.body, final_url)
            resp = requests.get(final_url, timeout=timeout)
            resp.raise_for_status()
            return _extract_pdf(resp.content, final_url)

        raw_html = driver.page_source
        print("------ raw_html -------", len(raw_html))
        return _extract_html(raw_html.encode("utf-8"), final_url, content_type)

    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}")
        raise

    finally:
        driver.quit()

def _extract_html(raw: bytes, url: str, content_type: str) -> tuple[str, str]:
    """Extract main content from HTML using trafilatura."""
    html = raw.decode("utf-8", errors="replace")
    doc = extract(html, url=url, output_format="txt", include_links=False)
    title = ""
    if doc:
        try:
            from trafilatura import bare_extraction
            meta = bare_extraction(html, url=url)
            if meta:
                title = (getattr(meta, "title", None) or (meta.get("title") if isinstance(meta, dict) else None)) or ""
        except Exception:
            pass
    if not doc:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        doc = soup.get_text(separator="\n", strip=True)[:50000]
    return title or url, doc or ""


def _extract_pdf(raw: bytes, url: str) -> tuple[str, str]:
    """Extract text from PDF bytes using pymupdf4llm."""
#    try:
#        import pymupdf4llm
#    except ImportError as e:
# @aseth - fixed this
    import pymupdf
    doc = pymupdf.open(stream=raw, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return url, text[:50000]
#    text = pymupdf4llm.to_markdown(io.BytesIO(raw), page_chunks=False)
#    print(f"----------- Read pdf text: {text}")
#    if isinstance(text, list):
#        text = "\n\n".join(text)
#    return url, (text or "")[:50000]


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication (strip fragment, lowercase scheme/host)."""
    parsed = urlparse(url)
    netloc = (parsed.netloc or "").lower()
    path = parsed.path or "/"
    query = "?" + parsed.query if parsed.query else ""
    return f"{parsed.scheme.lower()}://{netloc}{path}{query}"
