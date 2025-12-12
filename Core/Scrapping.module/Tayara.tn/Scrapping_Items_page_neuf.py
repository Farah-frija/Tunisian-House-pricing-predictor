import requests
from bs4 import BeautifulSoup
import time
import re
import pandas as pd

BASE_URL = "https://www.tayara.tn"
START_PATH = "/listing/c/immoneuf/immobilier-neuf/?minPrice=20000"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

def parse_price(art):
    # Prefer numeric attribute if present
    data_val = art.select_one("[data-value]")
    if data_val and data_val.has_attr("value"):
        try:
            return int(data_val["value"])
        except ValueError:
            pass

    # Fallback to price text
    price_span = art.select_one("span.font-bold.font-arabic.text-red-600")
    if price_span:
        digits = re.sub(r"[^\d]", "", price_span.get_text())
        if digits:
            return int(digits)
    return None

def parse_category(art):
    # Category is usually next to an SVG icon
    svg = art.select_one('svg[viewBox="0 0 512 512"]')
    if svg and svg.parent:
        # try closest text span
        span = svg.find_next("span")
        if span:
            return span.get_text(strip=True)
    return None

def parse_seller(art):
    # Small truncated seller/agency name
    seller_span = art.select_one("span.w-70px.overflow-hidden")
    if seller_span:
        return seller_span.get_text(strip=True)
    return None

def parse_card(art):
    item = {}

    # URL
    link_elem = art.select_one('a[target="_blank"]')
    if not link_elem or not link_elem.has_attr("href"):
        return None
    href = link_elem["href"]
    item["url"] = href if href.startswith("http") else BASE_URL + href

    # Title
    title_el = art.select_one("h2.card-title")
    item["title"] = title_el.get_text(strip=True) if title_el else None
    
    # Price
    item["price"] = parse_price(art)

    # Location + time
    loc_time_el = art.select_one("span.line-clamp-1")
    item["location_time"] = loc_time_el.get_text(strip=True) if loc_time_el else None

    # Category
    item["category"] = parse_category(art)

    # Seller / agency
    item["seller"] = parse_seller(art)

    return item

def scrape_all_pages(max_pages=100, delay=2.0):
    results = []
    page = 1

    while True:
        if max_pages is not None and page > max_pages:
            break

        url = f"{BASE_URL}{START_PATH}&page={page}"
        print(url)
        print(f"Fetching page {page}: {url}")

        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"Stop: HTTP {resp.status_code} on page {page}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("article.mx-0")
        print(f"  Found {len(cards)} listing cards")

        if not cards:
            print("Stop: no more listings.")
            break

        for art in cards:
            item = parse_card(art)
            if item:
                if "appartement" in item.get('title', '').lower() or "a vendre s+" in item.get('title', '').lower():
                    results.append(item)
                else:
                    print(item.get('title'))
        page += 1
        time.sleep(delay)

    return results

if __name__ == "__main__":
    listings = scrape_all_pages(max_pages=200, delay=2.0)
    print(f"Total listings scraped: {len(listings)}")
    df = pd.DataFrame(listings)
    df.to_csv("tayara_listings.csv", index=False, encoding="utf-8")
    print("Saved to tayara_listings.csv")
