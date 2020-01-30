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


class Users(models.Model):
    _inherit = "res.users"

    stock_responsible = fields.Boolean(string="Responsable stock")
    quality_responsible = fields.Boolean(string="Responsible qualite")
    tri_responsible = fields.Boolean(string="Responsable de tri")
    direction = fields.Boolean(string="Direction")