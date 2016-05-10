import base64
from collections import OrderedDict
from openerp import api, models, exceptions, fields,  _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning

import logging
from iso3166 import countries
from situation import calc_invoice_company, prepare_order_invoice_line

_logger = logging.getLogger(__name__)


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    #def _create_invoice_from_picking(self, cr, uid, picking, vals, context=None):
    #    rv = super(stock_picking, self)._create_invoice_from_picking(cr, uid, picking, vals, context)
    #    assert False

    @api.multi
    def _get_invoice_vals(self, info, key, inv_type, journal_id, move):
        _logger.info('%s get_invoice_vals %s', self, info)
        if not self.po_id:
            return info
        if not self.po_id.sale_id:
            return info

        sale_order = self.po_id.sale_id
        assert  sale_order
        info = sale_order.prepare_invoice(sale_order, info)
        #company = calc_invoice_company(sale_order)
        #info['company_id'] = company.id
        #print "MOVE", move, info
        #assert False
        return info

    # Override this method to populate values when creating invoice from picking.
    @api.v7
    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
        rv = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context)
        assert len(context.get('active_ids')) == 1
        for rec in self.browse(cr, uid, context.get('active_ids')):
            info = rec._get_invoice_vals(rv, key, inv_type, journal_id, move)
            print "VALUES",  info
            return info
        #assert False

    #@api.multi
    #def _calc_super_order_id(self):
    #    for picking in self:
    #        po = picking.po_id
    #        picking.super_order_id = po and po.super_order_id or None

    #super_order_id = fields.Many2one('super.sales.order', string='Super Order Reference', compute='_calc_super_order_id')

class stock_move(models.Model):
    _inherit = 'stock.move'

    @api.v8
    def set_invoice_line_vals(self, info):
        order = self.id.picking_id.sale_id
        #company = calc_invoice_company(order) # Why?

        info = prepare_order_invoice_line(order, info)
        return info

    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
        rv = super(stock_move, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type, context)
        for rec in self.browse(cr, uid, [move]):
            info = rec.set_invoice_line_vals(rv)
        return info
