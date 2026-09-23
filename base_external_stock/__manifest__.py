# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Base External Stock",
    "summary": "Base to sync stock data of suppliers from an external webservice",
    "version": "17.0.1.0.0",
    "category": "Stock",
    "website": "https://github.com/sygel-technology/sy-stock-logistics-warehouse",
    "author": "Sygel",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "purchase_stock",
    ],
    "data": [
        "data/ir_cron_data.xml",
        "security/ir.model.access.csv",
        "views/external_stock_inventory_config_views.xml",
        "views/external_stock_inventory_error_line_views.xml",
        "views/external_stock_inventory_views.xml",
        "views/res_partner_views.xml",
        "views/menuitems.xml",
    ],
}
