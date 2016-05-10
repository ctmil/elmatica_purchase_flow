import base64

from openerp import api, models, exceptions, fields,  _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)


class warning(models.TransientModel):
    _name = 'elmatica_purchase_flow.warning'

    warning = fields.Char('Warning text', readonly=True)
    order = fields.Many2one('sale.order', readonly=True)
    requested_delivery_date = fields.Date('Updated Requested delivery date')

    @api.multi
    #@api.returns('ir.actions.act_window')
    def action_continue(self):
        self.ensure_one()
        assert self.order
        return self.order.with_context(updated_requested_delivery_date=self.requested_delivery_date, skip_check_requested_delivery_date=True).action_create_purchase_order()
        #return {'type': 'ir.actions.act_window_close'}
