# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
import datetime
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
import csv
import os
import inspect

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
    quality_resp = fields.Text(string="Responsable qualité", readonly=True)
    ticket_number = fields.Char(related='picking_id.ticket_number', string="Numéro de ticket", readonly=True)
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
    qty = fields.Float(related='picking_id.quantity_done', string="Quantité", store=True)
    currency_id = fields.Many2one(related='picking_id.purchase_id.currency_id', string="Devise", store=True)
    #uom_id = fields.Many2one(related='picking_id.product_uom', string="Unite", store=True)
    uom_id = fields.Many2one('uom.uom', compute='_compute_uom', string="UOM")
    price_ttc = fields.Float(compute='_compute_price_ttc', string="Prix TTC")
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user)
    direction_ok = fields.Boolean(related='user_id.direction', string="Direction Ok")


    @api.depends('picking_id.move_ids_without_package')
    def _compute_uom(self):
        if self.picking_id.move_ids_without_package:
            for l in self.picking_id.move_ids_without_package:
                uom_id = l.product_uom
            self.uom_id = uom_id.id
        else:
            self.uom_id = None

    @api.depends('picking_id')
    def _compute_price_ttc(self):
        if self.picking_id:
            if self.picking_id.purchase_id:
                order_lines = self.picking_id.purchase_id.order_line
                for l in order_lines:
                    if l.product_id == self.product_id:
                        self.price_ttc = (l.price_subtotal + l.price_tax) / l.product_qty
                    else:
                        self.price_ttc = 0
        else:
            self.price_ttc = 0

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

    def do_pass(self):
        user_id = self.env.user
        self.write({'quality_state': 'pass',
                    'direction': "Approuvé par",
                    'user_id': self.env.user.id,
                    'direction_id': user_id.id,
                    'dir_validation_date': datetime.date.today(),
                    'control_date': datetime.date.today()})
        return self.redirect_after_pass_fail()

    def do_fail(self):
        user_id = self.env.user
        print('-----------', datetime.date.today())
        self.write({
            'quality_state': 'fail',
            'direction': "Réfusé par",
            'user_id': self.env.user.id,
            'direction_id': user_id.id,
            'dir_validation_date': datetime.date.today(),
            'control_date': datetime.date.today()})
        return self.redirect_after_pass_fail()

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

    def do_reject(self):
        user_id = self.env.user
        resp_stock = user_id.stock_responsible
        resp_quality = user_id.quality_responsible
        resp_tri = user_id.tri_responsible
        resp_direction = user_id.direction

        if resp_stock:
            self.write({
                'stock_resp': "Refusé par",
                'stock_resp_id': user_id.id,
                'resp_st_validation_date': datetime.date.today()})
        if resp_quality:
            self.write({
                'quality_resp': "Refusé par",
                'quality_resp_id': user_id.id,
                'resp_qu_validation_date': datetime.date.today()})
        if resp_tri:
            self.write({
                'tri_resp': "Refusé par",
                'tri_resp_id': user_id.id,
                'resp_tri_validation_date': datetime.date.today()})
        if resp_direction:
            self.write({
                'direction': "Refusé par",
                'direction_id': user_id.id,
                'dir_validation_date': datetime.date.today()})


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

    quantity_done = fields.Float(compute='_compute_quantity_done', string="Fait")
    purchase_id = fields.Many2one('purchase.order', string="Commande fournisseur", readonly=True)
    account_move_id = fields.Many2one('account.move', string="Avoir", readonly=True)
    ticket_number = fields.Char(string="Numéro de ticket")
    pesage_externe = fields.Float(string="Pesage externe")
    tri = fields.Boolean(string="Besoin de tri")
    supplier_raw = fields.Boolean(related='partner_id.supplier_materiel', string="Fournisseur de matier", store=True)
    deadline_tri = fields.Date(string="Date fin de tri")
    expected_date = fields.Date(compute='_compute_date', string="Date prévue fin de tri")
    approval_id = fields.Many2one('approval.request', string="Demande d'approbation")

    in_weight = fields.Float(string="Balance In")
    out_weight = fields.Float(string="Balance Out")

    def _compute_date(self):
        quality_id = self.env['quality.check'].search([('picking_id', '=', self.id)])
        if quality_id:
            rec = quality_id[0]
            self.expected_date = datetime.date.today() + datetime.timedelta(days=rec.days_number)
        else:
            self.expected_date = None

    @api.depends('move_ids_without_package')
    def _compute_quantity_done(self):
        move = []
        for l in self.move_ids_without_package:
            move.append(l.quantity_done)
        self.quantity_done = sum(move)

    def action_tri(self):
        a = self.env['stock.move'].search([('picking_id', '=', self.id)])
        b = a.product_id.ids
        self.deadline_tri = datetime.date.today()
        self.purchase_id.order_tri = True
        for x in b:
            c = self.env['product.product'].search([('id', '=', x)])
            d = c.tri
            if d == True:
                self.tri = True

    def cancel_action_tri(self):
        self.deadline_tri = False
        if not self.deadline_tri:
            self.purchase_id.order_tri = False

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

    def _create_backorder(self):

        """ This method is called when the user chose to create a backorder. It will create a new
        picking, the backorder, and move the stock.moves that are not `done` or `cancel` into it.
        """
        backorders = self.env['stock.picking']
        for picking in self:
            moves_to_backorder = picking.move_lines.filtered(lambda x: x.state not in ('done', 'cancel'))
            if moves_to_backorder:
                backorder_picking = picking.copy({
                    'name': '/',
                    'move_lines': [],
                    'move_line_ids': [],
                    'backorder_id': picking.id
                })
                picking.message_post(
                    body=_(
                        'The backorder <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> has been created.') % (
                             backorder_picking.id, backorder_picking.name))
                moves_to_backorder.write({'picking_id': backorder_picking.id})
                moves_to_backorder.mapped('package_level_id').write({'picking_id': backorder_picking.id})
                moves_to_backorder.mapped('move_line_ids').write({'picking_id': backorder_picking.id})
                backorder_picking.action_assign()
                backorders |= backorder_picking
        return backorders

    def read_balance(self):
        directory_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        path = os.path.join(directory_path, 'file.txt')
        print('path', path)
        file = open(path, "r")
        line = file.readline()
        in_weight = line.split(',')[0]
        out_weight = line.split(',')[1]
        print(in_weight)
        print(out_weight)
        if out_weight == '0000':
            self.in_weight = None
            self.out_weight = None
        else:
            self.in_weight = in_weight
            self.out_weight = out_weight



class StockReturnPiking(models.TransientModel):
    _inherit = "stock.return.picking.line"

    to_refund = fields.Boolean(string="Numéro de ticket", default=False)


class GenerateOrder(models.TransientModel):
    _name = "generate.mrp.production"
    _rec_name = 'product_id'
    _description = 'Return Picking Line'

    product_id = fields.Many2one('product.product', string="Produit issu du tri", required=True)
    picking_id = fields.Many2one('stock.picking', string="Transfert")

    def create_mrp(self):
        # create new mrp from transfert
        active_id = self.env.context.get('active_id', False)
        picking_id = self.env['stock.picking'].browse(active_id)
        data = {
            'product_id': self.product_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_id.uom_id.id,
            'purchase_id': picking_id.purchase_id.id,
            'picking_id': picking_id.id,
            'tri': True,
        }
        mrp_wiz = self.env['mrp.production'].create(data)
        return {
            'name': _('MRP'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('mrp.mrp_production_form_view').id,
            'res_model': 'mrp.production',
            'res_id': mrp_wiz.id,
            'type': 'ir.actions.act_window',
        }


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    order_tri = fields.Boolean(string="Commande triée", default=False)
    domain_product_id = fields.Many2one('product.product', string="Article")

    @api.onchange('domain_product_id')
    def onchange_domain_product_id(self):
        if self.domain_product_id:
            sellers = self.domain_product_id.seller_ids
            supp = []
            for s in sellers:
                supp.append(s.name.id)
            return {'domain': {
                'partner_id': [('id', 'in', supp)]
            }}


class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    multi_article = fields.Boolean(string="Saisie multi articles", default=False)


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    approval_line_ids = fields.One2many('approval.request.line', 'request_id', string="Lignes demande")
    employee_id = fields.Many2one('hr.employee', string="Employé", required=True)
    department_id = fields.Many2one(related='employee_id.department_id', string="Departement", required=True)
    picking_id = fields.Many2one('stock.picking', string="Transfert")
    multi_article = fields.Boolean(related='category_id.multi_article', string="Saisie multi articles", store=True)


class ApprovalRequestLine(models.Model):
    _name = "approval.request.line"
    _description = "Approval lines"

    product_id = fields.Many2one('product.product', string="Produit")
    request_id = fields.Many2one('approval.request', string="Demande d'approbation")
    quantity = fields.Float(string="Quantité")
    uom_id = fields.Many2one(related='product_id.uom_id', string="Unite de mésure", store=True)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    mrp_ids = fields.One2many('mrp.production', 'order_id', string="Production")
    mrp_count = fields.Integer(compute='action_compute_mrp', string="Ordre de fabrication", store=True)

    @api.depends('mrp_ids')
    def action_compute_mrp(self):
        if self.mrp_ids:
            self.mrp_count = len(self.mrp_ids) or 0
        else:
            pass


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    order_id = fields.Many2one('sale.order', string="Bon de commande")
    purchase_id = fields.Many2one('purchase.order', string="Commande achat")
    picking_id = fields.Many2one('stock.picking', string="Réception achat")
    lost = fields.Float(string='Perte de feu')
    tri = fields.Boolean(string='Origine tri')
    broyage = fields.Boolean(string='Origine broyage')

    def action_broyage(self):
        self.broyage = True
        self.origin = 'Broyage'
        self.name = self.env['ir.sequence'].next_by_code('mrp.production.bmc')


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    partner_id = fields.Many2one('res.partner', string="Fournisseur")
    partner_product_id = fields.Many2one('product.supplier.info', string="Fournisseur/Article")
    broyage = fields.Boolean(string='Broyage')


class AccountTax(models.Model):
    _inherit = "account.tax"

    exo_ok = fields.Boolean(string='Exonéré de TVA achats')


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    tva = fields.Boolean(string='TVA')

    @api.onchange('tva', 'product_id')
    def onchange_tva(self):
        if self.product_id:
            if self.product_id.raw_materials and self.tva is True:
                self.taxes_id = self.product_id.supplier_taxes_id
            elif self.product_id.raw_materials and self.tva is not True:
                self.taxes_id = None
                taxe_id = self.env['account.tax'].search([('exo_ok', '=', True)])
                print('--------', taxe_id)
                if taxe_id:
                    self.taxes_id = (taxe_id.id, taxe_id.id)
                else:
                    pass


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    tri = fields.Boolean(string="Tri")
