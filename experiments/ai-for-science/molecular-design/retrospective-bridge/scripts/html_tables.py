"""Small standard-library parser for publisher HTML tables."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table" and not self.in_table:
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_row = True
            self.row = []
        elif self.in_row and tag in {"th", "td"}:
            self.in_cell = True
            self.cell_parts = []

    def handle_endtag(self, tag: str) -> None:
        if self.in_cell and tag in {"th", "td"}:
            value = re.sub(r"\s+", " ", " ".join(self.cell_parts)).strip()
            self.row.append(value)
            self.in_cell = False
        elif self.in_row and tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.in_row = False
        elif self.in_table and tag == "table":
            self.in_table = False

    def handle_data(self, data: str) -> None:
        if self.in_cell and data.strip():
            self.cell_parts.append(data.strip())


def parse_first_table(path: Path) -> list[list[str]]:
    parser = _TableParser()
    parser.feed(path.read_text())
    return parser.rows
