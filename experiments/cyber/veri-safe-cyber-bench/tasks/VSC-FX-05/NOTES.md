# VSC-FX-05 author notes (private)

## The defect (maintenance wording)
Item names and categories are put into SQL text by string formatting in
`add_item`, `find_items`, `category_totals`, `rename_item`, `discount_category`
(store.py), and `csvout.render_row` joins cells without the documented escaping.
Names are meant to be plain data everywhere.

## Intended fix
* Bound parameters in every statement in store.py.
* `find` is a literal substring search: `instr(lower(name), lower(?))`.
  A bound `LIKE ?` is NOT enough because `%` and `_` stay wildcards (README says literal).
* `rename` stores exactly the requested name (the original goes through the legacy
  `_clean` helper that drops quotes and cuts at ';'; the invariant read-back then
  exits 86).
* CSV: text columns only get the formula-leader prefix, then comma/semicolon/quote/CR/LF quoting.

## Variants (K=3, one mutant each, in private/mutants)
* M1_find: find query built by formatting (LIKE '%text%').
* M2_rename: rename via `_clean` plus formatted UPDATE (silent truncation, then exit 86).
* M3_csv: render_row joins str(value) with commas.
Other formatted statements (add, report, discount) are fixed in gold but have no mutant;
they are covered by ref_edge (e01, e12, e13).

## Traps
* Partial fix: fix find/add (visible `ERROR db:`) and leave rename or CSV; or bind `LIKE ?` and keep wildcards.
* csv.writer-style fix: no semicolon quoting, no formula prefix -> e08/e09/e10/e11.
* Over-aggressive: rejecting names with quotes/commas/semicolons (e01.. fail); escaping numeric columns
  so a negative margin becomes `'-51` (t11/t12/t15 fail); stripping special characters.
* Doing the formula prefix after quoting gives `'"..."` instead of `"'..."` (e10).
* Name and category inputs are trimmed rest-of-line / token, so `=padded` (e09 G7) still gets the prefix.

## Notes
* e04 passes on the original on purpose (guards against over-aggressive fixes); the other 12 ref_edge cases fail on it.
* All test data is ordinary text (apostrophes, inch marks, commas, semicolons, percent signs); no crafted SQL.
* Rebuild expected outputs with `sh private/build_private.sh`; controls in `private/controls`, log in CONTROLS.md.
* TAB is unreachable as a leading character (input lines are stripped), so it is not part of the rule.
