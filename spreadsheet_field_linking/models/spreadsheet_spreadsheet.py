from odoo import api, fields, models
from odoo.fields import Domain

from . import spreadsheet_linkable as engine


class SpreadsheetSpreadsheet(models.Model):
    _inherit = "spreadsheet.spreadsheet"

    link_res_model = fields.Char(string="Linked Model", index=True, copy=False)
    link_res_id = fields.Many2oneReference(
        string="Linked Record", model_field="link_res_model", index=True, copy=False
    )

    def _get_link_target(self):
        self.ensure_one()
        model = self.link_res_model
        if model and self.link_res_id and model in self.env:
            record = self.env[model].browse(self.link_res_id).exists()
            if record:
                return record
        return self.env["spreadsheet.linkable"]

    def _get_link_context(self):
        self.ensure_one()
        target = self._get_link_target()
        if not target:
            return {
                "isLinkable": False,
                "writable": False,
                "model": False,
                "resId": False,
                "recordName": False,
            }
        return {**engine.linking_context(target), "writable": True}

    def get_linking_context(self):
        self.ensure_one()
        return {**self._get_link_context(), "spreadsheetId": self.id}

    def get_link_selectors(self, chain):
        self.ensure_one()
        context = self._get_link_context()
        model = context.get("model")
        if not model:
            return []
        record = self.env[model].browse(context["resId"])
        return engine.linking_selectors(record, chain)

    def write_field_mappings(self, mappings):
        self.ensure_one()
        target = self._get_link_target()
        if not target:
            return {"updated": 0, "created": 0}
        return engine.apply_field_mappings(target, mappings)

    def set_link_target(self, model=False, res_id=False):
        self.ensure_one()
        self.write({"link_res_model": model or False, "link_res_id": res_id or False})
        # Return the fresh context so the client can refresh in place. Reopening
        # the spreadsheet action here would race with the live collaborative
        # session for the same document ("Component is destroyed").
        return self.get_linking_context()

    @api.model
    def get_linkable_models(self):
        result = []
        domain = Domain("transient", "=", False)
        for record in self.env["ir.model"].sudo().search(domain):
            model = self.env.get(record.model)
            if model is None or model._abstract or not model._auto:
                continue
            if model.has_access("write"):
                result.append(record.model)
        return result
