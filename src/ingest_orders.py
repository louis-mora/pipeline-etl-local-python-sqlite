import csv
import os
import sys
import sqlite3
from typing import List, Optional, Dict, Any


# ----------------------------
# Conversions
# ----------------------------
def to_int(value: str) -> Optional[int]:
    value = value.strip()
    if value == "":
        return None
    return int(value)


def to_float(value: str) -> Optional[float]:
    value = value.strip()
    if value == "":
        return None
    return float(value)


# ----------------------------
# Validation
# ----------------------------
EXPECTED_COLUMNS = [
    "order_id",
    "order_date",
    "customer_id",
    "product_id",
    "product_category",
    "quantity",
    "unit_price",
]


def validate_schema(headers: List[str]) -> None:
    """
    Vérifie que le CSV contient exactement les colonnes attendues.
    Raise ValueError si mismatch.
    """
    missing = [c for c in EXPECTED_COLUMNS if c not in headers]
    extra = [h for h in headers if h not in EXPECTED_COLUMNS]

    if missing or extra:
        msg = "Schema mismatch.\n"
        if missing:
            msg += f"- Missing columns: {missing}\n"
        if extra:
            msg += f"- Unexpected columns: {extra}\n"
        msg += f"- Found headers: {headers}"
        raise ValueError(msg)


# ----------------------------
# DB init (idempotent)
# ----------------------------
def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS orders_raw;")
    cur.execute(
        """
        CREATE TABLE orders_raw (
            order_id          TEXT,
            order_date        TEXT,
            customer_id       TEXT,
            product_id        TEXT,
            product_category  TEXT,
            quantity          INTEGER,
            unit_price        REAL
        );
        """
    )
    conn.commit()


# ----------------------------
# Load CSV -> DB
# ----------------------------
def load_csv_to_db(csv_path: str, conn: sqlite3.Connection) -> int:
    rows_inserted = 0
    cur = conn.cursor()

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row (fieldnames is None).")

        headers = [h.strip() for h in reader.fieldnames]
        validate_schema(headers)

        for line_num, row in enumerate(reader, start=2):  # start=2: header = line 1
            try:
                order_id = row["order_id"].strip()
                order_date = row["order_date"].strip()
                customer_id = row["customer_id"].strip()
                product_id = row["product_id"].strip()
                product_category = row["product_category"].strip()
                quantity = to_int(row["quantity"])
                unit_price = to_float(row["unit_price"])

                cur.execute(
                    """
                    INSERT INTO orders_raw (
                        order_id, order_date, customer_id, product_id,
                        product_category, quantity, unit_price
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        order_id,
                        order_date,
                        customer_id,
                        product_id,
                        product_category,
                        quantity,
                        unit_price,
                    ),
                )
                rows_inserted += 1

            except KeyError as e:
                raise KeyError(f"Missing expected key {e} at CSV line {line_num}. Row={row}") from e
            except ValueError as e:
                raise ValueError(f"Invalid value at CSV line {line_num}. Row={row}. Error={e}") from e

    conn.commit()
    return rows_inserted


def verify_db(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM orders_raw;")
    (count,) = cur.fetchone()
    return int(count)


# ----------------------------
# CLI + main
# ----------------------------
def parse_args(argv: List[str]) -> Dict[str, str]:
    """
    Parsing minimaliste sans argparse (sobriété).
    Usage:
      python ingest_orders.py --csv path/to/orders_raw.csv --db warehouse.db
    """
    if "--csv" not in argv or "--db" not in argv:
        raise ValueError("Usage: python ingest_orders.py --csv <csv_path> --db <db_path>")

    csv_idx = argv.index("--csv") + 1
    db_idx = argv.index("--db") + 1

    if csv_idx >= len(argv) or db_idx >= len(argv):
        raise ValueError("Missing value for --csv or --db")

    return {"csv_path": argv[csv_idx], "db_path": argv[db_idx]}


def main(argv: List[str]) -> int:
    try:
        args = parse_args(argv)
        csv_path = args["csv_path"]
        db_path = args["db_path"]

        print(f"[START] Ingestion CSV -> SQLite")
        print(f"[INFO] CSV: {csv_path}")
        print(f"[INFO] DB : {db_path}")

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        conn = sqlite3.connect(db_path)
        try:
            print("[STEP] init_db (DROP/CREATE) ...")
            init_db(conn)
            print("[OK] DB initialized.")

            print("[STEP] load_csv_to_db ...")
            inserted = load_csv_to_db(csv_path, conn)
            print(f"[OK] Inserted rows: {inserted}")

            count = verify_db(conn)
            print(f"[CHECK] DB row count: {count}")

            if count != inserted:
                print("[WARN] COUNT(*) != inserted (unexpected). Check logic.")

            print("[DONE] Ingestion completed successfully.")
            return 0

        finally:
            conn.close()

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
