from odoo import fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    external_inventory_adjustment_id = fields.Many2one(
        "external.stock.inventory", ondelete="restrict", index=True
    )

    def _get_inventory_move_values(
        self,
        qty,
        location_id,
        location_dest_id,
        package_id=False,
        package_dest_id=False,
    ):
        res = super()._get_inventory_move_values(
            qty, location_id, location_dest_id, package_id, package_dest_id
        )
        if self.external_inventory_adjustment_id:
            res.update(
                {
                    "external_inventory_adjustment_id": self.external_inventory_adjustment_id.id  # noqa: E501
                }
            )
        return res
