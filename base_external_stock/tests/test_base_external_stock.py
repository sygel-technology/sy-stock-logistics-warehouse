# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestBaseExternalStock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier = cls.env["res.partner"].create({"name": "External Supplier"})
        cls.location = cls.env["stock.location"].create(
            {"name": "External Supplier", "usage": "internal"}
        )
        cls.external_stock_inventory_config = cls.env[
            "external.stock.inventory.config"
        ].create(
            {
                "name": "External Supplier",
                "state": "test",
                "supplier_id": cls.supplier.id,
                "location_id": cls.location.id,
                "batch_size": 1,
            }
        )

    def test_external_stock_inventory_method_sync(self):
        self.external_stock_inventory_config.manual_method = "sync"
        self.external_stock_inventory_config.update_external_stock()

    def test_external_stock_inventory_method_async(self):
        self.external_stock_inventory_config.manual_method = "async"
        self.external_stock_inventory_config.update_external_stock()
        self.external_stock_inventory_config.cron_update_external_stock_queue()

    def test_external_stock_inventory_config_test(self):
        self.external_stock_inventory_config.test_connection()
