# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    external_inventory_adjustment_id = fields.Many2one(
        "external.stock.inventory", ondelete="restrict", index=True
    )
