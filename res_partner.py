from openerp import api, models, exceptions, fields, _
import openerp.addons.decimal_precision as dp
import datetime


__author__ = 'tbri'


class res_partner(models.Model):
    _inherit = 'res.partner'

    delivery_method = fields.Selection([
                                           ('exw', 'Ex-Works'),
                                           ('ff', 'Via Elmatica Hub (HK)')], string='Delivery method',
                                       default='exw', required=True)
    wkng_gerber = fields.Boolean('Wkng Gerber', help='Customer needs to approve Gerber file before a PO is approved.')