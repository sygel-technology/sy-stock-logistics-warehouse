import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-sygel-technology-sy-stock-logistics-warehouse",
    description="Meta package for sygel-technology-sy-stock-logistics-warehouse Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-sale_order_line_multi_warehouse_widget>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
