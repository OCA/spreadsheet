# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.osv import expression


class SpreadsheetOcaRevision(models.Model):
    """Revisions have no access rules of their own: they follow the
    spreadsheet they belong to (``model``/``res_id``), the way attachments and
    messages follow their document. Reading a revision requires read access to
    its spreadsheet; creating, changing or deleting one requires write access
    to it."""

    _name = "spreadsheet.oca.revision"
    _description = "Spreadsheet Oca Revision"  # TODO

    model = fields.Char(required=True)
    res_id = fields.Integer(required=True, index=True)
    type = fields.Char()
    client_id = fields.Char()
    server_revision_id = fields.Char()
    next_revision_id = fields.Char()
    commands = fields.Char()

    @api.model
    def _get_spreadsheet_models(self):
        """Models whose records can own revisions."""
        return [
            name
            for name in self.env.registry.descendants(
                ["spreadsheet.abstract"], "_inherit"
            )
            if not self.env[name]._abstract
        ]

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if self.env.su:
            return super()._search(domain, offset=offset, limit=limit, order=order)
        readable = []
        for model_name in self._get_spreadsheet_models():
            documents = self.env[model_name].with_context(active_test=False)
            if not documents.has_access("read"):
                continue
            readable.append(
                [
                    ("model", "=", model_name),
                    ("res_id", "in", documents._search([])),
                ]
            )
        domain = expression.AND(
            [domain, expression.OR(readable) if readable else expression.FALSE_DOMAIN]
        )
        return super()._search(domain, offset=offset, limit=limit, order=order)

    def _check_access(self, operation):
        result = super()._check_access(operation)
        if not self:
            return result
        revisions = self - result[0] if result else self
        forbidden = revisions._get_forbidden_by_spreadsheet(operation)
        if forbidden:
            if result:
                result = (result[0] + forbidden, result[1])
            else:
                result = (
                    forbidden,
                    lambda: forbidden._make_spreadsheet_access_error(operation),
                )
        return result

    def _get_forbidden_by_spreadsheet(self, operation):
        """Return the revisions of ``self`` whose spreadsheet does not grant
        the current user the access ``operation`` needs."""
        document_operation = "read" if operation == "read" else "write"
        spreadsheet_models = set(self._get_spreadsheet_models())
        by_document = defaultdict(lambda: defaultdict(list))
        for revision in self.sudo():
            if revision.id:
                by_document[revision.model][revision.res_id].append(revision.id)
        forbidden_ids = []
        for model_name, revision_ids_by_res_id in by_document.items():
            if model_name not in spreadsheet_models:
                forbidden_ids += sum(revision_ids_by_res_id.values(), [])
                continue
            documents = (
                self.env[model_name]
                .with_context(active_test=False)
                .browse(revision_ids_by_res_id)
            )
            allowed = documents.exists()._filtered_access(document_operation)
            for res_id, revision_ids in revision_ids_by_res_id.items():
                if res_id not in allowed.ids:
                    forbidden_ids += revision_ids
        return self.browse(forbidden_ids)

    def _make_spreadsheet_access_error(self, operation):
        return AccessError(
            _(
                "You are not allowed to %(operation)s the revisions of a "
                "spreadsheet you cannot %(document_operation)s.",
                operation=operation,
                document_operation="read" if operation == "read" else "edit",
            )
        )

    def write(self, vals):
        result = super().write(vals)
        if "model" in vals or "res_id" in vals:
            # The check before the write was made on the former spreadsheet.
            self.check_access("write")
        return result
