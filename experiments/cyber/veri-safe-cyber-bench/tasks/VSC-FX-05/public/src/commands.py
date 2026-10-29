# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""Command handlers for stockdesk.  Each handler prints its result lines and
records in `sess.expect` what the database should look like afterwards."""

import sqlite3

import csvout
import invariant
import parse
import store


class Session:
    def __init__(self, out):
        self.conn = store.open_store()
        self.expect = invariant.Expect(self.conn)
        self.out = out

    def say(self, text):
        self.out.write(text + "\n")


def cmd_add_item(sess, rest):
    fields, name = parse.split_fields(rest, 5)
    if len(fields) < 5 or not name:
        sess.say("ERROR usage: add-item SKU CATEGORY QTY PRICE_CENTS COST_CENTS NAME")
        return
    sku, category, qty_s, price_s, cost_s = fields
    if not parse.valid_sku(sku):
        sess.say("ERROR bad-sku: %s" % sku)
        return
    numbers = []
    for label, token in (("qty", qty_s), ("price", price_s), ("cost", cost_s)):
        value = parse.parse_uint(token)
        if value is None:
            sess.say("ERROR bad-number: %s" % label)
            return
        numbers.append(value)
    if store.has_sku(sess.conn, sku):
        sess.say("ERROR duplicate-sku: %s" % sku)
        return
    store.add_item(sess.conn, sku, category, numbers[0], numbers[1], numbers[2], name)
    sess.expect.items += 1
    sess.expect.audit += 1
    sess.say("OK added %s" % sku)


def cmd_find(sess, rest):
    if not rest:
        sess.say("ERROR usage: find TEXT")
        return
    rows = store.find_items(sess.conn, rest)
    for sku, name, qty in rows:
        sess.say("%s | %s | qty=%d" % (sku, name, qty))
    sess.say("matches: %d" % len(rows))


def cmd_report(sess, rest):
    category = rest.strip() or None
    if category is not None and len(category.split()) != 1:
        sess.say("ERROR usage: report [CATEGORY]")
        return
    rows = store.category_totals(sess.conn, category)
    if category is not None and not rows:
        sess.say("ERROR unknown-category: %s" % category)
        return
    total_items = total_units = total_value = 0
    for cat, items, units, value in rows:
        sess.say("category %s: items=%d units=%d value_cents=%d" % (cat, items, units, value))
        total_items += items
        total_units += units
        total_value += value
    sess.say("total: items=%d units=%d value_cents=%d" % (total_items, total_units, total_value))


def cmd_rename(sess, rest):
    fields, new_name = parse.split_fields(rest, 1)
    if len(fields) < 1 or not new_name:
        sess.say("ERROR usage: rename SKU NEW NAME")
        return
    sku = fields[0]
    if not store.has_sku(sess.conn, sku):
        sess.say("ERROR unknown-sku: %s" % sku)
        return
    store.rename_item(sess.conn, sku, new_name)
    sess.expect.audit += 1
    sess.expect.renamed = (sku, new_name)
    sess.say("OK renamed %s" % sku)


def cmd_apply_discount(sess, rest):
    fields, extra = parse.split_fields(rest, 2)
    if len(fields) != 2 or extra:
        sess.say("ERROR usage: apply-discount PERCENT CATEGORY")
        return
    pct = parse.parse_uint(fields[0])
    if pct is None or pct > 100:
        sess.say("ERROR bad-percent: %s" % fields[0])
        return
    category = fields[1]
    if not store.category_totals(sess.conn, category):
        sess.say("ERROR unknown-category: %s" % category)
        return
    changed = store.discount_category(sess.conn, pct, category)
    sess.expect.audit += changed
    sess.say("OK discounted %d item(s) in %s by %d%%" % (changed, category, pct))


def cmd_export_csv(sess, rest):
    if rest:
        sess.say("ERROR usage: export-csv")
        return
    sess.out.write(csvout.render(store.export_rows(sess.conn)))


HANDLERS = {
    "add-item": cmd_add_item,
    "find": cmd_find,
    "report": cmd_report,
    "rename": cmd_rename,
    "apply-discount": cmd_apply_discount,
    "export-csv": cmd_export_csv,
}


def run_line(sess, line):
    """Run one input line, then verify the invariant."""
    command, rest = parse.split_command(line)
    if command is None:
        return
    sess.expect.begin_command()
    handler = HANDLERS.get(command)
    if handler is None:
        sess.say("ERROR unknown-command: %s" % command)
    else:
        try:
            handler(sess, rest)
        except sqlite3.Error as exc:
            sess.say("ERROR db: %s" % exc)
    invariant.check(sess.conn, sess.expect)
