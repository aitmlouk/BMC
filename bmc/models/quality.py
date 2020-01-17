# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
import datetime
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES


class QualityCheck(models.Model):
    _inherit = "quality.check"

    chimique_comment = fields.Text(string="Commentaire analyse chimique")
    control_comment = fields.Text(string="Commentaire contrôle visuel")
    devise_id = fields.Many2one('res.currency', string="Devise")

    dir_validation_date = fields.Date(string="Date validation direction",
                                      readonly=True)
    resp_qu_validation_date = fields.Date(string="Date validation responsable qualité",
                                          readonly=True)
    resp_st_validation_date = fields.Date(string="Date validation responsable stock",
                                          readonly=True)
    resp_tri_validation_date = fields.Date(string="Date validation responsable Tri",
                                           readonly=True)
    picture_1 = fields.Binary(string="Image")
    picture_2 = fields.Binary(string="Image")
    direction_id = fields.Many2one('res.users', string="Direction", readonly=True)
    tri_resp_id = fields.Many2one('res.users', string="Responsable Tri", readonly=True)
    stock_resp_id = fields.Many2one('res.users', string="Responsable stock", readonly=True)
    quality_resp_id = fields.Many2one('res.users', string="Responsable quality", readonly=True)
    scrap_id = fields.Many2one('bmc.scrap', string="Qualité ferraille")
    tri_type_id = fields.Many2one('tri.type', string="Type de Tri")
    uom_id = fields.Many2one('uom.uom', string="Unité de mesure", readonly=False)
    direction = fields.Text(string="Direction", readonly=True)
    tri_resp = fields.Text(string="Responsable Tri", readonly=True)
    stock_resp = fields.Text(string="Responsable stock", readonly=True)
    quality_resp = fields.Text(string="Responsable quality", readonly=True)
    ticket_number = fields.Integer(related='picking_id.ticket_number', string="Numéro de ticket", readonly=True)
    days_number = fields.Integer(string="Objectif nombre de jours de tri")
    purchase_order_id = fields.Many2one('purchase.order', string="Bon de commande",
                                        readonly=True)
    purchase_date = fields.Datetime(string="Commande validée le", readonly=True)
    received_date = fields.Datetime(string="Réception Commande", readonly=True)
    test_type_id = fields.Many2one(
        'quality.point.test_type', 'Test Type',
        required=False)
    supplier_id = fields.Many2one(related='picking_id.partner_id', string="Fournisseur")
    origin = fields.Char(related='picking_id.origin', string="Origin", store=True)
    qty = fields.Float(compute='_compute_quantity', string="Quantité")
    price_ttc = fields.Float(compute='_compute_price_ttc', string="Prix TTC")

    @api.depends('picking_id.move_ids_without_package')
    def _compute_quantity(self):
        qty = 0.0
        if self.picking_id.move_ids_without_package:
            for l in self.picking_id.move_ids_without_package:
                qty = qty + l.product_uom_qty
        self.qty = qty

    @api.depends('picking_id')
    def _compute_price_ttc(self):
        if self.picking_id.purchase_id:
            self.price_ttc = self.picking_id.purchase_id.amount_total

    def do_validate(self):
        user_id = self.env.user
        resp_stock = user_id.stock_responsible
        resp_quality = user_id.quality_responsible
        resp_tri = user_id.tri_responsible
        resp_direction = user_id.direction

        if resp_stock:
            self.write({
                'stock_resp': "Approuvé par",
                'stock_resp_id': user_id.id,
                'resp_st_validation_date': datetime.date.today()})
        if resp_quality:
            self.write({
                'quality_resp': "Approuvé par",
                'quality_resp_id': user_id.id,
                'resp_qu_validation_date': datetime.date.today()})
        if resp_tri:
            self.write({
                'tri_resp': "Approuvé par",
                'tri_resp_id': user_id.id,
                'resp_tri_validation_date': datetime.date.today()})
        if resp_direction:
            self.write({
                'direction': "Approuvé par",
                'direction_id': user_id.id,
                'dir_validation_date': datetime.date.today()})

    def do_cancel(self):
        user_id = self.env.user
        resp_stock = user_id.stock_responsible
        resp_quality = user_id.quality_responsible
        resp_tri = user_id.tri_responsible
        resp_direction = user_id.direction

        if resp_stock:
            self.write({
                'stock_resp': False,
                'stock_resp_id': False,
                'resp_st_validation_date': False})
        if resp_quality:
            self.write({
                'quality_resp': False,
                'quality_resp_id': False,
                'resp_qu_validation_date': False})
        if resp_tri:
            self.write({
                'tri_resp': False,
                'tri_resp_id': False,
                'resp_tri_validation_date': False})
        if resp_direction:
            self.write({
                'direction': False,
                'direction_id': False,
                'dir_validation_date': False})


class Scrap(models.Model):
    _name = 'bmc.scrap'

    name = fields.Char(string="Valeur")
    code = fields.Char(string="Nom")


class TriType(models.Model):
    _name = 'tri.type'

    name = fields.Char(string="Valeur")
    code = fields.Char(string="Nom")


class Picking(models.Model):
    _inherit = "stock.picking"

    def action_done(self):
        """Changes picking state to done by processing the Stock Moves of the Picking

        Normally that happens when the button "Done" is pressed on a Picking view.
        @return: True
        """
        self._check_company()

        todo_moves = self.mapped('move_lines').filtered(
            lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
        # Check if there are ops not linked to moves yet
        for pick in self:
            if pick.owner_id:
                pick.move_lines.write({'restrict_partner_id': pick.owner_id.id})
                pick.move_line_ids.write({'owner_id': pick.owner_id.id})

            # # Explode manually added packages
            # for ops in pick.move_line_ids.filtered(lambda x: not x.move_id and not x.product_id):
            #     for quant in ops.package_id.quant_ids: #Or use get_content for multiple levels
            #         self.move_line_ids.create({'product_id': quant.product_id.id,
            #                                    'package_id': quant.package_id.id,
            #                                    'result_package_id': ops.result_package_id,
            #                                    'lot_id': quant.lot_id.id,
            #                                    'owner_id': quant.owner_id.id,
            #                                    'product_uom_id': quant.product_id.uom_id.id,
            #                                    'product_qty': quant.qty,
            #                                    'qty_done': quant.qty,
            #                                    'location_id': quant.location_id.id, # Could be ops too
            #                                    'location_dest_id': ops.location_dest_id.id,
            #                                    'picking_id': pick.id
            #                                    }) # Might change first element
            # # Link existing moves or add moves when no one is related
            for ops in pick.move_line_ids.filtered(lambda x: not x.move_id):
                # Search move with this product
                moves = pick.move_lines.filtered(lambda x: x.product_id == ops.product_id)
                moves = sorted(moves, key=lambda m: m.quantity_done < m.product_qty, reverse=True)
                if moves:
                    ops.move_id = moves[0].id
                else:
                    new_move = self.env['stock.move'].create({
                        'name': _('New Move:') + ops.product_id.display_name,
                        'product_id': ops.product_id.id,
                        'product_uom_qty': ops.qty_done,
                        'product_uom': ops.product_uom_id.id,
                        'description_picking': ops.description_picking,
                        'location_id': pick.location_id.id,
                        'location_dest_id': pick.location_dest_id.id,
                        'picking_id': pick.id,
                        'picking_type_id': pick.picking_type_id.id,
                        'restrict_partner_id': pick.owner_id.id,
                        'company_id': pick.company_id.id,
                    })
                    ops.move_id = new_move.id
                    new_move._action_confirm()
                    todo_moves |= new_move
                    # 'qty_done': ops.qty_done})
        todo_moves._action_done(cancel_backorder=self.env.context.get('cancel_backorder'))
        self.write({'date_done': fields.Datetime.now()})
        self._send_confirmation_email()
        return True


class StockPicking(models.Model):
    _inherit = "stock.picking"

    purchase_id = fields.Many2one('purchase.order', string="Commande fournisseur", readonly=True)
    account_move_id = fields.Many2one('account.move', string="Avoir", readonly=True)
    ticket_number = fields.Integer(string="Numéro de ticket", required=False)


class StockReturnPiking(models.TransientModel):
    _inherit = "stock.return.picking.line"

    to_refund = fields.Boolean(string="Numéro de ticket", default=False)
