# Copyright 2024 Manuel Regidor <manuel.regidor@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_by_warehouse = fields.Binary(
        compute="_compute_qty_by_warehouse", exportable=False
    )
    display_qty_by_warehouse_widget = fields.Boolean(
        compute="_compute_display_qty_by_warehouse_widget"
    )

    def _compute_qty_to_deliver(self):
        ret_vals = super()._compute_qty_to_deliver()
        for line in self.filtered("allow_sale_multi_warehouse"):
            line.display_qty_widget = False
        return ret_vals

    @api.depends(
        "product_type",
        "qty_delivered",
        "state",
        "move_ids",
        "product_uom",
        "allow_sale_multi_warehouse",
    )
    def _compute_display_qty_by_warehouse_widget(self):
        for line in self:
            display_qty_by_warehouse_widget = False
            if (
                line.allow_sale_multi_warehouse
                and line.product_type == "product"
                and line.product_uom
                and line.qty_to_deliver > 0
                and (
                    line.state in ["draft", "sent"]
                    or (line.state == "sale" and line.move_ids)
                )
            ):
                display_qty_by_warehouse_widget = True
            line.display_qty_by_warehouse_widget = display_qty_by_warehouse_widget

    # Based on _compute_qty_at_date method in sale.order.line
    def _get_qty_by_warehouse_vals(self, warehouse):
        self.ensure_one()
        scheduled_date = self.order_id.commitment_date or self._expected_date()
        moves = self.move_ids | self.env["stock.move"].browse(
            self.move_ids._rollup_move_origs()
        )
        moves = moves.filtered(
            lambda m: m.product_id == self.product_id
            and m.state not in ("cancel", "done")
            and m.warehouse_id == warehouse
        )

        # qty_available_today
        qty_available_today = 0
        for move in moves:
            qty_available_today += move.product_uom._compute_quantity(
                move.reserved_availability, self.product_uom
            )

        # forecast_expected_date
        forecast_expected_date = False
        if moves:
            forecast_expected_date = max(moves.mapped("forecast_expected_date"))

        # free_qty_today
        free_qty_today = 0.0
        if self.state == "sale":
            for move in moves:
                free_qty_today += move.product_id.uom_id._compute_quantity(
                    move.forecast_availability, self.product_uom
                )
        elif self.state in ["draft", "sent"]:
            free_qty_today = self.product_id.with_context(
                to_date=scheduled_date, warehouse=warehouse.id
            ).free_qty

        # virtual_available_at_date
        virtual_available_at_date = self.product_id.with_context(
            to_date=scheduled_date, warehouse=warehouse.id
        ).virtual_available

        # qty_to_deliver
        to_deliver_from_warehouse = (
            sum(
                self.sale_order_line_warehouse_ids.filtered(
                    lambda a: a.warehouse_id == warehouse
                ).mapped("product_uom_qty")
            )
            or 0.0
        )
        # taken from _compute_qty_delivered in sale.order.line in module
        # sale_stock
        qty_delivered = 0.0
        qty_to_deliver = 0.0
        if self.qty_delivered_method == "stock_move":
            outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves()
            for move in outgoing_moves.filtered(lambda a: a.warehouse_id == warehouse):
                if move.state != "done":
                    continue
                qty_delivered += move.product_uom._compute_quantity(
                    move.quantity_done,
                    self.product_uom,
                    rounding_method="HALF-UP",
                )
            for move in incoming_moves.filtered(lambda a: a.warehouse_id == warehouse):
                if move.state != "done":
                    continue
                qty_delivered -= move.product_uom._compute_quantity(
                    move.quantity_done,
                    self.product_uom,
                    rounding_method="HALF-UP",
                )
            qty_to_deliver = to_deliver_from_warehouse - qty_delivered

        # will_be_fulfilled
        if self.state in ["sale", "done"]:
            will_be_fulfilled = free_qty_today >= qty_to_deliver
        else:
            will_be_fulfilled = virtual_available_at_date >= qty_to_deliver

        # forecasted_issue
        forecasted_issue = False
        if (
            self.state in ["draft", "sent"]
            and not will_be_fulfilled
            and not self.is_mto
        ):
            forecasted_issue = True
        elif not will_be_fulfilled or (
            forecast_expected_date and forecast_expected_date > scheduled_date
        ):
            forecasted_issue = True

        # format forecast_expected_date formatted
        forecast_expected_date_str = ""
        lang = self.env.context.get("lang") or "en_US"
        date_format = self.env["res.lang"]._lang_get(lang).date_format
        if forecast_expected_date:
            forecast_expected_date_str = forecast_expected_date.strftime(date_format)

        return {
            "warehouse": warehouse.id,
            "warehouse_name": warehouse.name,
            "qty_available_today": qty_available_today,
            "virtual_available_at_date": virtual_available_at_date,
            "free_qty_today": free_qty_today,
            "qty_to_deliver": qty_to_deliver,
            "will_be_fulfilled": will_be_fulfilled,
            "forecast_expected_date": forecast_expected_date,
            "scheduled_date": scheduled_date,
            "forecast_expected_date_str": forecast_expected_date_str,
            "forecasted_issue": forecasted_issue,
        }

    @api.depends(
        "product_id",
        "product_uom_qty",
        "product_uom",
        "order_id.commitment_date",
        "move_ids",
        "move_ids.forecast_expected_date",
        "move_ids.forecast_availability",
        "sale_order_line_warehouse_ids",
    )
    def _compute_qty_by_warehouse(self):
        for line in self:
            qty_by_warehouse = {}
            warehouses = []
            for warehouse in line.suitable_warehouse_ids:
                warehouses.append(line._get_qty_by_warehouse_vals(warehouse))
            qty_by_warehouse["warehouses"] = warehouses
            forecasted_issue = any(
                warehouse.get("forecasted_issue") for warehouse in warehouses
            )
            qty_by_warehouse["forecasted_issue"] = forecasted_issue
            line.qty_by_warehouse = qty_by_warehouse
