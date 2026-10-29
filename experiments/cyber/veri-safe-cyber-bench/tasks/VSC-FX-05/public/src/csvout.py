# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""CSV rendering for export-csv.

Documented escaping rule (see README, "CSV export"):

1. Only the text columns (sku, category, name) are escaped; numeric columns
   are written as plain decimal integers and may legitimately start with '-'.
2. A text value whose first character is one of  =  +  -  or  @  gets a
   single quote (') prepended so that spreadsheet programs show it as text.
3. After step 2, if the value contains a comma, a semicolon, a double quote,
   CR or LF, it is wrapped in double quotes and every double quote inside it
   is doubled.
4. Rows end with LF.  Rows are separated exactly as in the header.
"""

HEADER = ("sku", "category", "qty", "price_cents", "margin_cents", "name")
TEXT_COLUMNS = (0, 1, 5)
FORMULA_LEADERS = ("=", "+", "-", "@")
QUOTE_TRIGGERS = (",", ";", '"', "\r", "\n")


def escape_text(value):
    text = str(value)
    if text and text[0] in FORMULA_LEADERS:
        text = "'" + text
    if any(ch in text for ch in QUOTE_TRIGGERS):
        text = '"' + text.replace('"', '""') + '"'
    return text


def render_row(row):
    return ",".join(str(value) for value in row)


def render(rows):
    """Return the full CSV document (header + rows) as a string."""
    lines = [",".join(HEADER)]
    for row in rows:
        lines.append(render_row(row))
    return "\n".join(lines) + "\n"
