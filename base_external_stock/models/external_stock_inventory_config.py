# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import sys
from datetime import timedelta

from odoo import _, api, fields, models

DEFAULT_BATCH_SIZE = 5000


class ExternalStockInventoryConfig(models.Model):
    _name = "external.stock.inventory.config"
    _description = "Config of auto inventory adjusments of external supplier stock"

    name = fields.Char()
    state = fields.Selection(
        selection=[
            ("disabled", "Disabled"),
            ("enabled", "Enabled"),
            ("test", "Test"),
        ],
        required=True,
        default="disabled",
    )
    supplier_id = fields.Many2one(
        comodel_name="res.partner",
        ondelete="restrict",
        domain=[("parent_id", "=", False)],
    )
    location_id = fields.Many2one(
        string="Location",
        comodel_name="stock.location",
        ondelete="restrict",
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', company_id), ('company_id', '=', False)]",  # noqa: E501
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
        default=lambda self: self.env.company,
        required=True,
    )
    stock_inventory_ids = fields.One2many(
        string="Created Inventory Adjustments",
        comodel_name="external.stock.inventory",
        inverse_name="config_id",
        domain="[('usage', '=', 'internal')]",
    )
    count_stock_inventory = fields.Integer(compute="_compute_count_stock_inventory")
    manual_method = fields.Selection(
        selection=[
            ("sync", "Syncronous"),
            ("async", "Asyncronous"),
        ],
        help="Method that will be executed when manually creating an adjustment",
        required=True,
        default="async",
    )
    product_limit = fields.Integer(
        default=0,
        help="If set, the adjustment will only get those number of products "
        "from the external data source",
    )
    start_offset = fields.Integer(
        default=0,
        help="If set, the adjustment will ignore the first products "
        "of the external data source",
    )
    batch_size = fields.Integer(
        default=DEFAULT_BATCH_SIZE,
        help="Number of products that will be fetched from "
        "the external data source and imported at once",
    )

    @api.depends("stock_inventory_ids")
    def _compute_count_stock_inventory(self):
        for rec in self:
            rec.count_stock_inventory = len(rec.stock_inventory_ids)

    def _get_batch_size(self):
        self.ensure_one()
        return self.batch_size or DEFAULT_BATCH_SIZE

    def _get_external_stock_data_batch_enabled(self):
        """This method must be implemented by modules
        that want to connect to a specific webservice

        Returns the data of the products to import,
        a list of errors, and returns if the batch is the last one

        Data format {
            product_id: (stock_qty, metadata_dict)
        }
        """
        raise NotImplementedError()

    def _get_external_stock_data_batch_test(self, offset=0):
        data = {
            self.env["product.product"]
            .search([("type", "=", "product")], limit=1)
            .id: [10, {}]
        }
        errors = self.env["external.stock.inventory.error.line"].create(
            {"error_msg": "Test Error Example"}
        )
        finished = offset
        return data, errors, finished

    def _get_external_stock_data_batch(self, offset=0):
        if self.state == "test":
            return self._get_external_stock_data_batch_test(offset)
        elif self.state == "enabled":
            return self._get_external_stock_data_batch_enabled(offset)

    def _get_external_stock_data(self):
        """Returns the data of the products to import, and a list of errors

        Data format {
            product_id: (stock_qty, metadata_dict)
        }
        """
        batch_size = self._get_batch_size()
        offset = max(self.start_offset, 0)
        limit = self.product_limit + offset if self.product_limit else sys.maxsize
        finished = False
        total_data = {}
        total_errors = self.env["external.stock.inventory.error.line"]
        while not finished and offset < limit:
            data, errors, finished = self._get_external_stock_data_batch(offset)
            offset += batch_size
            total_data.update(data)
            total_errors |= errors
        return total_data, total_errors

    def _get_external_stock_inventory_vals(self, **extra_vals):
        vals = {
            "state": "in_progress",
            "config_id": self.id,
            "location_id": self.location_id.id,
            "company_id": self.company_id.id,
        }
        if extra_vals:
            vals.update(extra_vals)
        return vals

    def _sync_update_external_stock(self):
        self.ensure_one()
        data, errors = self._get_external_stock_data()
        stock_inventory = self.env["external.stock.inventory"].create(
            self._get_external_stock_inventory_vals()
        )
        quants = stock_inventory.external_create_update_quants(data)
        stock_inventory.write(
            {
                "stock_quant_ids": [(6, 0, quants.ids)],
                "state": "done",
                # "data": data,
                "error_ids": [(6, 0, errors.ids)],
            }
        )
        return self._view_stock_inventory(stock_inventory)

    def _update_external_stock_job(self, inventory, offset=0):
        if inventory.state != "in_progress":
            return
        offset = offset if offset else inventory.in_progress_offset
        data, errors, finished = self._get_external_stock_data_batch(offset)
        quants = inventory.external_create_update_quants(data)
        inventory.write(
            {
                "stock_quant_ids": [(4, quant.id) for quant in quants],
                "error_ids": [(4, error.id) for error in errors],
            }
        )
        if finished:
            inventory.write(
                {
                    "state": "done",
                }
            )
        else:
            batch_size = self._get_batch_size()
            offset += batch_size
            inventory.write({"in_progress_offset": offset})
            self.env["ir.cron.trigger"].sudo().create(
                {
                    "cron_id": self.env.ref(
                        "base_external_stock.cron_external_stock_queue"
                    ).id,
                    "call_at": fields.Datetime.now(),
                }
            )

    def _async_update_external_stock(self):
        stock_inventory = self.env["external.stock.inventory"].create(
            self._get_external_stock_inventory_vals()
        )
        self._update_external_stock_job(stock_inventory)
        return self._view_stock_inventory(stock_inventory)

    def update_external_stock(self):
        if self.manual_method == "sync":
            res = self._sync_update_external_stock()
        else:
            res = self._async_update_external_stock()
        return res

    def cron_update_external_stock_queue(self, block_hours=24):
        inventory_id = self.env["external.stock.inventory"].search(
            [("state", "=", "in_progress")], limit=1
        )
        if inventory_id:
            if inventory_id.create_date <= fields.Datetime.now() - timedelta(
                hours=block_hours
            ):
                inventory_id.action_cancel()
            else:
                config = inventory_id.config_id
                config._update_external_stock_job(inventory_id)

    @api.model
    def _view_stock_inventory(self, stock_inventory):
        return {
            "name": _("Inventory Adjustment"),
            "type": "ir.actions.act_window",
            "res_model": "external.stock.inventory",
            "view_mode": "form",
            "res_id": stock_inventory.id,
        }

    def action_view_inventory_ids(self):
        return {
            "name": _("External Inventory Adjustment"),
            "type": "ir.actions.act_window",
            "res_model": "external.stock.inventory",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.stock_inventory_ids.ids)],
        }

    def _test_connection(self):
        """This method must be implemented by modules
        that want to connect to a specific webservice

        Returns True or False
        """
        if self.state == "test":
            return True
        else:
            raise NotImplementedError()

    def test_connection(self):
        self.ensure_one()
        test_ok = self._test_connection()
        if test_ok:
            res = {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Test results"),
                    "message": _("Everything went ok. "),
                    "type": "success",
                    "sticky": False,
                },
            }
        else:
            res = {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Test results"),
                    "message": _("An error happened during the connection test"),
                    "type": "danger",
                    "sticky": False,
                },
            }
        return res
