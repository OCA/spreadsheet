from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Renamed field data to spreadsheet_binary_data in V17
    openupgrade.rename_fields(
        env,
        [
            (
                "spreadsheet.spreadsheet",
                "spreadsheet_spreadsheet",
                "data",
                "spreadsheet_binary_data",
            ),
        ],
    )
