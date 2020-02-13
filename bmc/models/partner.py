# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    ice = fields.Char(string="I.C.E.", help="I.C.E.")
    register = fields.Char(string="Registre du commerce", help="Register")
    tax_identification = fields.Char(
        string="Identifiant fiscal",
        help="Tax Identification"
    )
    patent = fields.Char(string="Patente", help="Patent")
    supplier_materiel = fields.Boolean(string="Fournisseur matière première")
    is_customer = fields.Boolean(string="Est un client")
    is_supplier = fields.Boolean(string="Est un fournisseur")


class Product(models.Model):
    _inherit = "product.template"

    raw_materials = fields.Boolean(string="Matière première",
                                   help="Materials")
    tri = fields.Boolean(string="Besoin d\'un tri",
                         help="Tri")
    quality_id = fields.Many2one("quality.point",
                                 string="Point de controle",
                                 help="Control point"
                                 )
    define_product = fields.Boolean(string="Produit fini", default=False)

    @api.onchange('raw_materials')
    def onchange_raw_materials(self):
        if self.raw_materials:
            self.tri = True


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    move_ids = fields.One2many('stock.move', 'partner_id2', string="Mouvement de stock reception",
                               domain="['&',['state','=','done'],['picking_type_id.name','ilike','Réception']]")
    move_return_ids = fields.One2many('stock.move', 'partner_id2', string="Mouvement de stock retour")
    move_prod_ids = fields.One2many('stock.move.line', 'partner_id2', string="Mouvement de stock prod")
    qty_livre = fields.Float(string="Quantités livrées", compute='action_compute_qty_livre')
    qty_retour = fields.Float(string="Retours", compute='action_compute_qty_retour')
    qty_prod = fields.Float(string="Produits -Tri", compute='action_compute_qty_prod')
    taux_efficacite = fields.Float(string="Efficacité", compute='action_compute_taux_efficacite')

    @api.depends('move_ids')
    def action_compute_qty_livre(self):
        total = 0.0
        for line in self.move_ids:
            total += line.quantity_done
        self.qty_livre = total

    @api.depends('move_return_ids')
    def action_compute_qty_retour(self):
        total = 0.0
        for line in self.move_return_ids:
            total += line.quantity_done
        self.qty_retour = total

    @api.depends('move_prod_ids')
    def action_compute_qty_prod(self):
        total = 0.0
        for line in self.move_prod_ids:
            total += line.qty_done
        self.qty_prod = total

    @api.depends('move_ids', 'move_return_ids', 'move_prod_ids')
    def action_compute_taux_efficacite(self):
        if self.move_ids:
            total = 0.0
            for line in self.move_ids:
                total += line.quantity_done
            total1 = 0.0
            for line in self.move_return_ids:
                total1 += line.quantity_done
            total2 = 0.0
            for line in self.move_prod_ids:
                total2 += line.qty_done
                if total > 0:
                    self.taux_efficacite = ((total - total1 - total2) * 100) / total
                else:
                    self.taux_efficacite = 0
        else:
            self.taux_efficacite = 0


class StockMove(models.Model):
    _inherit = "stock.move"

    partner_id1 = fields.Many2one('res.partner', string="Fournisseur", domain="[('state','=','done')]")
    partner_id2 = fields.Many2one('product.supplierinfo', string="Fournisseur/Article", domain="[('state','=','done')]")


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    partner_id2 = fields.Many2one('product.supplierinfo', string="Fournisseur/Article")


class Users(models.Model):
    _inherit = "res.users"

    stock_responsible = fields.Boolean(string="Responsable stock")
    quality_responsible = fields.Boolean(string="Responsible qualite")
    tri_responsible = fields.Boolean(string="Responsable de tri")
    direction = fields.Boolean(string="Direction")
