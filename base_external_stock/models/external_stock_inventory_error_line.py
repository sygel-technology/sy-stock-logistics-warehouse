# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ExternalStockInventoryErrorLine(models.Model):
    _name = "external.stock.inventory.error.line"
    _description = "Inventory adjusments of external supplier stock errors"

    external_stock_inventory_id = fields.Many2one(
        string="External Stock Inventory",
        comodel_name="external.stock.inventory",
        ondelete="cascade",
    )

    error_type = fields.Selection(
        selection=[],
    )

    error_msg = fields.Text()
