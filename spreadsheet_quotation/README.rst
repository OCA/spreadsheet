.. image:: https://odoo-community.org/readme-banner-image
   :target: https://odoo-community.org/get-involved?utm_source=readme
   :alt: Odoo Community Association

===============================
Spreadsheet Quotation Calculator
===============================

|badge1| |badge2| |badge3| |badge4| |badge5|

.. |badge1| image:: https://img.shields.io/badge/maturity-Alpha-red.png
    :target: https://odoo-community.org/page/development-status
    :alt: Alpha
.. |badge2| image:: https://img.shields.io/badge/license-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-OCA%2Fspreadsheet-lightgray.png?logo=github
    :target: https://github.com/OCA/spreadsheet/tree/18.0/spreadsheet_quotation
    :alt: OCA/spreadsheet
.. |badge4| image:: https://img.shields.io/badge/weblate-Translate%20me-F47D42.png
    :target: https://translation.odoo-community.org/projects/spreadsheet-18-0/spreadsheet-18-0-spreadsheet_quotation
    :alt: Translate me on Weblate
.. |badge5| image:: https://img.shields.io/badge/runboat-Try%20me-875A7B.png
    :target: https://runboat.odoo-community.org/builds?repo=OCA/spreadsheet&target_branch=18.0
    :alt: Try me on Runboat

This module allows linking spreadsheet calculators to quotation templates
in Odoo. When a sale order is created from a template that has a
calculator, a copy of the spreadsheet is automatically assigned to the
order with a pre-configured global filter so the ``ODOO.LIST`` formulas
display only that order's lines.

The spreadsheet calculator is built on top of ``spreadsheet_oca`` and
uses ``ODOO.LIST`` formulas to display sale order line data such as
product, quantity, and unit price. A Field Sync side panel lets users map
spreadsheet columns to sale order line fields and push calculated values
back to the quotation.

**Table of contents**

.. contents::
   :local:

Installation
============

This module requires:

- ``spreadsheet_oca`` from the OCA spreadsheet repository
- ``sale_management`` from Odoo core addons

Usage
=====

Setting up a quotation calculator
---------------------------------

1. Go to **Sales > Configuration > Quotation Templates**.
2. Open or create a quotation template.
3. Click **Create Calculator** next to the quotation calculator field.
4. Set a name and the initial number of rows in the wizard.
5. Customize the spreadsheet and save it.

Using the calculator on a sale order
------------------------------------

1. Create a new quotation and select a template with a calculator.
2. Use the **Calculator** smart button to open the spreadsheet.
3. Edit values in the spreadsheet.
4. Use **Field Sync** to map columns to sale order line fields.
5. Save the spreadsheet to sync values back to the sale order.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/spreadsheet/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us to smash it by providing detailed and welcomed
`feedback <https://github.com/OCA/spreadsheet/issues/new?body=module:%20spreadsheet_quotation%0Aversion:%2018.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Authors
-------

* Odoo Community Association (OCA)
* Cloud Lotus

Contributors
------------

* OCA Contributors

Maintainers
-----------

This module is maintained by the OCA.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

This module is part of the `OCA/spreadsheet <https://github.com/OCA/spreadsheet/tree/18.0/spreadsheet_quotation>`_ project on GitHub.

You are welcome to contribute. To learn how please visit
https://odoo-community.org/page/Contribute.
