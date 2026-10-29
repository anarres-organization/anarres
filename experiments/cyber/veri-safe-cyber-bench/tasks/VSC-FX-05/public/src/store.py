# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""In-memory sqlite storage layer for stockdesk.

All statements that involve user supplied text (SKUs, categories, item names,
search text) must treat that text as plain data.
"""

import sqlite3

SCHEMA = (
    "CREATE TABLE items ("
    " sku TEXT PRIMARY KEY, category TEXT NOT NULL, qty INTEGER NOT NULL,"
    " price_cents INTEGER NOT NULL, cost_cents INTEGER NOT NULL,"
    " name TEXT NOT NULL)",
    "CREATE TABLE audit_log ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT NOT NULL,"
    " action TEXT NOT NULL)",
)


def open_store():
    conn = sqlite3.connect(":memory:", isolation_level=None)
    for statement in SCHEMA:
        conn.execute(statement)
    return conn


def schema_snapshot(conn):
    rows = conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name").fetchall()
    return tuple(rows)


def count_items(conn):
    return conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]


def count_audit(conn):
    return conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]


def has_sku(conn, sku):
    row = conn.execute("SELECT 1 FROM items WHERE sku = ?", (sku,)).fetchone()
    return row is not None


def get_name(conn, sku):
    row = conn.execute("SELECT name FROM items WHERE sku = ?", (sku,)).fetchone()
    return None if row is None else row[0]


def add_item(conn, sku, category, qty, price, cost, name):
    conn.execute(
        "INSERT INTO items (sku, category, qty, price_cents, cost_cents, name)"
        " VALUES ('%s', '%s', %d, %d, %d, '%s')" % (sku, category, qty, price, cost, name)
    )
    conn.execute("INSERT INTO audit_log (sku, action) VALUES (?, 'add')", (sku,))


def find_items(conn, text):
    """Case-insensitive (ASCII) literal substring search on item names.
    Returns [(sku, name, qty)] ordered by sku."""
    query = "SELECT sku, name, qty FROM items WHERE name LIKE '%%%s%%' ORDER BY sku" % text
    return conn.execute(query).fetchall()


def category_totals(conn, category=None):
    """Return [(category, items, units, value_cents)] ordered by category,
    optionally restricted to one category."""
    sql = "SELECT category, COUNT(*), SUM(qty), SUM(qty * price_cents) FROM items"
    if category is not None:
        sql += " WHERE category = '%s'" % category
    sql += " GROUP BY category ORDER BY category"
    return conn.execute(sql).fetchall()


def _clean(text):
    """Legacy cleanup kept from the first version of the rename command."""
    return text.replace("'", "").split(";")[0].strip()


def rename_item(conn, sku, new_name):
    clean = _clean(new_name)
    conn.execute("UPDATE items SET name = '%s' WHERE sku = '%s'" % (clean, sku))
    conn.execute("INSERT INTO audit_log (sku, action) VALUES (?, 'rename')", (sku,))


def discount_category(conn, pct, category):
    """Reduce price_cents of every item in `category` by pct percent (integer
    arithmetic, rounded down).  Returns the number of items changed."""
    cur = conn.execute(
        "UPDATE items SET price_cents = price_cents * %d / 100"
        " WHERE category = '%s'" % (100 - pct, category)
    )
    changed = cur.rowcount
    conn.execute(
        "INSERT INTO audit_log (sku, action)"
        " SELECT sku, 'discount' FROM items WHERE category = '%s'" % category
    )
    return changed


def export_rows(conn):
    """Rows for export-csv, ordered by sku:
    (sku, category, qty, price_cents, margin_cents, name)."""
    return conn.execute(
        "SELECT sku, category, qty, price_cents, price_cents - cost_cents, name"
        " FROM items ORDER BY sku"
    ).fetchall()
