# Copyright 2023 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import models
from odoo.exceptions import AccessDenied


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _build_bus_channel_list(self, channels):
        """
        With this change we are adding an extra layer of security.
        Without it, any user was able to sniff how all happened using something like:

            const any_spreadsheet_id = 1234;
            const channel = "spreadsheet_oca;spreadsheet.spreadsheet" +
                            ";" + any_spreadsheet_id;
            bus_service.addChannel(channel);
            bus_service.addEventListener(
                "spreadsheet_oca",
                (message) => /* every revision arrives here */
            )

        """
        if self.env.uid:
            # Do not alter original list.
            channels = list(channels)
            for channel in channels:
                if isinstance(channel, str):
                    match = re.match(r"spreadsheet_oca;(\w+(?:\.\w+)*);(\d+)", channel)
                    if match:
                        model_name = match[1]
                        res_id = int(match[2])

                        # Verify access to the edition channel.
                        if not self.env.user._is_internal():
                            raise AccessDenied()

                        if not self.env["ir.model.access"].check(
                            model_name, "read", raise_exception=False
                        ):
                            continue
                        # If user don't have access to the model, we don't even try to read

                        document = self.env[model_name].search(
                            [("id", "=", res_id)], limit=1
                        )
                        # We do a search in order to apply the access rules.
                        # We just need to ensure that the user can read it

                        if not document.exists():
                            continue

                        channels.append(
                            (
                                self.env.registry.db_name,
                                "spreadsheet_oca",
                                model_name,
                                res_id,
                            )
                        )
        return super()._build_bus_channel_list(channels)
