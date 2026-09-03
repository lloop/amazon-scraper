import logging
import time
from database.database import init_db, get_connection
from scrapers.amazon_search import scrape_amazon_category

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AmazonPipeline")

CATEGORIES_TO_SCRAPE = [
    "wireless headphones",
    "mechanical keyboard",
    "gaming mouse",
    "4k monitor"
]

def save_products_to_db(products: list[dict]):
    """Upserts product dictionaries into the SQLite database."""
    if not products:
        logger.warning("No products provided for database insertion.")
        return

    query = """
    INSERT INTO amazon_products (
        asin, title, category, price, rating, review_count, bestseller_rank, product_url, image_url
    ) VALUES (
        :asin, :title, :category, :price, :rating, :review_count, :bestseller_rank, :product_url, :image_url
    )
    ON CONFLICT(asin) DO UPDATE SET
        title=EXCLUDED.title,
        price=EXCLUDED.price,
        rating=EXCLUDED.rating,
        review_count=EXCLUDED.review_count,
        product_url=EXCLUDED.product_url,
        image_url=EXCLUDED.image_url,
        scraped_at=CURRENT_TIMESTAMP;
    """
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(query, products)
        conn.commit()
        logger.info(f"Successfully upserted {cursor.rowcount} records into SQLite.")

def run_pipeline(max_pages_per_category: int = 2):
    """Initializes DB and runs the search scraping pipeline across categories."""
    logger.info("Initializing SQLite database...")
    init_db()

    for category in CATEGORIES_TO_SCRAPE:
        logger.info(f"Starting harvest for category: '{category}'")
        try:
            products = scrape_amazon_category(category, max_pages=max_pages_per_category)
            logger.info(f"Harvested {len(products)} products for '{category}'.")
            save_products_to_db(products)
        except Exception as e:
            logger.error(f"Failed to process category '{category}': {e}")
        
        # Polite delay between category runs to avoid triggering aggressive IP rate caps
        time.sleep(3)

if __name__ == "__main__":
    run_pipeline(max_pages_per_category=1)