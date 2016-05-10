from openerp import api, models, exceptions, fields,  _
import openerp.addons.decimal_precision as dp
import datetime
import logging
import datetime

_logger = logging.getLogger(__name__)


__author__ = 'tbri'

class shipping_days(models.Model):
    _name = 'elmatica_purchase_flow.shipping_days'

    to_country = fields.Many2one('res.country', 'From country', required=True)
    shipping_days = fields.Integer('Number of days', required=True)