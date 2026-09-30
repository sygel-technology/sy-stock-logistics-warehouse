# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    external_stock_inventory_ids = fields.One2many(
        string="External Inventory Adjustments",
        comodel_name="external.stock.inventory",
        inverse_name="supplier_id",
    )
    count_external_stock_inventory = fields.Integer(
        compute="_compute_count_external_stock_inventory"
    )

    @api.depends("external_stock_inventory_ids")
    def _compute_count_external_stock_inventory(self):
        for rec in self:
            rec.count_external_stock_inventory = len(rec.external_stock_inventory_ids)

    def action_view_external_inventory_ids(self):
        return {
            "name": _("External Inventory Adjustment"),
            "type": "ir.actions.act_window",
            "res_model": "external.stock.inventory",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.external_stock_inventory_ids.ids)],
        }
