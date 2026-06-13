import sqlite3
import pandas as pd
import os

DB_PATH = "data/superstore.db"
CSV_PATH = "data/superstore.csv"

def create_database():
    if os.path.exists(DB_PATH):
        print("Database already exists, skipping creation.")
        return

    print("Loading CSV...")
    df = pd.read_csv(CSV_PATH, encoding="latin-1")

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )

    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    print("Columns:", list(df.columns))

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("orders", conn, if_exists="replace", index=False)
    conn.close()

    print(f"Database created at {DB_PATH}")
    print("Done!")

if __name__ == "__main__":
    create_database()