import re
import time
import logging
from bs4 import BeautifulSoup
from curl_cffi import requests
from database.database import get_connection

logger = logging.getLogger("AmazonPipeline")

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "device-memory": "8",
    "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}

def fetch_product_detail(asin: str) -> str:
    """Fetches full HTML for an Amazon product detail page."""
    url = f"https://www.amazon.com/dp/{asin}"
    response = requests.get(url, headers=HEADERS, impersonate="chrome", timeout=15)
    
    if response.status_code != 200:
        raise RuntimeError(f"Detail fetch failed for ASIN {asin} with status {response.status_code}")
        
    return response.text

def parse_product_detail(html: str) -> dict:
    """Extracts price and Bestseller Rank from detail page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    
    price = None
    price_selectors = [
        "#corePrice_feature_div .a-offscreen",
        "#corePriceDisplay_desktop_feature_div .a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        ".apexPriceToPay .a-offscreen",
        "#price_inside_buybox"
    ]
    
    for selector in price_selectors:
        price_elem = soup.select_one(selector)
        if price_elem:
            price_match = re.search(r"\$\s*([\d,]+\.?\d*)", price_elem.get_text())
            if price_match:
                try:
                    price = float(price_match.group(1).replace(",", ""))
                    break
                except ValueError:
                    continue

    bestseller_rank = None
    bsr_text = soup.get_text()
    bsr_match = re.search(r"#([\d,]+)\s+in\s+([A-Za-z\s&]+)\s*\(See Top 100", bsr_text)
    if bsr_match:
        try:
            bestseller_rank = int(bsr_match.group(1).replace(",", ""))
        except ValueError:
            pass

    return {
        "price": price,
        "bestseller_rank": bestseller_rank
    }

def hydrate_missing_prices(limit: int = 10):
    """Encapsulated task: fetches detail pages for DB records missing prices."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT asin FROM amazon_products WHERE price IS NULL LIMIT ?", (limit,))
        rows = cursor.fetchall()

    if not rows:
        logger.info("No records found with missing prices.")
        return

    logger.info(f"Found {len(rows)} products missing prices. Hydrating via detail pages...")

    for row in rows:
        asin = row["asin"]
        try:
            html = fetch_product_detail(asin)
            metrics = parse_product_detail(html)
            
            with get_connection() as conn:
                conn.execute("""
                    UPDATE amazon_products 
                    SET price = COALESCE(?, price),
                        bestseller_rank = COALESCE(?, bestseller_rank),
                        scraped_at = CURRENT_TIMESTAMP
                    WHERE asin = ?
                """, (metrics["price"], metrics["bestseller_rank"], asin))
                conn.commit()
                
            logger.info(f"Hydrated ASIN {asin}: Price={metrics['price']}, BSR={metrics['bestseller_rank']}")
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Failed to hydrate ASIN {asin}: {e}")