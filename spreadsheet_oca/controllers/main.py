# Copyright 2024 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
from io import BytesIO
from zipfile import ZipFile

from odoo.http import Controller, content_disposition, request, route


class SpreadsheetDownloadXLSX(Controller):
    @route("/spreadsheet/xlsx", type="http", auth="user", methods=["POST"])
    def download_spreadsheet_xlsx(self, zip_name, files, **kw):
        files = json.loads(files)
        file_bytes = BytesIO()
        with ZipFile(file_bytes, "w") as zip_file:
            for file in files:
                zip_file.writestr(file["path"], file["content"])
        file_content = file_bytes.getvalue()
        return request.make_response(
            file_bytes.getvalue(),
            [
                ("Content-Length", len(file_content)),
                ("Content-Type", "application/vnd.ms-excel"),
                ("X-Content-Type-Options", "nosniff"),
                ("Content-Disposition", content_disposition(zip_name)),
            ],
        )
