import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-spreadsheet",
    description="Meta package for oca-spreadsheet Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-spreadsheet_dashboard_oca>=16.0dev,<16.1dev',
        'odoo-addon-spreadsheet_oca>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
