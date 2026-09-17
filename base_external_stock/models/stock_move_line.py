# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    external_inventory_adjustment_id = fields.Many2one(
        related="move_id.external_inventory_adjustment_id",
        store=True,
    )
