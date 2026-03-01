"""Fetch messages from a Google Group via web scraping (Selenium for list pagination)."""

import logging
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.shared.config import get_config
from src.shared.models import Message

logger = logging.getLogger(__name__)

# Seconds to wait for list/topic page to load
PAGE_LOAD_WAIT = 5
# Seconds between list-page next clicks
REQUEST_DELAY = 1.0

# XPath for the "Next page" button on the group's main list (30 items per page)
NEXT_PAGE_XPATH = "//div[@aria-label='Next page']"


def _make_driver(headless: bool = True) -> webdriver.Chrome:
    """Create a Chrome WebDriver (caller must quit())."""
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)


def _topic_links_from_list_page(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract topic/thread URLs from a group or topic list page."""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            href = urljoin(base_url, href)
        if "/c/" in href or "/topic/" in href or ("forum" in href and "topic" in href.lower()):
            if "groups.google.com" in href and href not in links:
                href = href.replace("/g/g", "/g")
                links.append(href)
    return list(dict.fromkeys(links))


def _parse_message_blocks(soup: BeautifulSoup, thread_url: str, thread_subject: str) -> list[dict]:
    # Remove scripts and styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    for a in soup.find_all("a", href=True):
        link_text = a.get_text(strip=True)
        href = a["href"]
        if (
            "google.co.in" in href
            or "google.com" in href
            or "facebook.com" in href
            or "twitter.com" in href
            or "kmarkiv" in href
            or "calendly.com" in href
            or "https://indianwetlands.in/" in href
            or "http://nbaindia.org/" in href
            or "https://epic.iitd.ac.in/" in href
            or "discord.com" in href
            or href == "http://www.cse.iitd.ernet.in/~aseth/"
            or href == "https://www.cse.iitd.ac.in/~aseth/"
            or href == "https://www.linkedin.com/company/gramvaani"
            or href == "https://core-stack.org/"
            or href == "https://gramvaani.org/"
            or href == "https://www.gramvaani.org/"
            or href == "http://act4d.iitd.ac.in/"
            or href == "https://www.cse.iitd.ernet.in/~aseth/act.html"
        ):
            continue
        replacement = f"{link_text} ( {href} )"
        a.replace_with(replacement)

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    subject = None
    if len(lines) > 0:
        subject = lines[0]

    posting_date = None
    filtered_lines = []
    for line in lines:
        words = line.split()
        has_link = "http://" in line or "https://" in line
        if has_link is True or (
            len(words) >= 5
            and not (
                "Skip to first" in line
                or "Sign in to reply" in line
                or "You do not have permission" in line
                or "You received this message because" in line
                or "To unsubscribe from this group" in line
                or "To view this discussion visit" in line
                or "Either email addresses" in line
                or "Aaditeshwar Seth" in line
                or "Microsoft Chair Professor" in line
                or "Co-founder" in line
                or "Technology and (Dis)Empowerment" in line
                or "googlegroups.com" in line
            )
        ):
            if re.match(r"^[A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2}:\d{2}", line):
                line = line.replace("\u202f", " ").replace("\xa0", " ").strip()
                match = re.match(r"^(.*?\b[AP]M)", line)
                if match:
                    try:
                        posting_date = datetime.strptime(match.group(1), "%b %d, %Y, %I:%M:%S %p")
                    except ValueError:
                        pass
                continue
            filtered_lines.append(line)

    messages = []
    messages.append({
        "message_id": thread_url,
        "thread_id": thread_url,
        "author": "",
        "subject": subject or "No subject",
        "body": "\n".join(filtered_lines),
        "date": posting_date,
        "url": thread_url,
    })
    return messages


def _collect_topic_urls_with_pagination(
    driver: webdriver.Chrome,
    base: str,
    limit_topics: int | None,
) -> list[str]:
    """
    Open the group main page and paginate with "Next page", collecting topic URLs from each page.
    Stops when we have at least limit_topics URLs or there is no Next button.
    """
    driver.get(base)
    time.sleep(PAGE_LOAD_WAIT)

    all_links: list[str] = []
    page_num = 0

    while True:
        page_num += 1
        soup = BeautifulSoup(driver.page_source, "html.parser")
        page_links = _topic_links_from_list_page(soup, base)
        for link in page_links:
            if link not in all_links:
                all_links.append(link)
        logger.info("List page %d: found %d links (total %d)", page_num, len(page_links), len(all_links))

        if limit_topics is not None and len(all_links) >= limit_topics:
            break

        try:
            next_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, NEXT_PAGE_XPATH))
            )
            # Disabled when on last page
            if next_btn.get_attribute("aria-disabled") == "true":
                break
            next_btn.click()
            time.sleep(PAGE_LOAD_WAIT)
        except Exception as e:
            logger.debug("No more pages or click failed: %s", e)
            break

    return all_links


def fetch_group_messages(
    group_url: str | None = None,
    *,
    limit_topics: int | None = None,
    since_message_id: str | None = None,
    headless: bool = True,
) -> list[Message]:
    """
    Fetch messages from a Google Group using Selenium to paginate the main list
    (30 messages per page) and to load each topic page for parsing.

    - group_url: e.g. https://groups.google.com/g/core-stack-nrm/
    - limit_topics: max number of topic/thread pages to fetch (None = all collected from list).
    - since_message_id: reserved for future use (filter by message id).
    - headless: run browser headless if True.
    """
    cfg = get_config()
    base = (group_url or cfg["group_url"]).rstrip("/")
    all_messages: list[Message] = []
    seen_ids: set[str] = set()

    driver = _make_driver(headless=headless)
    try:
        # Paginate main list and collect topic URLs
        topic_urls = _collect_topic_urls_with_pagination(driver, base, limit_topics)
        if limit_topics is not None:
            topic_urls = topic_urls[:limit_topics]
        logger.info("Will fetch %d topic pages", len(topic_urls))

        for topic_url in topic_urls:
            time.sleep(REQUEST_DELAY)
            try:
                driver.get(topic_url)
                time.sleep(PAGE_LOAD_WAIT)
                tsoup = BeautifulSoup(driver.page_source, "html.parser")
                title_el = tsoup.find("title") or tsoup.find("h1")
                thread_subject = title_el.get_text(strip=True) if title_el else "No subject"
                for m in _parse_message_blocks(tsoup, topic_url, thread_subject):
                    mid = m.get("message_id") or ""
                    if mid and mid in seen_ids:
                        continue
                    seen_ids.add(mid)
                    msg = Message(
                        message_id=mid,
                        thread_id=m.get("thread_id", topic_url),
                        author=m.get("author", ""),
                        subject=m.get("subject", ""),
                        body=m.get("body", ""),
                        date=m.get("date"),
                        url=m.get("url", topic_url),
                        links=[],
                    )
                    all_messages.append(msg)
            except Exception as e:
                logger.warning("Failed to fetch topic %s: %s", topic_url, e)
                continue
    finally:
        driver.quit()

    return all_messages
