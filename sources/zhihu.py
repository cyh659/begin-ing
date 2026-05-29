import logging
import time
from urllib.parse import urljoin

from curl_cffi import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

ZHIHU_HOT_URL = "https://www.zhihu.com/hot"
ZHIHU_API_URL = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50"
BASE_URL = "https://www.zhihu.com"


class ZhihuFetchError(Exception):
    pass


def fetch_hot_list(top_n=20, timeout=15):
    items = _scrape_hot_page(timeout)
    if not items:
        logger.warning("HTML scraping returned 0 items, trying API fallback")
        items = _scrape_api_fallback(timeout)
    if not items:
        raise ZhihuFetchError("Failed to fetch Zhihu hot list from both HTML and API")
    return items[:top_n]


def _fetch(url, timeout, impersonate="chrome124"):
    # curl_cffi impersonates real browser TLS fingerprint to avoid 403
    return requests.get(
        url,
        timeout=timeout,
        impersonate=impersonate,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )


def _scrape_hot_page(timeout):
    for attempt in range(3):
        try:
            resp = _fetch(ZHIHU_HOT_URL, timeout)
            resp.raise_for_status()
            items = _parse_hot_html(resp.text)
            if items:
                logger.info("Scraped %d items from Zhihu /hot HTML", len(items))
                return items
            return []
        except Exception as e:
            if attempt == 2:
                logger.error("Failed to fetch Zhihu /hot after 3 retries: %s", e)
                return []
            wait = 2 ** attempt
            logger.warning("Zhihu request attempt %d failed, retrying in %ds: %s", attempt + 1, wait, e)
            time.sleep(wait)
    return []


def _parse_hot_html(html):
    soup = BeautifulSoup(html, "lxml")
    items = []

    cards = soup.select('[class*="HotItem"], [class*="HotList-item"], [class*="HotList"], .List-item')
    if not cards:
        cards = soup.find_all("div", class_=lambda c: c and ("Hot" in c or "List" in c))

    for i, card in enumerate(cards):
        try:
            link_el = card.select_one('a[href*="/question/"], a[href*="/answer/"], a[href*="/pin/"]')
            if not link_el:
                link_el = card.find("a")

            title = link_el.get_text(strip=True) if link_el else ""
            if not title:
                title_el = card.select_one('[class*="title"], h3, h2')
                if title_el:
                    title = title_el.get_text(strip=True)
            if not title or len(title) < 2:
                continue

            href = link_el.get("href", "") if link_el else ""
            url = urljoin(BASE_URL, href) if href else ""

            excerpt_el = card.select_one('[class*="excerpt"], [class*="desc"], [class*="Excerpt"], p')
            excerpt = excerpt_el.get_text(strip=True) if excerpt_el else ""

            heat_el = card.select_one('[class*="metrics"], [class*="Metrics"], [class*="heat"], [class*="Hot"]')
            hot_score = heat_el.get_text(strip=True) if heat_el else ""

            items.append({
                "rank": i + 1,
                "title": title,
                "hot_score": hot_score,
                "excerpt": excerpt,
                "url": url,
            })
        except Exception:
            continue

    return items


def _scrape_api_fallback(timeout):
    try:
        resp = _fetch(ZHIHU_API_URL, timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error("Zhihu API fallback failed: %s", e)
        return []

    items = []
    raw_list = data.get("data", [])
    for entry in raw_list:
        target = entry.get("target", {})
        items.append({
            "rank": len(items) + 1,
            "title": target.get("title", ""),
            "hot_score": entry.get("detail_text", ""),
            "excerpt": target.get("excerpt", ""),
            "url": urljoin(BASE_URL, f"/question/{target.get('id', '')}"),
        })

    logger.info("Fetched %d items from Zhihu API fallback", len(items))
    return items
