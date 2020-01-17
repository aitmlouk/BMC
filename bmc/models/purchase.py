# -*- coding: utf-8 -*-

# from lxml.etree import tostring, XML

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    exchange_rate = fields.Float(string="Taux de change", help="Exchange Rate")
    tva = fields.Float(string="TVA réelle", help="TVA Real")
    tva_theoretical = fields.Float(
        compute="_compute_tva_theoretical",
        string="TVA théorique",
        help="""
            TVA Theoretical, Calculated as: \n
            Sum of TVA from `Prix de vente` tab
        """
    )
    transport_cost = fields.Float(
        string="Frais transport",
        help="Transporation Cost"
    )
    # transit_cost = fields.Float(string="Frais transit", help="Transit Cost")

    # bank_charges = fields.Float(
    #     string="Frais bancaires",
    #     help="Bank Charges"
    # )
    customs = fields.Float(string="Douane réelle", help="Customs Cost")
    customs_theoretical = fields.Float(
        compute="_compute_customs_theoretical",
        string="Douane théorique",
        help="""
            Customs Cost Theoretical, Calculated as: \n
            Sum of Total Douane from `Prix de vente` tab
        """
    )
    misc_costs = fields.Float(
        string="Frais transit & divers",
        help="Miscallaneous Costs"
    )

    order_line_ids = fields.One2many(
        "purchase.order.line",
        "order_id",
        string="Définition prix de vente"
    )

    total_importation = fields.Float(
        compute="_compute_total_importation",
        string="Total Importation",
        help="""
            Total Importation, Calculated as: \n
            (record.amount_untaxed * record.(Taux de change)) +
            record.(TVA réelle) + record.(Frais transport) +
            record.(Douane réelle) + record.(Frais transit & divers)
        """
    )

    total_dh = fields.Float(
        compute="_compute_amount_dh",
        string="Total DH",
        help="""
            Total DH
        """
    )

    discount_eva = fields.Float(
        string="Taux de remise",
        help="""
            Taux de remise
        """
    )

    @api.depends('amount_total', 'exchange_rate')
    def _compute_amount_dh(self):
        for order in self:
            order.total_dh = self.amount_total * self.exchange_rate

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
    #                     submenu=False):
    #     res = super(PurchaseOrder, self).fields_view_get(
    #         view_id, view_type, toolbar, submenu)

    #     if view_type == 'form':
    #         res['arch'] = self._remove_taxes_id(res['arch'])
    #     return res

    # def _remove_taxes_id(self, view_arch):
    #     params = self._context.get('params')
    #     order = self.env[params.get('model')].browse(params.get('id'))
    #     if order.currency_id.id != order.company_id.currency_id.id:
    #         doc = XML(view_arch)
    #         expr = """
    #             //form//sheet//notebook//page//field//tree//field[\
    #                 @name='taxes_id']
    #         """.replace(' ', '').replace('\n', '')
    #         taxes_id = doc.xpath(expr)[0]
    #         doc.remove(taxes_id)
    #     return tostring(doc, encoding='unicode')

    @api.depends('order_line_ids.tva')
    def _compute_tva_theoretical(self):
        for order in self:
            order.tva_theoretical = \
                sum([line.tva for line in order.order_line_ids])

    @api.depends('order_line_ids.total_customs')
    def _compute_customs_theoretical(self):
        for order in self:
            order.customs_theoretical = \
                sum([line.total_customs for line in order.order_line_ids])

    @api.depends('amount_untaxed', 'exchange_rate', 'tva', 'transport_cost',
                 'customs', 'misc_costs')
    def _compute_total_importation(self):
        for order in self:
            order.total_importation = \
                (order.amount_untaxed * order.exchange_rate) + order.tva + \
                order.transport_cost + order.misc_costs


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    bill_per = fields.Float(
        compute="_compute_bill",
        string="% facture",
        store=True,
        help="""
            Bill %, Calculated as: \n
            Price Subtotal / order_id.amount_untaxed
        """
    )

    transport = fields.Float(
        compute="_compute_transport",
        string="Transport",
        store=True,
        help="""
            Transporation Cost, Calculated as: \n
            order_id.Frais transport * facture
        """
    )

    price_total_dirhams = fields.Float(
        compute="_compute_price_total_dirhams",
        string="Total HT Dirhams",
        store=True,
        help="""
            Total HT Dirhams, Calculated as: \n
            (Total HT * order_id.Taux de change) + Transport
        """
    )

    droit = fields.Float(
        string="Droit",
        help="By default, it's `Droit de douane` value from product."
    )

    total_customs = fields.Float(
        compute="_compute_total_customs",
        string="Total Douane",
        store=True,
        help="""
            Total Customs, Calculated as: \n
            Total HT Dirhams * Droit
        """
    )

    tva = fields.Float(
        compute="_compute_tva",
        string="TVA",
        store=True,
        help="""
            TVA, Calculated as: \n
            (Total HT Dirhams + Total Douane) *
                (product_id.supplier_taxes_id / 100)
        """
    )

    # transit_cost = fields.Float(
    #     compute="_compute_transit",
    #     string="Transit",
    #     store=True,
    #     help="""
    #         Transit cost, calculated as: \n
    #         order_id.Frais de transit * facture
    #     """
    # )

    bank_and_misc_costs = fields.Float(
        compute="_compute_bank_and_misc_costs",
        string="frais transit & divers",
        store=True,
        help="""
            Bank and Miscallaneous Costs, Calculated as: \n
            (record.order_id.(Frais transit & divers) +
            (record.order_id.(TVA réelle) - record.order_id.(TVA théorique)) +
            (record.order_id.(Douane réelle) - \
            record.order_id.(Douane théorique))) * record.(% facture)
        """
    )

    total = fields.Float(
        compute="_compute_total",
        string="P.R. TTC",
        store=True,
        help="""
            Total, Calculated as: \n
            (Total HT Dirhams + Total Douane + TVA +
            frais bancaires & divers) / Quantité
        """
    )

    list_price = fields.Float(
        related="product_id.list_price",
        string="P.V. TTC",
        store=True,
        help="By default, it's the Sales price of the product."
    )

    margin_amount = fields.Float(
        compute="_compute_margin_amount",
        string="Marge",
        help="""
            Margin amount, Calculated as: \n
            P.V. TTC - P.R. TTC
        """
    )

    margin_rate = fields.Float(
        compute="_compute_margin_rate",
        string="Taux de marge",
        store=True,
        help="""
            Margin Rate, Calculated as: \n
            Marge / P.V. TTC
        """
    )

    discount_eva = fields.Float(
        compute="_compute_discount_eva",
        string="Taux de remise",
        help="""
            Taux de remise
        """
    )

    @api.depends('order_id.discount_eva')
    def _compute_discount_eva(self):
        for line in self:
            discount = line.order_id.discount_eva
            line.discount_eva = discount

    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            vals = line._prepare_compute_all_values()
            taxes = line.taxes_id.compute_all(
                vals['price_unit'],
                vals['currency_id'],
                vals['product_qty'],
                vals['product'],
                vals['partner'])
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'] * (1 - line.discount_eva),
            })

    @api.multi
    def _compute_tax_id(self):
        for line in self:
            currency_id = self.env.user.company_id.currency_id
            print('EEE',currency_id.name)
            print('AAA',line.order_id.partner_id.property_purchase_currency_id.name)
            if line.order_id.partner_id.property_purchase_currency_id.name == currency_id.name:
                fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
                # If company_id is set, always filter taxes by the company
                taxes = line.product_id.supplier_taxes_id.filtered(lambda r: not line.company_id or r.company_id == line.company_id)
                line.taxes_id = fpos.map_tax(taxes, line.product_id, line.order_id.partner_id) if fpos else taxes
            else:
                pass
    # has_same_currency = fields.Boolean(
    #     compute="_compute_same_currency",
    #     string="Has same Currency?",
    # )

    @api.model
    def create(self, vals):
        if 'product_id' in vals:
            product = self.env['product.product'].browse(vals['product_id'])
            vals['droit'] = product.customs_duty
        return super(PurchaseOrderLine, self).create(vals)

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super(PurchaseOrderLine, self).onchange_product_id()
        self.droit = self.product_id.customs_duty or 0.0
        return result

    @api.depends('price_subtotal', 'order_id.amount_untaxed')
    def _compute_bill(self):
        for line in self:
            denom = line.order_id.amount_untaxed or 1.0
            line.bill_per = line.price_subtotal / denom

    @api.depends('order_id.transport_cost', 'bill_per')
    def _compute_transport(self):
        for line in self:
            line.transport = line.order_id.transport_cost * line.bill_per

    @api.depends('price_subtotal', 'order_id.exchange_rate', 'transport')
    def _compute_price_total_dirhams(self):
        for line in self:
            line.price_total_dirhams = \
                (line.price_subtotal * line.order_id.exchange_rate) + \
                line.transport

    @api.depends('price_total_dirhams', 'droit')
    def _compute_total_customs(self):
        for line in self:
            line.total_customs = line.price_total_dirhams * line.droit

    @api.depends('price_total_dirhams', 'total_customs',
                 'product_id.supplier_taxes_id')
    def _compute_tva(self):
        for line in self:
            amount = sum([
                tax.amount for tax in line.product_id.supplier_taxes_id
                if tax]) or 1.0
            line.tva = \
                (line.price_total_dirhams + line.total_customs) * \
                (amount / 100)

    # @api.depends('order_id.transit_cost', 'bill_per')
    # def _compute_transit(self):
    #     for line in self:
    #         line.transit_cost = line.order_id.transit_cost * line.bill_per

    @api.depends('order_id.misc_costs', 'order_id.tva',
                 'order_id.tva_theoretical', 'order_id.customs',
                 'order_id.customs_theoretical', 'bill_per')
    def _compute_bank_and_misc_costs(self):
        for line in self:
            line.bank_and_misc_costs = \
                (line.order_id.misc_costs +
                    (line.order_id.tva - line.order_id.tva_theoretical) +
                    (line.order_id.customs - line.order_id.customs_theoretical)
                 ) * (line.bill_per)

    @api.depends('price_total_dirhams', 'total_customs', 'tva',
                 'bank_and_misc_costs', 'product_qty')
    def _compute_total(self):
        for line in self:
            denom = line.product_qty or 1.0
            line.total = (line.price_total_dirhams + line.total_customs +
                          line.tva + line.bank_and_misc_costs) / denom

    @api.depends('total', 'list_price')
    def _compute_margin_amount(self):
        for line in self:
            line.margin_amount = line.list_price - line.total

    @api.depends('margin_amount', 'list_price')
    def _compute_margin_rate(self):
        for line in self:
            denom = line.list_price or 1.0
            line.margin_rate = line.margin_amount / denom

    # @api.depends('currency_id', 'company_id.currency_id')
    # def _compute_same_currency(self):
    #     for line in self:
    #         line.has_same_currency = \
    #             line.currency_id.id == line.company_id.currency_id.id
