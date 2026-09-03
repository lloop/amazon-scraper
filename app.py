import sqlite3
from pathlib import Path
from flask import Flask, jsonify, render_template, request

# PROJECT_ROOT is the directory containing app.py
PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "data" / "amazon_products.db"
VISUALIZATION_DIR = PROJECT_ROOT / "visualization"

app = Flask(
    __name__,
    template_folder=str(VISUALIZATION_DIR / "templates"),
    static_folder=str(VISUALIZATION_DIR / "static"),
    static_url_path="/static"
)

def get_db_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/products", methods=["GET"])
def get_products():
    category = request.args.get("category")
    valid_price_only = request.args.get("valid_price_only", "false").lower() == "true"

    query = "SELECT asin, title, category, price, rating, review_count, bestseller_rank, product_url, image_url, scraped_at FROM amazon_products WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if valid_price_only:
        query += " AND price IS NOT NULL"

    query += " ORDER BY price ASC"

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            products = [dict(row) for row in rows]
            return jsonify({
                "status": "success",
                "count": len(products),
                "data": products
            })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/stats", methods=["GET"])
def get_stats():
    query = """
    SELECT 
        category,
        COUNT(asin) as total_items,
        ROUND(AVG(price), 2) as avg_price,
        MIN(price) as min_price,
        MAX(price) as max_price,
        ROUND(AVG(rating), 2) as avg_rating,
        MAX(review_count) as max_reviews
    FROM amazon_products
    WHERE price IS NOT NULL
    GROUP BY category
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            
            stats = [dict(row) for row in rows]
            return jsonify({
                "status": "success",
                "categories": stats
            })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print("--- FLASK STARTUP CONFIG ---")
    print(f"Templates: {app.template_folder}")
    print(f"Static:    {app.static_folder}")
    print(f"Database:  {DB_PATH}")
    print("----------------------------")
    app.run(debug=True, host="0.0.0.0", port=5000)