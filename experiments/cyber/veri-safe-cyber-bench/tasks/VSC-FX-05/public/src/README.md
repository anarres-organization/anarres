# stockdesk

Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.

stockdesk is a toy back-office tool for a small parts warehouse. It keeps
items and a change log in an in-memory sqlite database and is driven by
command lines on standard input. Results go to standard output. Everything in
it is invented and runs locally; it has no network access.

Run: `python3 main.py < commands.in` (Python 3.12, standard library only).
Build/syntax check: `sh build.sh`.

## Input format

One command per line. Blank lines and lines whose first non-blank character
is `#` are ignored. Command words are case sensitive. "Token" means a run of
non-whitespace characters. A trailing `NAME` or `TEXT` argument is the rest of
the line, trimmed of surrounding whitespace, and may contain any characters
(spaces, quotes, commas, semicolons, `%`, `_`, ...). Names are plain data
everywhere: they are never interpreted as SQL, as a search pattern or as a
formula.

| Command | Effect | Output |
|---|---|---|
| `add-item SKU CATEGORY QTY PRICE_CENTS COST_CENTS NAME` | add an item | `OK added SKU` |
| `find TEXT` | list items whose name contains TEXT | one line `SKU \| NAME \| qty=N` per match ordered by SKU, then `matches: N` |
| `report [CATEGORY]` | totals per category (or for one category) | one `category C: items=I units=U value_cents=V` line per category ordered by name, then `total: items=I units=U value_cents=V` |
| `rename SKU NEW NAME` | replace the item's name with NEW NAME exactly as given | `OK renamed SKU` |
| `apply-discount PERCENT CATEGORY` | lower the price of every item in CATEGORY by PERCENT (integer arithmetic, rounded down) | `OK discounted N item(s) in CATEGORY by P%` |
| `export-csv` | write all items as CSV | the CSV document |

* `find` is a case-insensitive (ASCII letters) literal substring search.
  `%` and `_` in TEXT have no special meaning: `find 50%` matches only names
  that contain the three characters `50%`.
* SKUs are 1 to 16 characters from `A-Za-z0-9_-`. QTY, PRICE_CENTS,
  COST_CENTS are non-negative decimal integers of at most 9 digits. PERCENT is
  an integer from 0 to 100. Categories are single tokens and are compared
  exactly (case sensitive).
* `report` and `find` change nothing. `add-item`, `rename` and `apply-discount`
  write one change-log row per item added, renamed or discounted.

## Error handling

A command that cannot be carried out prints one line starting with `ERROR`
on standard output, changes nothing, and processing continues with the next
line:

`ERROR usage: ...`, `ERROR bad-sku: SKU`, `ERROR bad-number: qty|price|cost`,
`ERROR duplicate-sku: SKU`, `ERROR unknown-sku: SKU`,
`ERROR unknown-category: CATEGORY`, `ERROR bad-percent: VALUE`,
`ERROR unknown-command: WORD`.

An `ERROR db: ...` line means a database statement failed. Valid input never
produces it.

## CSV export

`export-csv` prints a header line `sku,category,qty,price_cents,margin_cents,name`
followed by one row per item ordered by SKU (margin_cents = price_cents -
cost_cents, which can be negative). Rows end with LF. The documented escaping
rule is:

1. Only the text columns (`sku`, `category`, `name`) are escaped. The numeric
   columns are plain decimal integers (a negative margin keeps its `-`).
2. A text value whose first character is `=`, `+`, `-` or `@` gets a single
   quote (`'`) prepended, so spreadsheets display it as text.
3. After step 2, a value containing a comma, a semicolon, a double quote, CR
   or LF is wrapped in double quotes and each double quote inside it is doubled.
   (Both comma and semicolon count as delimiters so the file reads the same in
   either spreadsheet locale.)

Example: the name `Washer, 5" ; steel` is written as `"Washer, 5"" ; steel"`;
the name `-5mm washer` is written as `'-5mm washer`.

## Internal consistency check

After every command the program compares the database with what the command
is documented to have done: the schema must be unchanged, the `items` and
`audit_log` row counts must be exactly as expected, and after `rename` the
stored name must be identical to the requested NEW NAME. If any check fails
the program prints `INVARIANT: <reason>` on standard error and exits with
status 86 (output produced so far is kept). On valid input it never fails;
a failure indicates a bug in the program.

## Source layout

* `main.py` input loop and exit status
* `commands.py` one handler per command, session state
* `parse.py` line and field parsing, validation
* `store.py` all SQL
* `csvout.py` CSV rendering
* `invariant.py` the consistency check
