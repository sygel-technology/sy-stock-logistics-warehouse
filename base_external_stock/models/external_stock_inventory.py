# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class ExternalStockInventory(models.Model):
    # Inspired in the stock_inventory module
    _name = "external.stock.inventory"
    _description = "Inventory adjusments of external supplier stock"
    _order = "date desc, id desc"
    _inherit = [
        "mail.thread",
    ]

    name = fields.Char(
        required=True,
        default="Inventory",
        string="Inventory Reference",
        readonly=True,
    )

    date = fields.Datetime(
        default=lambda self: fields.Datetime.now(),
        readonly=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
        index=True,
        default=lambda self: self.env.company,
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="in_progress",
        tracking=True,
        required=True,
    )
    config_id = fields.Many2one(
        string="Origin",
        comodel_name="external.stock.inventory.config",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
    )
    supplier_id = fields.Many2one(
        string="External Supplier",
        related="config_id.supplier_id",
        copy=False,
        store=True,
    )
    # data = fields.Text(readonly=True, copy=False)
    error_ids = fields.One2many(
        string="Errors",
        comodel_name="external.stock.inventory.error.line",
        inverse_name="external_stock_inventory_id",
    )
    in_progress_offset = fields.Integer(default=0, readonly=True)
    stock_quant_ids = fields.Many2many(
        "stock.quant",
        string="Inventory Adjustment",
        domain="['|', ('company_id', '=', company_id), ('company_id', '=', False)]",
        readonly=True,
    )
    count_stock_quants = fields.Integer(
        compute="_compute_count_stock_quants", string="# Adjustments"
    )

    count_stock_moves = fields.Integer(
        compute="_compute_count_stock_moves", string="Stock Moves Lines"
    )

    @api.depends("stock_quant_ids")
    def _compute_count_stock_quants(self):
        for rec in self:
            rec.count_stock_quants = len(rec.stock_quant_ids)

    def _compute_count_stock_moves(self):
        group_fname = "external_inventory_adjustment_id"
        group_data = self.env["stock.move.line"].read_group(
            [
                (group_fname, "in", self.ids),
            ],
            [group_fname],
            [group_fname],
        )
        data_by_adj_id = {
            row[group_fname][0]: row.get(f"{group_fname}_count", 0)
            for row in group_data
        }
        for rec in self:
            rec.count_stock_moves = data_by_adj_id.get(rec.id, 0)

    def action_view_inventory_adjustment(self):
        self.ensure_one()
        return self.env["stock.quant"]._get_quants_action(
            [("id", "in", self.stock_quant_ids.ids)]
        )

    def action_view_stock_moves(self):
        self.ensure_one()
        result = self.env["ir.actions.act_window"]._for_xml_id(
            "stock.stock_move_line_action"
        )
        result["domain"] = [("external_inventory_adjustment_id", "=", self.id)]
        result["context"] = {}
        return result

    def external_create_update_quants(self, quant_data):
        # quant_data = {product_id: (product_qty, metadata)}
        product_ids = list(quant_data.keys())
        location = self.location_id
        quant_model = self.env["stock.quant"]
        quants_to_apply = quant_model
        quants_to_create_vals = []

        # 1. Get already existing quants
        existing_quants_domain = [
            ("product_id", "in", product_ids),
            ("location_id", "=", location.id),
            ("lot_id", "=", False),
            ("package_id", "=", False),
            ("owner_id", "=", False),
        ]
        existing_quants = quant_model.search(existing_quants_domain)
        quant_by_product = {q.product_id.id: q for q in existing_quants}

        # 2. Loop products. Update existing quants and prepare vals for new quants
        for product_id in quant_data.keys():
            qty = quant_data[product_id][0]
            quant = quant_by_product.get(product_id, quant_model)
            if quant:
                quant.inventory_quantity = qty
                quant.external_inventory_adjustment_id = self.id
                quants_to_apply |= quant
            else:
                quants_to_create_vals.append(
                    {
                        "location_id": location.id,
                        "product_id": product_id,
                        "inventory_quantity": qty,
                        "external_inventory_adjustment_id": self.id,
                    }
                )

        # 3. Create new quants and apply inventory changes
        if quants_to_create_vals:
            quants_to_apply = quant_model.create(quants_to_create_vals)
        if quants_to_apply:
            quants_to_apply.action_apply_inventory()
        return quants_to_apply

    def action_cancel(self):
        self.filtered(lambda a: a.state == "in_progress").write({"state": "cancel"})
