# Copyright 2026 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.model
    def has_parent_relation(self, model_name):
        """Return if the model has a parent relation."""
        model = self.env.get(model_name)
        if model is None or not model.has_access("read"):
            return False
        return model._parent_name in model._fields
