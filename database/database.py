import sqlite3
import os
from pathlib import Path

# Resolves: database/database.py -> database/ -> project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = PROJECT_ROOT / "data"
DB_PATH = DB_DIR / "amazon_products.db"

def init_db():
    # Automatically create the data/ folder if it doesn't exist
    os.makedirs(DB_DIR, exist_ok=True)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(CREATE_PRODUCTS_TABLE)
        conn.commit()
        

CREATE_PRODUCTS_TABLE = """
CREATE TABLE IF NOT EXISTS amazon_products (
    asin TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL,
    rating REAL,
    review_count INTEGER,
    bestseller_rank INTEGER,
    product_url TEXT,
    image_url TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def get_connection():
    """Returns a SQLite connection object with tuple dictionary-style access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")