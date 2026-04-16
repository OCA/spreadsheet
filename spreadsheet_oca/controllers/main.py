# Copyright 2024 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json

from odoo.http import Controller, request, route
from odoo.http.stream import content_disposition


class SpreadsheetDownloadXLSX(Controller):
    @route("/spreadsheet/xlsx", type="http", auth="user", methods=["POST"])
    def download_spreadsheet_xlsx(self, zip_name, files, **kw):
        if hasattr(files, "read"):
            files = files.read().decode("utf-8")
        files = json.loads(files)
        file_content = request.env["spreadsheet.mixin"]._zip_xslx_files(files)
        return request.make_response(
            file_content,
            [
                ("Content-Length", len(file_content)),
                ("Content-Type", "application/vnd.ms-excel"),
                ("X-Content-Type-Options", "nosniff"),
                ("Content-Disposition", content_disposition(zip_name)),
            ],
        )
