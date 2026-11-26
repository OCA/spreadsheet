# Copyright 2026 Cloud Lotus
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSpreadsheetSnapshot(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spreadsheet = cls.env["spreadsheet.spreadsheet"].create(
            {"name": "Snapshot compact test"}
        )
        cls.Revision = cls.env["spreadsheet.oca.revision"]

    def _create_remote_revision(self, server_revision_id, next_revision_id):
        return self.Revision.create(
            {
                "model": self.spreadsheet._name,
                "res_id": self.spreadsheet.id,
                "type": "REMOTE_REVISION",
                "client_id": "client-1",
                "server_revision_id": server_revision_id,
                "next_revision_id": next_revision_id,
                "commands": json.dumps(
                    {
                        "type": "REMOTE_REVISION",
                        "commands": [{"type": "UPDATE_CELL", "sheetId": "sheet1"}],
                    }
                ),
            }
        )

    def test_snapshot_persists_raw_and_drops_history(self):
        self._create_remote_revision("START_REVISION", "rev-1")
        self._create_remote_revision("rev-1", "rev-2")
        self.assertEqual(len(self.spreadsheet.spreadsheet_revision_ids), 2)
        snapshot_data = {
            "version": 1,
            "sheets": [{"id": "sheet1", "name": "Sheet1"}],
            "revisionId": "snap-1",
        }
        accepted = self.spreadsheet.send_spreadsheet_message(
            {
                "type": "SNAPSHOT",
                "serverRevisionId": "rev-2",
                "nextRevisionId": "snap-1",
                "data": snapshot_data,
            }
        )
        self.assertTrue(accepted)
        self.assertFalse(self.spreadsheet.spreadsheet_revision_ids)
        self.assertEqual(self.spreadsheet.spreadsheet_raw["revisionId"], "snap-1")
        payload = self.spreadsheet.get_spreadsheet_data()
        self.assertEqual(payload["spreadsheet_raw"]["revisionId"], "snap-1")
        self.assertEqual(payload["revisions"], [])

    def test_legacy_snapshot_revision_skips_older_history_on_open(self):
        """Pre-fix SNAPSHOT rows stored the workbook in commands and kept history."""
        old_rev = self._create_remote_revision("START_REVISION", "rev-1")
        snapshot_data = {
            "version": 1,
            "sheets": [{"id": "sheet1", "name": "Compacted"}],
            "revisionId": "snap-legacy",
        }
        self.Revision.create(
            {
                "model": self.spreadsheet._name,
                "res_id": self.spreadsheet.id,
                "type": "SNAPSHOT",
                "server_revision_id": "rev-1",
                "next_revision_id": "snap-legacy",
                "commands": json.dumps(
                    {
                        "type": "SNAPSHOT",
                        "data": snapshot_data,
                    }
                ),
            }
        )
        later = self._create_remote_revision("snap-legacy", "rev-after")
        payload = self.spreadsheet.get_spreadsheet_data()
        self.assertEqual(payload["spreadsheet_raw"]["revisionId"], "snap-legacy")
        self.assertEqual(len(payload["revisions"]), 1)
        self.assertEqual(payload["revisions"][0]["nextRevisionId"], "rev-after")
        loaded_ids = {rev["nextRevisionId"] for rev in payload["revisions"]}
        self.assertNotIn(old_rev.next_revision_id, loaded_ids)
        self.assertIn(later.next_revision_id, loaded_ids)

    def test_write_spreadsheet_raw_still_unlinks_revisions(self):
        self._create_remote_revision("START_REVISION", "rev-1")
        self.spreadsheet.write(
            {
                "spreadsheet_raw": {
                    "version": 1,
                    "sheets": [],
                    "revisionId": "START_REVISION",
                }
            }
        )
        self.assertFalse(self.spreadsheet.spreadsheet_revision_ids)

    def test_snapshot_without_data_is_rejected(self):
        accepted = self.spreadsheet.send_spreadsheet_message(
            {
                "type": "SNAPSHOT",
                "serverRevisionId": "START_REVISION",
                "nextRevisionId": "snap-1",
            }
        )
        self.assertFalse(accepted)
        self.assertFalse(self.spreadsheet.spreadsheet_revision_ids)

    def test_snapshot_revision_id_mismatch_raises(self):
        with self.assertRaises(ValueError):
            self.spreadsheet.send_spreadsheet_message(
                {
                    "type": "SNAPSHOT",
                    "serverRevisionId": "START_REVISION",
                    "nextRevisionId": "snap-1",
                    "data": {"sheets": [], "revisionId": "other-id"},
                }
            )
