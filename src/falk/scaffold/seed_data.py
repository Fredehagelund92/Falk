"""Seed a DuckDB database with example data for testing.

This creates a simple e-commerce dataset with:
- Revenue, orders, customers metrics
- Date, product_category, region dimensions
- 90 days of sample data
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import duckdb


def create_example_database(db_path: Path) -> None:
    """Create a DuckDB database with example e-commerce data.
    
    Args:
        db_path: Path where the database file should be created.
    """
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing database if it exists
    if db_path.exists():
        db_path.unlink()
    
    con = duckdb.connect(str(db_path))

    # Create the fact table (empty schema, we'll insert into it)
    con.execute("""
        CREATE TABLE sales_fact (
            date DATE,
            product_category VARCHAR,
            region VARCHAR,
            revenue DOUBLE,
            orders INTEGER,
            customers INTEGER
        )
    """)

    # Generate 90 days of sample data (all from same recent range)
    start_date = date.today() - timedelta(days=90)
    categories = ['Electronics', 'Clothing', 'Home & Garden', 'Sports', 'Books']
    regions = ['US', 'EU', 'APAC', 'LATAM']
    
    rows = []
    for day_offset in range(90):
        current_date = start_date + timedelta(days=day_offset)
        
        # Generate data for each category/region combination
        for category in categories:
            for region in regions:
                # Add some randomness and trends
                base_revenue = random.uniform(200, 2000)
                # Weekend boost
                if current_date.weekday() >= 5:
                    base_revenue *= 1.3
                
                revenue = round(base_revenue, 2)
                orders = max(1, int(revenue / random.uniform(50, 200)))
                customers = max(1, int(orders * random.uniform(0.7, 0.95)))
                
                rows.append((current_date, category, region, revenue, orders, customers))
    
    # Insert all rows
    con.executemany(
        "INSERT INTO sales_fact VALUES (?, ?, ?, ?, ?, ?)",
        rows
    )
    
    # Create indexes for better query performance
    con.execute("CREATE INDEX idx_date ON sales_fact(date)")
    con.execute("CREATE INDEX idx_category ON sales_fact(product_category)")
    con.execute("CREATE INDEX idx_region ON sales_fact(region)")
    
    con.close()
    print(f"✓ Created example database at {db_path}")
    print(f"  - {len(rows)} rows of sample data")
    print(f"  - Date range: {start_date} to {date.today()}")


if __name__ == "__main__":
    # Default path
    db_path = Path.cwd() / "data" / "warehouse.duckdb"
    create_example_database(db_path)

