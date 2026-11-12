import re
from datetime import datetime, timedelta

from odoo import Command, fields, models


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value):
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no", "n")
    return bool(value)


def _to_datetime(value):
    number = _to_float(value)
    if number is not None:
        # o-spreadsheet, like Excel, counts dates as serial days from 1899-12-30.
        return datetime(1899, 12, 30) + timedelta(days=number)
    try:
        return fields.Datetime.to_datetime(value)
    except (TypeError, ValueError):
        return None


def _to_ids(value):
    items = value if isinstance(value, (list, tuple)) else re.split(r"\D+", str(value))
    return [int(n) for n in map(_to_float, items) if n is not None and n.is_integer()]


def _cast(field, value):
    ftype = field.type
    if value is None or value == "":
        # A mapped cell left empty clears the field: the mapping is deliberate.
        return [Command.clear()] if ftype in ("one2many", "many2many") else False
    number = _to_float(value)
    whole = number if number is not None and number.is_integer() else None
    if ftype in ("float", "monetary"):
        return number
    if ftype == "integer":
        return None if number is None else int(number)
    if ftype == "boolean":
        return _to_bool(value)
    if ftype in ("char", "text", "html"):
        return str(value)
    if ftype == "selection":
        return str(int(whole)) if whole is not None else str(value)
    if ftype == "datetime":
        return _to_datetime(value)
    if ftype == "date":
        dt = _to_datetime(value)
        return dt.date() if dt else None
    if ftype == "many2one":
        return None if whole is None else int(whole)
    if ftype in ("one2many", "many2many"):
        ids = _to_ids(value)
        return [Command.set(ids)] if ids else None
    return None


def _candidates(root, records, segment):
    hook = getattr(root, "_linking_candidates", None)
    if hook is not None:
        return hook(records, segment)
    if "display_type" not in records._fields:
        return records
    # Skip section/note rows so positions count only real data lines. Models
    # like account.move.line make display_type required and tag real lines as
    # "product", so only these layout markers may be dropped, never every row.
    return records.filtered(
        lambda record: record.display_type
        not in ("line_section", "line_subsection", "line_note")
    )


def _line_label(root, line, index):
    # A glue module can override _linking_label to pin the preview to whatever
    # best identifies its lines; otherwise fall back to display_name.
    hook = getattr(root, "_linking_label", None)
    if hook is not None:
        label = hook(line)
        if label:
            return label
    return line.display_name or root.env._("Line %s", index)


def _line_labels(root, lines):
    return [
        {"position": index, "label": _line_label(root, line, index)}
        for index, line in enumerate(lines, start=1)
    ]


def _check_allowed(root):
    hook = getattr(root, "_check_linking_allowed", None)
    if hook is not None:
        hook()


def _write(root, record, values):
    hook = getattr(root, "_linking_write", None)
    if hook is not None:
        return hook(record, values)
    return record.write(values)


def _create_line(root, parent, segment, values):
    hook = getattr(root, "_create_linked_line", None)
    if hook is not None:
        return hook(parent, segment, values)
    field = parent._fields[segment]
    return parent.env[field.comodel_name].create(
        {field.inverse_name: parent.id, **values}
    )


def _cast_values(records, leaves):
    # Write gate: only stored, non-readonly fields pass, so an arbitrary chain
    # from the client can never reach a computed or protected field.
    values = {}
    for name, raw in leaves.items():
        field = records._fields.get(name)
        if not field or not field.store or field.readonly:
            continue
        value = _cast(field, raw)
        if value is None:
            continue
        values[name] = value
    return values


def _link_index(selector):
    value = _to_float(selector)
    if value is None or not value.is_integer() or value < 1:
        return None
    return int(value)


def _group_field_mappings(mappings):
    groups = {}
    for mapping in mappings or []:
        chain = mapping.get("chain")
        if not chain:
            continue
        *path, leaf = chain.split(".")
        selectors = dict(mapping.get("selectors") or {})
        key = (tuple(path), tuple(selectors.get(seg) for seg in path))
        group = groups.setdefault(
            key, {"path": path, "selectors": selectors, "leaves": {}}
        )
        group["leaves"][leaf] = mapping.get("value")
    return list(groups.values())


def _resolve_link_target(root, group):
    record = root
    created = False
    for depth, segment in enumerate(group["path"]):
        field = record._fields.get(segment)
        if field is None:
            return None, False
        related = record[segment]
        if field.type in ("one2many", "many2many"):
            index = _link_index(group["selectors"].get(segment))
            if index is None:
                return None, False
            candidates = _candidates(root, related, segment)
            if index <= len(candidates):
                record = candidates[index - 1]
            elif depth == 0 and field.type == "one2many":
                # Only the leading one2many grows a new line.
                values = _cast_values(record.env[field.comodel_name], group["leaves"])
                if not values:
                    return None, False
                record = _create_line(root, record, segment, values)
                created = True
            else:
                return None, False
        else:
            if not related:
                return None, False
            record = related
        if len(record) != 1:
            return None, False
    return record, created


def apply_field_mappings(root, mappings):
    root.ensure_one()
    _check_allowed(root)
    updated = created = 0
    for group in _group_field_mappings(mappings):
        record, was_created = _resolve_link_target(root, group)
        if record is None:
            continue
        if was_created:
            created += 1
            continue
        values = _cast_values(record, group["leaves"])
        if values:
            _write(root, record, values)
            updated += 1
    return {"updated": updated, "created": created}


def linking_selectors(root, chain):
    record = root
    model = root
    result = []
    for segment in chain.split(".")[:-1]:
        field = model._fields.get(segment)
        if field is None:
            break
        if field.type in ("one2many", "many2many"):
            lines = record[segment] if record else model.browse()
            lines = _candidates(root, lines, segment)
            result.append({"segment": segment, "labels": _line_labels(root, lines)})
            record = lines[:1]
        else:
            record = record[segment] if record else model.browse()
        model = root.env[field.comodel_name]
    return result


def linking_context(root):
    return {
        "isLinkable": True,
        "model": root._name,
        "resId": root.id,
        "recordName": root.display_name,
    }


class SpreadsheetLinkable(models.AbstractModel):
    """Optional helper for records that a spreadsheet writes into.

    The engine works on any record; a model inherits this mixin only for the
    convenience API below. Its hooks (``_check_linking_allowed``,
    ``_linking_write``, ``_linking_candidates``, ``_create_linked_line``,
    ``_linking_label``) are consulted by duck-typing and need no mixin.
    """

    _name = "spreadsheet.linkable"
    _description = "Spreadsheet Field Linking Mixin"

    def apply_field_mappings(self, mappings):
        return apply_field_mappings(self, mappings)

    def _linking_context(self):
        self.ensure_one()
        return linking_context(self)

    def _linking_selectors(self, chain):
        self.ensure_one()
        return linking_selectors(self, chain)

    def _link_spreadsheet(self, spreadsheet):
        self.ensure_one()
        stale = spreadsheet.filtered(
            lambda sheet: (
                sheet.link_res_model != self._name or sheet.link_res_id != self.id
            )
        )
        if stale:
            stale.sudo().write({"link_res_model": self._name, "link_res_id": self.id})
