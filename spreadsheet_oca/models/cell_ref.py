# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Shared cell-reference helpers for spreadsheet_oca.

Used by spreadsheet_alert, spreadsheet_scenario, and spreadsheet_input_param
to avoid duplicating cell-address parsing and raw-JSON access logic.
"""

import re

# Pre-compiled pattern: column letters + row number (1-based, no zero row).
_CELL_REF_RE = re.compile(r"^([A-Za-z]+)([1-9][0-9]*)$")


def _idx_to_cell_address(col_idx, row_idx):
    """Convert 0-based (col, row) to cell address like 'A1', 'B3', 'AA12'."""
    col_str = ""
    c = col_idx
    while True:
        col_str = chr(ord("A") + c % 26) + col_str
        c = c // 26 - 1
        if c < 0:
            break
    return f"{col_str}{row_idx + 1}"


def parse_cell_ref(ref):
    """
    Parse a bare cell reference like 'B3' or 'AA12' into (col_index, row_index).

    Both indices are 0-based to match the o-spreadsheet JSON cell-map format.
    Returns (None, None) on invalid input (empty string, zero row, etc.).
    """
    m = _CELL_REF_RE.match(ref.strip())
    if not m:
        return None, None
    col_str, row_str = m.group(1).upper(), m.group(2)
    col_idx = 0
    for ch in col_str:
        col_idx = col_idx * 26 + (ord(ch) - ord("A") + 1)
    col_idx -= 1  # convert to 0-based
    row_idx = int(row_str) - 1  # convert to 0-based
    return col_idx, row_idx


def parse_cell_key(key):
    """
    Parse a possibly-qualified cell key into (sheet_name_or_None, col_idx, row_idx).

    Supported formats:
      - ``"B3"``        — no sheet qualifier; sheet_name = None
      - ``"Sheet1!B3"`` — explicit sheet qualifier
    """
    key = key.strip()
    if "!" in key:
        sheet_part, addr_part = key.split("!", 1)
        sheet_name = sheet_part.strip()
    else:
        sheet_name = None
        addr_part = key
    col_idx, row_idx = parse_cell_ref(addr_part)
    return sheet_name, col_idx, row_idx


def _resolve_sheet(sheets, sheet_name=None):
    """Return the target sheet dict from a list of sheets.

    If *sheet_name* is given, searches case-insensitively; falls back to the
    first sheet if not found.  Returns None when *sheets* is empty.
    """
    if not sheets:
        return None
    if sheet_name:
        for s in sheets:
            if s.get("name", "").lower() == sheet_name.lower():
                return s
    return sheets[0]


def read_cell_value(spreadsheet_raw, cell_ref, sheet_name=None):
    """
    Read the value of a cell from a spreadsheet_raw JSON dict.

    *cell_ref* may be bare (``"B3"``) or sheet-qualified (``"Sheet1!B3"``).
    *sheet_name*, when provided, overrides any sheet qualifier embedded in
    *cell_ref* and forces lookup in the named sheet (falling back to sheet 0).

    Return value priority:
      1. The cell's evaluated ``"value"`` key (set by o-spreadsheet when the
         workbook is saved after formula evaluation in the browser).
      2. The cell's ``"content"`` string (for static / hand-typed cells).
      3. ``None`` when the cell, sheet, or raw JSON is absent.
    """
    sheets = (spreadsheet_raw or {}).get("sheets", [])
    ref_sheet, col_idx, row_idx = parse_cell_key(cell_ref)
    if col_idx is None:
        return None

    target_name = sheet_name or ref_sheet
    target_sheet = _resolve_sheet(sheets, target_name)
    if target_sheet is None:
        return None

    cells = target_sheet.get("cells", {})
    cell_addr = _idx_to_cell_address(col_idx, row_idx)
    cell_data = cells.get(cell_addr, {})
    if not cell_data:
        return None

    value = cell_data.get("value")
    if value is None:
        value = cell_data.get("content")
    return value if value != "" else None


def write_cell_content(spreadsheet_raw, cell_ref, value, sheet_name=None):
    """
    Write a value into ``cells[row][col]["content"]`` of *spreadsheet_raw* in-place.

    Creates nested dicts as needed.  *cell_ref* and *sheet_name* follow the
    same conventions as :func:`read_cell_value`.

    Returns the (mutated) *spreadsheet_raw* dict.
    """
    sheets = (spreadsheet_raw or {}).get("sheets", [])
    ref_sheet, col_idx, row_idx = parse_cell_key(cell_ref)
    if col_idx is None:
        return spreadsheet_raw

    target_name = sheet_name or ref_sheet
    target_sheet = _resolve_sheet(sheets, target_name)
    if target_sheet is None:
        return spreadsheet_raw

    cells = target_sheet.setdefault("cells", {})
    cell_addr = _idx_to_cell_address(col_idx, row_idx)
    cell_data = cells.setdefault(cell_addr, {})
    cell_data["content"] = str(value) if value is not None else ""
    return spreadsheet_raw
