The SpreadsheetUploadMixin mixin can be used when a model needs the ability to upload an XLSX file and automatically create or link a spreadsheet document in Odoo.
It allows users to manage spreadsheets directly from the form view of a record.

Let's consider the following models:

.. code-block:: python

    class MyModelA(models.Model):
        _name = "my.model.a"
        _inherit = ["spreadsheet.upload.mixin"]

By inheriting from spreadsheet.upload.mixin, the model gains the following:

- upload_file: binary field to upload an XLSX file.

- file_name: helper field to store the filename.

- spreadsheet_id: link to the generated spreadsheet.spreadsheet record.

- action_create_spreadsheet(): creates a new spreadsheet from the uploaded file.

- action_open_spreadsheet(): opens the linked spreadsheet directly from the form.

A corresponding form view can then be defined to expose these fields and buttons:

.. code-block:: xml

    <record id="my_model_a_form_view" model="ir.ui.view">
        <field name="name">my.model.a.form.view</field>
        <field name="model">my.model.a</field>
        <field name="arch" type="xml">
            <form>
                <sheet>
                    <group>
                        <div class="o_row">
                            <label for="spreadsheet_id"
                                attrs="{'invisible': [('spreadsheet_id', '=', False)]}" />
                            <div attrs="{'invisible': [('spreadsheet_id', '=', False)]}"
                                style="margin-bottom: 15px;">
                                <field name="spreadsheet_id"
                                    readonly="1"
                                    class="oe_inline"
                                    style="margin-right:7px;"/>
                                <button name="action_open_spreadsheet"
                                        type="object"
                                        string="Edit"
                                        icon="fa-pencil"
                                        class="btn btn-primary"/>
                            </div>
                        </div>

                        <div class="o_row">
                            <label for="upload_file"
                                class="o_form_label"
                                style="font-weight: bold;"
                                attrs="{'invisible': ['|', ('upload_file', '=', False), ('spreadsheet_id', '!=', False)]}"/>
                            <field name="upload_file"
                                filename="file_name"
                                nolabel="1"
                                attrs="{'invisible': [('spreadsheet_id', '!=', False)]}"/>
                            <div style="margin-right: 400px; margin-bottom: 15px;">
                                <button name="action_create_spreadsheet"
                                        type="object"
                                        string="Create Spreadsheet From File"
                                        class="btn btn-primary"
                                        attrs="{'invisible': ['|', ('upload_file', '=', False), ('spreadsheet_id', '!=', False)]}"/>
                            </div>
                        </div>

                        <field name="file_name" invisible="1"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

By using this mixin and view definition, you can upload an XLSX file from any record form, create a linked Odoo Spreadsheet, and open it for editing directly from the form view.