# Copyright 2024 Manuel Regidor <manuel.regidor@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import fields

from odoo.addons.sale_order_line_multi_warehouse.tests.test_so_line_multiwarehouse import (  # noqa: E501
    TestSOLineMultiwarehouse,
)


class TestSOLineMultiwarehouse(TestSOLineMultiwarehouse):
    # Distribution of products in warehouses
    QUANTITIES = {
        "YourCompany": {
            "Product-1": 5,
            "Product-2": 8,
        },
        "Alternative Warehouse-1": {
            "Product-1": 6,
            "Product-2": 9,
        },
        "Alternative Warehouse-2": {
            "Product-1": 7,
            "Product-2": 10,
        },
    }

    # Distribution of quantity in used order line
    SPLIT_QTY = {
        "Product-1": {
            "YourCompany": 1,
            "Alternative Warehouse-1": 1,
            "Alternative Warehouse-2": 1,
        },
        "Product-2": {
            "YourCompany": 2,
            "Alternative Warehouse-1": 2,
            "Alternative Warehouse-2": 1,
        },
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def replenish_qty(self, product, qty, warehouse, date=False):
        replenish_wizard = self.env["product.replenish"].create(
            {
                "product_id": product.id,
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_uom_id": product.uom_id.id,
                "quantity": qty,
                "warehouse_id": warehouse.id,
                "date_planned": date,
            }
        )
        replenish_wizard.launch_replenishment()

    def test_display_widget_draft(self):
        sale = self.create_sale_order()
        self.assertEqual(sale.state, "draft")
        for line in sale.order_line:
            self.assertTrue(line.display_qty_by_warehouse_widget)

    def test_display_widget_confirmed(self):
        sale = self.create_sale_order()
        sale.action_confirm()
        self.assertTrue(sale.state in ["sale", "done"])
        for line in sale.order_line:
            self.assertTrue(line.display_qty_by_warehouse_widget)

    def test_warehouse_qty_draft(self):
        sale = self.create_sale_order()
        self.split_order_lines(sale)

        # product_1 split in warehouses
        #   1u. -> warehouse
        #   1u. -> alternative_warehouse_1
        #   1u. -> anternative_warehouse_2

        # product_2 split in warehouses
        #   2u. -> warehouse
        #   2u. -> alternative_warehouse_1
        #   1u. -> anternative_warehouse_2

        for line in sale.order_line:
            warehouses = line.qty_by_warehouse.get("warehouses")
            forecasted_issue = line.qty_by_warehouse.get("forecasted_issue")
            self.assertFalse(forecasted_issue)
            for warehouse in warehouses:
                values = self.QUANTITIES.get(warehouse["warehouse_name"])
                self.assertTrue(values)
                self.assertEqual(
                    values.get(line.product_id.name),
                    warehouse["virtual_available_at_date"],
                )
                self.assertEqual(
                    values.get(line.product_id.name), warehouse["free_qty_today"]
                )

        # 5 extra units of product_1 in warehouse available in 7 days
        self.replenish_qty(
            self.product_1, 5, self.warehouse, datetime.now() + timedelta(days=7)
        )

        # 5 extra units of product_1 in alternative_warehouse_1 available in 7 days
        self.replenish_qty(
            self.product_1,
            5,
            self.alternative_warehouse_1,
            datetime.now() + timedelta(days=7),
        )

        # 5 extra units of product_1 in alternative_warehouse_2 available in 7 days
        self.replenish_qty(
            self.product_1,
            5,
            self.alternative_warehouse_2,
            datetime.now() + timedelta(days=7),
        )

        # 5 extra units of product_1 in warehouse available in 7 days
        self.replenish_qty(
            self.product_2, 5, self.warehouse, datetime.now() + timedelta(days=7)
        )

        # 5 extra units of product_1 in alternative_warehouse_1 available in 7 days
        self.replenish_qty(
            self.product_2,
            5,
            self.alternative_warehouse_1,
            datetime.now() + timedelta(days=7),
        )

        # 5 extra units of product_1 in alternative_warehouse_2 available in 7 days
        self.replenish_qty(
            self.product_2,
            5,
            self.alternative_warehouse_2,
            datetime.now() + timedelta(days=7),
        )

        sale.write({"commitment_date": datetime.now() + timedelta(days=10)})

        for line in sale.order_line:
            warehouses = line.qty_by_warehouse.get("warehouses")
            forecasted_issue = line.qty_by_warehouse.get("forecasted_issue")
            self.assertFalse(forecasted_issue)
            for warehouse in warehouses:
                values = self.QUANTITIES.get(warehouse["warehouse_name"])
                self.assertTrue(values)
                self.assertEqual(
                    values.get(line.product_id.name) + 5,
                    warehouse["virtual_available_at_date"],
                )
                self.assertEqual(
                    values.get(line.product_id.name), warehouse["free_qty_today"]
                )

        # Each line of the sale order is increased 20 units
        for line in sale.order_line:
            line.write({"product_uom_qty": line.product_uom_qty + 20})
            forecasted_issue = line.qty_by_warehouse.get("forecasted_issue")
            self.assertTrue(forecasted_issue)

        # 20 extra units of product_1 in warehouse available in 8 days
        self.replenish_qty(
            self.product_1, 20, self.warehouse, datetime.now() + timedelta(days=8)
        )

        # 20 extra units of product_1 in alternative_warehouse_1 available in 8 days
        self.replenish_qty(
            self.product_1,
            20,
            self.alternative_warehouse_1,
            datetime.now() + timedelta(days=7),
        )

        # 20 extra units of product_1 in alternative_warehouse_2 available in 8 days
        self.replenish_qty(
            self.product_1,
            20,
            self.alternative_warehouse_2,
            datetime.now() + timedelta(days=7),
        )

        # 20 extra units of product_2 in warehouse available in 8 days
        self.replenish_qty(
            self.product_2, 20, self.warehouse, datetime.now() + timedelta(days=8)
        )

        # 20 extra units of product_2 in alternative_warehouse_1 available in 8 days
        self.replenish_qty(
            self.product_2,
            20,
            self.alternative_warehouse_1,
            datetime.now() + timedelta(days=7),
        )

        # 20 extra units of product_2 in alternative_warehouse_2 available in 8 days
        self.replenish_qty(
            self.product_2,
            20,
            self.alternative_warehouse_2,
            datetime.now() + timedelta(days=7),
        )

        for line in sale.order_line:
            line._compute_qty_by_warehouse()
            warehouses = line.qty_by_warehouse.get("warehouses")
            forecasted_issue = line.qty_by_warehouse.get("forecasted_issue")
            self.assertFalse(forecasted_issue)
            for warehouse in warehouses:
                values = self.QUANTITIES.get(warehouse["warehouse_name"])
                self.assertTrue(values)
                self.assertEqual(
                    values.get(line.product_id.name) + 25,
                    warehouse["virtual_available_at_date"],
                )
                self.assertEqual(
                    values.get(line.product_id.name), warehouse["free_qty_today"]
                )

        sale.write({"commitment_date": datetime.now()})

        for line in sale.order_line:
            warehouses = line.qty_by_warehouse.get("warehouses")
            forecasted_issue = line.qty_by_warehouse.get("forecasted_issue")
            self.assertTrue(forecasted_issue)
            for warehouse in warehouses:
                values = self.QUANTITIES.get(warehouse["warehouse_name"])
                self.assertTrue(values)
                self.assertEqual(
                    values.get(line.product_id.name),
                    warehouse["virtual_available_at_date"],
                )
                self.assertEqual(
                    values.get(line.product_id.name), warehouse["free_qty_today"]
                )

    def test_warehouse_qty_confirmed(self):
        sale = self.create_sale_order()
        self.split_order_lines(sale)
        sale.action_confirm()

        # product_1 split in warehouses
        #   1u. -> warehouse
        #   1u. -> alternative_warehouse_1
        #   1u. -> anternative_warehouse_2

        # product_2 split in warehouses
        #   2u. -> warehouse
        #   2u. -> alternative_warehouse_1
        #   1u. -> anternative_warehouse_2

        for line in sale.order_line:
            warehouses = line.qty_by_warehouse.get("warehouses")
            forecasted_issue = line.qty_by_warehouse.get("forecasted_issue")
            self.assertFalse(forecasted_issue)
            for warehouse in warehouses:
                qty = self.SPLIT_QTY[line.product_id.name][warehouse["warehouse_name"]]
                self.assertTrue(qty)
                self.assertEqual(qty, warehouse["qty_available_today"])
                self.assertEqual(qty, warehouse["free_qty_today"])

        # Each line of the sale order is increased 20 units
        for line in sale.order_line:
            line.write({"product_uom_qty": line.product_uom_qty + 20})

        for line in sale.order_line:
            forecasted_issue = line.qty_by_warehouse.get("forecasted_issue")
            self.assertTrue(forecasted_issue)
            warehouses = line.qty_by_warehouse.get("warehouses")
            for warehouse in warehouses:
                warehouse_line = line.sale_order_line_warehouse_ids.filtered(
                    lambda a, w=warehouse: w["warehouse"] == a.warehouse_id.id
                )
                self.assertTrue(warehouse_line)
                if warehouse.get("will_be_fulfilled"):
                    self.assertEqual(
                        warehouse_line.product_uom_qty, warehouse["qty_available_today"]
                    )
                    self.assertEqual(
                        warehouse_line.product_uom_qty, warehouse["free_qty_today"]
                    )
                else:
                    self.assertEqual(
                        warehouse_line.product_uom_qty,
                        warehouse["qty_available_today"]
                        - warehouse["virtual_available_at_date"],
                    )
                    self.assertEqual(
                        warehouse_line.product_uom_qty,
                        warehouse["free_qty_today"]
                        - warehouse["virtual_available_at_date"],
                    )

        replenish_date = fields.Datetime.now() + timedelta(days=7)
        # 20 extra units of product_1 in warehouse available in 8 days
        self.replenish_qty(self.product_1, 20, self.warehouse, replenish_date)
        # 20 extra units of product_2 in warehouse available in 8 days
        self.replenish_qty(self.product_2, 20, self.warehouse, replenish_date)

        # It is necessary to recompute the forecast_information field in moves
        sale.order_line.mapped("move_ids")._compute_forecast_information()

        for line in sale.order_line:
            forecasted_issue = line.qty_by_warehouse.get("forecasted_issue")
            self.assertTrue(forecasted_issue)
            warehouses = line.qty_by_warehouse.get("warehouses")
            for warehouse in warehouses:
                self.assertTrue(warehouse["will_be_fulfilled"])
                warehouse_line = line.sale_order_line_warehouse_ids.filtered(
                    lambda a, w=warehouse: w["warehouse"] == a.warehouse_id.id
                )
                self.assertTrue(warehouse_line)
                if warehouse.get("warehouse") == self.warehouse.id:
                    self.assertEqual(
                        replenish_date, warehouse["forecast_expected_date"]
                    )
                    self.assertTrue(warehouse["forecast_expected_date_str"])
                else:
                    self.assertEqual(
                        warehouse_line.product_uom_qty, warehouse["qty_available_today"]
                    )
                    self.assertEqual(
                        warehouse_line.product_uom_qty, warehouse["free_qty_today"]
                    )
                    self.assertFalse(warehouse["forecast_expected_date"])
                    self.assertFalse(warehouse["forecast_expected_date_str"])

        # Commitment date is moved forward, so quantity will be repplenished
        # by then
        sale.write({"commitment_date": datetime.now() + timedelta(days=8)})

        for line in sale.order_line:
            forecasted_issue = line.qty_by_warehouse.get("forecasted_issue")
            self.assertFalse(forecasted_issue)
            warehouses = line.qty_by_warehouse.get("warehouses")
            for warehouse in warehouses:
                warehouse_line = line.sale_order_line_warehouse_ids.filtered(
                    lambda a, w=warehouse: w["warehouse"] == a.warehouse_id.id
                )
                self.assertTrue(warehouse_line)
                if warehouse.get("warehouse") == self.warehouse.id:
                    self.assertEqual(
                        replenish_date, warehouse["forecast_expected_date"]
                    )
                    self.assertTrue(warehouse["forecast_expected_date_str"])
                    self.assertEqual(
                        self.QUANTITIES.get(warehouse["warehouse_name"]).get(
                            line.product_id.name
                        ),
                        warehouse["qty_available_today"],
                    )
                else:
                    self.assertEqual(
                        warehouse_line.product_uom_qty, warehouse["qty_available_today"]
                    )
                    self.assertEqual(
                        warehouse_line.product_uom_qty, warehouse["free_qty_today"]
                    )
                    self.assertFalse(warehouse["forecast_expected_date"])
                    self.assertFalse(warehouse["forecast_expected_date_str"])
