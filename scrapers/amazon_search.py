import re
import urllib.parse
from bs4 import BeautifulSoup
from curl_cffi import requests

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "device-memory": "8",
    "downlink": "10",
    "ect": "4g",
    "rtt": "50",
    "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}

def fetch_search_page(keyword: str, page: int = 1) -> str:
    """Fetches search page HTML from Amazon using browser impersonation."""
    encoded_keyword = urllib.parse.quote_plus(keyword)
    url = f"https://www.amazon.com/s?k={encoded_keyword}&page={page}"
    
    # Use impersonate="chrome" to mimic modern Chrome TLS/JA3 handshakes
    response = requests.get(url, headers=HEADERS, impersonate="chrome", timeout=15)
    
    if response.status_code != 200:
        raise RuntimeError(f"Amazon search request failed with status code {response.status_code}")
        
    if "api-services-support@amazon.com" in response.text or "Captcha" in response.text:
        raise PermissionError("CAPTCHA challenge detected on Amazon search page.")
        
    return response.text

def parse_search_results(html: str, category: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    
    page_title = soup.title.string.strip() if soup.title else "No Title"
    if "Robot Check" in page_title or "CAPTCHA" in page_title or soup.select_one("form[action*='validateCaptcha']"):
        print("[DEBUG] Soft CAPTCHA detected!")
        return []

    cards = soup.select('div[data-component-type="s-search-result"]')
    if not cards:
        cards = [div for div in soup.select('div[data-asin]') if div.get("data-asin")]

    items = []
    for card in cards:
        asin = card.get("data-asin")
        if not asin:
            continue
            
        # Title
        title_elem = card.select_one("h2 a span, h2 span")
        title = title_elem.get_text(strip=True) if title_elem else None
        if not title:
            continue

        # Product URL (check h2 link first, fallback to any product link with ASIN)
        link_elem = card.select_one("h2 a, a.a-link-normal.s-no-hover, a.a-link-normal.s-underline-text")
        product_url = None
        if link_elem and link_elem.has_attr("href"):
            href = link_elem["href"]
            product_url = href if href.startswith("http") else f"https://www.amazon.com{href}"

        # Price (check offscreen text, then price container, then whole/fraction span)
        price = None
        price_elem = card.select_one(".a-price .a-offscreen")
        if price_elem:
            price_raw = re.sub(r"[^\d.]", "", price_elem.get_text(strip=True))
            try:
                price = float(price_raw)
            except ValueError:
                price = None
        
        if price is None:
            price_whole = card.select_one(".a-price-whole")
            price_fraction = card.select_one(".a-price-fraction")
            if price_whole:
                w = re.sub(r"[^\d]", "", price_whole.get_text(strip=True))
                f = re.sub(r"[^\d]", "", price_fraction.get_text(strip=True)) if price_fraction else "00"
                try:
                    price = float(f"{w}.{f}")
                except ValueError:
                    price = None

        # Rating (check star icon aria-label, text, or parent title)
        rating = None
        rating_elem = card.select_one("i[class*='a-icon-star'] span, span[aria-label*='out of 5 stars'], i[class*='a-icon-star']")
        if rating_elem:
            rating_text = rating_elem.get("aria-label") or rating_elem.get_text()
            rating_match = re.search(r"([0-9.]+)\s+out of", rating_text)
            if rating_match:
                try:
                    rating = float(rating_match.group(1))
                except ValueError:
                    rating = None

        # Review Count (check review count links and aria labels)
        review_count = None
        reviews_elem = card.select_one('a[href*="#customerReviews"] span, a[href*="customerReviews"] span, span.a-size-base.s-underline-text')
        if reviews_elem:
            rev_raw = re.sub(r"[^\d]", "", reviews_elem.get_text(strip=True))
            if rev_raw.isdigit():
                review_count = int(rev_raw)

        # Image URL
        img_elem = card.select_one("img.s-image")
        image_url = img_elem["src"] if img_elem and img_elem.has_attr("src") else None

        items.append({
            "asin": asin,
            "title": title,
            "category": category,
            "price": price,
            "rating": rating,
            "review_count": review_count,
            "bestseller_rank": None,
            "product_url": product_url,
            "image_url": image_url
        })

    return items

def scrape_amazon_category(keyword: str, max_pages: int = 1) -> list[dict]:
    """Harvests multiple pages for a category keyword."""
    all_products = []
    for page in range(1, max_pages + 1):
        html = fetch_search_page(keyword, page=page)
        products = parse_search_results(html, category=keyword)
        all_products.extend(products)
    return all_products


if __name__ == "__main__":
    # Isolated test run
    test_keyword = "wireless headphones"
    print(f"Testing search scraper for keyword: '{test_keyword}'...")
    results = scrape_amazon_category(test_keyword, max_pages=1)
    print(f"Successfully extracted {len(results)} items.")
    if results:
        print("Sample product:", results[0])