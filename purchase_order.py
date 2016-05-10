from openerp import api, models, exceptions, fields,  _
import openerp.addons.decimal_precision as dp
import datetime
import logging
import datetime

_logger = logging.getLogger(__name__)
tooling_products = ['[TOOLING]','[SETUP]']

class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'

    @api.multi
    def _calc_delivered_qty(self):
        ids = [x.id for x in self]
        self._cr.execute("""
  select pol.id as purchase_order_line_id, sp.name, sm.product_uom_qty,sm.state as move_state,
    sp.name,coalesce(spt.code, 'nada') as picking_type
  --left join sale_order so on so.id=sol.order_id
  from purchase_order_line pol
  left outer join stock_move sm on sm.purchase_line_id=pol.id
  left outer join stock_picking sp on sm.picking_id=sp.id
  LEFT outer JOIN stock_picking_type spt on (spt.id=sp.picking_type_id)
  where pol.id in %s
""", (tuple(ids),))

        tmp = {}
        # https://www.odoo.com/es_ES/forum/help-1/question/showing-delivery-information-on-sales-orders-72892
        for item in self._cr.dictfetchall():
            if item['move_state'] == 'cancel':
                continue

            if item['picking_type'] == 'nada':
                continue

            sign = item['picking_type'] in ('incoming', 'nada') and 1 or -1
            pol = item['purchase_order_line_id']
            if not pol in tmp:
                tmp[pol] = {'done' : 0.0, 'assigned': 0.0}

            tmp[pol][item['move_state']] += sign * item['product_uom_qty']
        for theline in self:
                if theline.id in tmp:
                    theline.delivered_qty = tmp[theline.id]['done']
                    theline.undelivered_qty = tmp[theline.id]['assigned']

    sale_order_line = fields.Many2one('sale.order.line', string='Sale order line')
    delivered_qty = fields.Float('Delivered', compute='_calc_delivered_qty')
    undelivered_qty = fields.Float('Undelivered', compute='_calc_delivered_qty')


class purchase_order(models.Model):
    _inherit = 'purchase.order'

    """ can be removed soon
    @api.multi
    def action_confirm_order(self):
        self.ensure_one()
        req_shipping_date, delivery_date = self.calculate_shipping_date()
        self.updated_delivery = delivery_date
        action_dict = self.sale_id.action_quotation_send()
        print "ACTION DICT", action_dict
        return action_dict
        return self.sale_id.action_quotation_send()
        et = self.env['email.template']
        try:
            template_id = self.env['ir.model.data'].get_object_reference('sale', 'email_template_edi_sale')[1]
        except ValueError:
            template_id = False

        print "SENDING THE MAIL!!", template_id
        t2 = et.browse([template_id])
        print "T2", t2
        mail_id = t2.send_mail(template_id, self.sale_id.id, raise_exception=True)
    """

    """
    @api.onchange('confirmed_date')
    def onchange_confirmed_date(self):
        print "onchange_confirmed", self
        self.updated_delivery = None
        self.write({'updated_delivery': None})
        req_shipping_date, delivery_date = self.calculate_shipping_date()
        self.updated_delivery = delivery_date

        deviation, warning = self.get_deviation_status()

        if warning:
            raise exceptions.Warning(warning)
        else:
            return
    """
    @api.multi
    def _calc_deviating_shipping_date(self):
        for order in self:
            deviation, warning = order.get_deviation_status()
            order.deviating_shipping_date = bool(deviation)
    """
    def get_deviation_status(self):
        self.ensure_one()
        required_date = fields.Date.from_string(self.minimum_planned_date)
        confirmed_date = fields.Date.from_string(self.confirmed_date)

        if not required_date or not confirmed_date:
            return None, None

        diff = (confirmed_date - required_date).days
        warning = None
        deviation = None
        if diff>0 and diff>self.partner_days_delay:
            warning = _('Confirmed shipping is too late since partner has allowed delay of %d when the delay is %d' % (self.partner_days_delay, diff))
            deviation = 'late'
        elif diff<0 and diff<self.partner_days_early:
            warning = _('Confirmed shipping is too early since partner has allowed delay of %d when it is %d days before' % (self.partner_days_delay, diff))
            deviation = 'early'

        return deviation, warning

        # MAY BE DELETED SOON
    """

    @api.multi
    def write(self, vals):
        info_product = self.get_info_product()
        _logger.info('%s Writing PO lines %s', self, vals)
        if 'order_line' in vals:
            ids = [x[1] for x in vals['order_line'] if x[1]]
            ids += [x.id for x in self]
            _logger.info('Looking for ids %s', ids)
            self._cr.execute('select pol.id, order_id, po.state as po_state, po.name as po_name from purchase_order_line pol '
                             'join purchase_order po on po.id=pol.order_id '
                             'where pol.id in %s', (tuple(ids),))
            lines_states = {}
            for item in self._cr.dictfetchall():
                lines_states[item['id']] = (item['po_state'], item['po_name'])

            _logger.info('po_lines_states %s', lines_states)

            for ol in vals['order_line']:
                _logger.info('Writing PO lines %s %s', ol, ol[1] in lines_states)
                if ol[0] == 4:
                    continue
                elif ol[0] == 1:
                    state = lines_states[ol[1]][0]
                    if state not in ('draft', 'sent'):
                        raise exceptions.Warning(_('%s: Can not update lines in the current state %s.\n'
                                                   'Only add new lines for changing leadtime.' % (lines_states[ol[1]][1], state)))
                elif ol[0] == 0:
                    # Check that the product is an info product
                    lineinfo = ol[2]
                    if not lineinfo['product_id']:
                        raise exceptions.Warning(_('%s: Trying to add line without product' % lines_states[ol[1]][1]))
                    elif lineinfo['product_id'] != info_product:
                        for so in self:
                             if so.state in ('approved', 'done'):
                                raise exceptions.Warning(_('%s: Trying to add line with product that is not a leadtime product.' % so.name))
                    else:
                        _logger.info('Adding infoline to PO %s', self)

        return super(purchase_order, self).write(vals)

    """
    @api.multi
    def write(self, vals):
        # If we are in divergence
        for order in self:
            deviation, warning = order.get_deviation_status()
            if deviation:
                _logger.info('Writing values %s' % vals)
                _logger.info('Order %s deviation %s updated delivery %s or %s', self.name, order.updated_delivery, vals.get('actual_delivery', 'NOTSET'))
                # We must either have updated_delivery or write it
                if order.updated_delivery or vals.get('updated_delivery', False):
                    continue
                else:
                    req_shipping_date, delivery_date = order.sudo().calculate_shipping_date()
                    order.updated_delivery = delivery_date
                    if not delivery_date:
                        raise exceptions.Warning(_('We must have an actual delivery date for %s' % self.name))

        result = super(purchase_order, self).write(vals)
        return result
    """

    def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
        info = super(purchase_order, self)._prepare_invoice(cr, uid, order, line_ids, context)
        info['operational'] = True
        return info


    def view_invoice(self, cr, uid, ids, context=None):
        info = super(purchase_order, self).view_invoice(cr, uid, ids, context)
        print "CTX", info['context']
        e = eval(info['context'])
        e.update(operational=True)
        e.update(default_operational=True)
        info['context'] = repr(e)
        print "CTX 2", info['context']
        return info

    @api.multi
    def _calc_customer(self):
        for order in self:
            cust = order.dest_address_id
            if cust.sudo().parent_id:
                cust = cust.sudo().parent_id
            order.customer_id = cust

    @api.multi
    def _calc_sale(self):
        for order in self:
            sales = set([x.sale_order for x in order.order_line if x.sale_order])
            if not sales or len(sales)==0:
                order.shipping_calc_status = _('Unable to calculate shipping date since sales order is not set. PO=%s' % order.name)
            elif len(sales)>1:
                order.shipping_calc_status = _('Unable to calculate shipping date since PO is pointing to several sales orders. PO=%s' % order.name)
            else:
                order.sale_id = sales.pop()

    @api.multi
    def _calc_super_order_id(self):
	return None
        #for order in self:
        #    order.super_order_id = order.sudo().sale_id and order.sudo().sale_id.super_order_id or None
        #    if not order.super_order_id:
        #        _logger.info('Fetching super_order_id %s %s', order.sudo().requisition_id, order.sudo().requisition_id.sso_id)
        #        order.super_order_id = order.sudo().requisition_id and order.requisition_id.sudo().sso_id or None

    def recalc_shipping_days(self):
        destination = self.customer_id.country_id
        _logger.info('Recalculate shipping days for order %s', self.name)
        if not destination:
            self.shipping_calc_status = 'No destination country.'
            return None

        old_shipping_days = self.shipping_days
        if self.sale_id and self.sale_id.incoterm and self.sale_id.incoterm.code in ('FCA', 'EXW'):
            if self.sale_id.incoterm.code == 'FCA':
                _logger.info('Not calculating shipping days for order %s since the SO is FCA.', self.name)
                self.shipping_days = 1
            elif self.sale_id.incoterm.code == 'EXW':
                _logger.info('Not calculating shipping days for order %s since the SO is EXW.', self.name)
                self.shipping_days = 0
        else:
            days = self.env['elmatica_purchase_flow.shipping_days'].search([('to_country','=',destination.id)])
            if len(days)!=1:
                raise exceptions.Warning('Unable to retrieve shipping days for %s.' % destination.code)
            self.shipping_days = days.shipping_days
            _logger.info('shipping days for order %s is %d since the country is %s', self.name, self.shipping_days, destination.code)
        _logger.info('Changed shipping days from %d to %d' % (old_shipping_days, self.shipping_days))

    
    @api.multi
    @api.depends('sale_id')
    def _calc_shipping_days(self):
        for order in self:
            order.sudo().recalc_shipping_days()
            req_shipping_date, delivery_date = order.sudo().calculate_shipping_date()
            order.updated_delivery = delivery_date
    

    @api.onchange('dest_address_id', 'sale_id', 'shipping_days',
                  'hub_days', 'buffer_days', 'customer_partner_days_add', 'requested_delivery')
    @api.multi
    def onchange_destination(self):
        self.ensure_one()
        _logger.info("onchange_destination %s", self)
        #shipping_date, delivery_date = self.calculate_shipping_date()
        #self.updated_delivery = delivery_date
        #if not shipping_date:
        #    return
	self.shipping_calc_status = 'Calculation disabled at this time.2'
        #self.shipping_calc_status = 'Calculated shipping date %s' % fields.Date.to_string(shipping_date)
	# TBRI

    
    @api.multi
    def _calc_hub_days(self):
        for order in self:
            supplier = order.partner_id
            if supplier.delivery_method=='exw': # ExWorks
                order.hub_days = 0
            else:                            
                order.hub_days = supplier.partner_add_days
   
    
    @api.multi
    def _calc_add_days(self):
        for order in self:
            if order.customer_id and order.sudo().customer_id.partner_add_days:
                order.customer_partner_days_add = order.sudo().customer_id.partner_add_days
    
    @api.onchange('buffer_days')
    def onchange_buffer_days(self):
	# TBRI
        #required_date, delivery_date = self.calculate_shipping_date()
        #if not required_date:
        #    return
        #self.updated_delivery = delivery_date
        self.shipping_calc_status = 'Calculation disables still.'
       	# self.shipping_calc_status = 'Calculated shipping date %s' % fields.Date.to_string(required_date)
        #for line in self.order_line:
        #    line.date_planned = required_date
        #x = self.minimum_planned_date
        #print "MINIMUM_PLANNED_DATE", x

    @api.depends('sale_id')
    @api.multi
    def _calc_product_po(self):
        for order in self:
            if order.is_tooling():
                order.matching_product_po = order.sale_id.purchase_orders
            else:
                order.matching_product_po = None

    @api.multi
    @api.depends('order_line', 'order_line.name')
    def _calc_tooling_order(self):
        for order in self:
            _logger.info('Order %s tooling_order? %s', order.name, order.tooling_order)
            order.tooling_order = order.is_tooling()
            _logger.info('Order %s tooling_order? %s', order.name, order.tooling_order)

    def is_tooling(self):
        tooling_match = {True: 0, False: 0}
        self.ensure_one()
        matches = [x for x in self.order_line if x.name.find('[TOOLING]')==0 ]
        #_logger.info('is_tooling %s %s', self.name, matches)
        return len(matches)>0

    @api.depends('sale_id')
    @api.multi
    def _calc_customer_contact(self):
        for order in self:
            if not order.sudo().sale_id:
                continue

            order.customer_contact = order.sudo().sale_id.customer_contact

    @api.depends('wkng_gerber_field', 'customer_id.wkng_gerber')
    @api.multi
    def _calc_wkng_gerber(self):
        for order in self:
            if order.is_tooling():
                order.wkng_gerber = True
            else:
                #n consider_gerber = order.sudo().customer_id.wkng_gerber or order.sudo().sale_id.super_order_id.wkng_gerber
                consider_gerber = order.sudo().customer_id.wkng_gerber
                order.wkng_gerber = not consider_gerber and True or order.wkng_gerber_field


    @api.depends('sale_id')
    @api.multi
    def _calc_customer_ref(self):
        for order in self:
            if not order.sudo().sale_id:
                order.customer_ref = ''
                continue

            order.customer_ref = order.sudo().sale_id.client_order_ref

    @api.depends('sale_id', 'partner_id')
    @api.multi
    def _calc_consider_wkng_gerber(self):
        for order in self:
            if not order.customer_id:
                order.consider_wkng_gerber = False
                continue
            customer_wkng_gerber = order.customer_id.wkng_gerber
            # _logger.info('%s Considering %s %s %s %s' % (order.name, order.is_tooling(), order.customer_id, customer_wkng_gerber, order.sudo().sale_id.super_order_id.wkng_gerber))
            if order.is_tooling():
                order.consider_wkng_gerber = False
            # elif customer_wkng_gerber or order.sudo().sale_id.wkng_gerber:
            elif customer_wkng_gerber:
                order.consider_wkng_gerber = True
            else:
                order.consider_wkng_gerber = False

    
    @api.multi
    def _calc_comp_buffer_days(self):
        """
        Computed buffer days is the difference between in-leadtime and out-leadtime of the SSO...
        """
        for order in self:
            if order.tooling_po:
                continue

            po_products = [x.product_id for x in order.order_line]

            #pcb_superline = None
            #for superline in super_order.order_line:
            #    if superline.order_id == order.sale_id and superline.product_id in po_products:
            #        pcb_superline = superline
            #        assert superline.order_id == order.sale_id, 'PO %s superline %s has order_id %s but we have sale_id %s' % (order.name, superline, superline.order_id, order.sale_id)
            #       break

            #if not pcb_superline:
            #    _logger.info('No PCB SSO line found for po %s so %s product %s', order.name, order.sale_id, po_products)
            #    continue
            #buff_d = pcb_superline.out_delay and pcb_superline.out_delay - pcb_superline.delay or 0
	    # gustavo
	    buff_d = 0
            order.computed_buffer_days = buff_d
    
    """
    @api.multi
    def _calc_expected_delivery(self):
        for order in self:
            if order.updated_delivery and order.updated_delivery != order.requested_delivery:
                order.expected_delivery = order.updated_delivery
            else:
                order.expected_delivery = order.requested_delivery
    """

    @api.multi
    def _get_delivery_date(self):
        info_product = self.get_info_product()

        for order in self:
            if not order.confirmed_date:
                continue
            leadtime_for_order = 0
            for line in order.order_line:
                if not line.product_id or not line.product_id.id==info_product:
                    continue

                _logger.info('%s leadtime line %s adds %s', order.name, line.name, line.leadtime)
                leadtime_for_order += line.leadtime
            leadtime_for_order += order.buffer_days
            order.delivery_date = fields.Date.from_string(order.confirmed_date) + datetime.timedelta(days=leadtime_for_order)

    def get_info_product(self):
        info_product_template = self.env['product.template'].search([('name', '=', 'info:')])
        if not info_product_template:
            raise exceptions.Warning(_('Must have one and only one product called info: We have %d' % len(info_product_template)))
        self._cr.execute('select id from product_product where product_tmpl_id=%s', (info_product_template[0].id,))
        info_product = None
        for l in self._cr.fetchall():
            if l[0]:
                assert not info_product
                info_product = l[0]

        if not info_product:
            raise exceptions.Warning(_('Unable to retrieve the :info: product uniquely. Must have a product called info:'))

        _logger.info('Retrieved info product %d', info_product)
        return info_product

    order_line = fields.One2many('purchase.order.line', 'order_id', 'Order Lines',
                                      states={'approved':[('readonly',False)], # hm
                                              'done':[('readonly',True)]},
                                      copy=True)

    confirmed_date = fields.Date('Confirmed shipping date')
    super_order_id = fields.Many2one('super.sales.order', string='Super Order Reference', compute='_calc_super_order_id')
    customer_id = fields.Many2one('res.partner',  compute='_calc_customer')
    customer_ref = fields.Char('Customer ref', compute='_calc_customer_ref')
    sale_id = fields.Many2one('sale.order', compute='_calc_sale', string='Sale Order')
    matching_product_po = fields.Many2one('purchase.order', compute='_calc_product_po', string='Related Purchase Order')
    customer_contact = fields.Many2one('res.partner', compute='_calc_customer_contact')
    partner_days_early = fields.Integer(related='customer_id.partner_delivery_early', readonly=True, help='The number of days before the expected date the customer will accept.')
    partner_days_delay = fields.Integer(related='customer_id.partner_delivery_late', readonly=True, help='The number of days after the expected date the customer will accept')
    hub_days = fields.Integer('Hub days', compute='_calc_hub_days', help='Hub days: \n'
                                                                         'If the delivery method of the supplier is EXW (ExWorks), hub days is 0.\n'
                                                                         'Otherwise it is set to the additional days parameter of the supplier.')
    computed_buffer_days = fields.Integer('Computed buffer days', compute='_calc_comp_buffer_days')
    buffer_days = fields.Integer('Buffer days', required=True, readonly=False, default=0, help='Buffer days. A number of days to be added to the date calculation')
    #supplier_partner_days_add = fields.Integer(related='')
    customer_partner_days_add = fields.Integer('Additional days', compute='_calc_add_days', help='The number of additional days for the customer.')
    shipping_days = fields.Integer('Days shipping', help='Number of days in shipping.', compute='_calc_shipping_days')
    requested_delivery = fields.Date('Requested delivery', related='sale_id.requested_delivery_date', readonly=True, help='The requested delivery date')
    updated_delivery = fields.Date('Updated delivery date', readonly=True)
    delivery_date = fields.Date('Delivery date', compute='_get_delivery_date')
    deviating_shipping_date = fields.Boolean('Deviating shipping date', help='Confirmed shipping date is too late or too early', compute='_calc_deviating_shipping_date')
    #expected_delivery = fields.Date('Expected delivery date', compute='_calc_expected_delivery')
    shipping_calc_status = fields.Char('Status', readonly=True)
    wkng_gerber = fields.Boolean('Wkng Gerber', compute='_calc_wkng_gerber')
    consider_wkng_gerber = fields.Boolean('Partner Wkng Gerber', compute='_calc_consider_wkng_gerber', invisible=True)
    wkng_gerber_field = fields.Boolean('Wkng Gerber Approved', default=False, readonly=True, help='The Gerber has been approved',
            states={'draft': [('readonly', False)], 'sent': [('readonly',False)], 'bid': [('readonly',False)]})
    #hide_bid_date = fields.Boolean('Hide the bid deadline', default=False)
    tooling_order = fields.Boolean(string='Is a tooling PO?', compute='_calc_tooling_order', help='is this a tooling-only po')
