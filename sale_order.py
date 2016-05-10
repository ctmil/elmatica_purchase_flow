#-.- encoding: utf-8 -.-

from openerp import api, models, exceptions, fields,  _
import openerp.addons.decimal_precision as dp

import logging
import datetime
from situation import *

tooling_products = ['[TOOLING]']


_logger = logging.getLogger(__name__)

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'


    # Method overridden to set the analytic account by default on criterion match
    # TBRI Må sikkert på plass igjen.
#    @api.multi
#    def invoice_line_create(self):
#        create_ids = super(sale_order_line, self),invoice_line_create()
#        #self.ensure_one()
#
#        ids = [x.originating_from.id for x in self if x.originating_from]
#
#        self._cr.execute("""
#  select sol.id as sale_order_line_id, pol.id as purchase_order_line_id
#  from sale_order_line sol
#  --left join sale_order so on so.id=sol.order_id
#  left outer join purchase_order_line pol on pol.sale_order_line=sol.id
#  where sol.id in %s
#""", (tuple(ids),))


#        for item in self._cr.dictfetchall():
#            sol = item['sale_order_line_id']
#            pol = item['purchase_order_line_id']
#            for sale_order_line in self:
#                if sale_order_line.originating_from and sol==sale_order_line.originating_from.id:
#                    po_line = self.env['purchase.order.line'].browse(pol)
#                    invo_line = self.env['account.invoice.line'].browse(create_ids)
#                    _logger.info('%s Writing ordered_quantity? = %s', invo_line, po_line)
#                    total_qty = po_line.delivered_qty and po_line.delivered_qty or 0
#                    total_qty += po_line.undelivered_qty and po_line.undelivered_qty or 0

#                    invo_line.ordered_quantity = total_qty
#                    _logger.info('%s Writing ordered_quantity = %d', invo_line, total_qty)

#        return create_ids


    @api.v8
    def _prepare_order_invoice_line(self, info, account_id=False):
        order = self.order_id
        return prepare_order_invoice_line(order, info)

    @api.v7
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        info = super(sale_order_line, self)._prepare_order_line_invoice_line(cr, uid, line, account_id, context)
        #line_obj = self.browse(cr, uid, [line])
        info = line._prepare_order_invoice_line(info)
        print "INFO LINE", info, 'and line', line
        return info

    @api.multi
    def _calc_delivered_qty(self):
        ids = [x.id for x in self if type(x.id)==int]
        if len(ids)==0:
            # It could be a NewId
            for l in self:
                l.delivered_qty = 0
                l.undelivered_qty = 0
            return
        _logger.info('%s calc_delivered_qty checking for ids %s', self, ids)

        self._cr.execute("""
        select sol.originating_from as org_id, sol.id as lineid from sale_order_line sol where sol.originating_from in %s
        """, (tuple(ids),))
        originators = {}
        for item in self._cr.dictfetchall():
            if not item['org_id'] in originators:
                originators[item['org_id']] = []
            originators[item['org_id']].append(item['lineid'])
        _logger.info('ORIGI %s', originators)

        self._cr.execute("""
  select sol.id as sale_order_line_id, sol.order_id, sp.name, sm.product_uom_qty,sm.state as move_state,
    sp.name,coalesce(spt.code, 'nada') as picking_type
  from sale_order_line sol
  --left join sale_order so on so.id=sol.order_id
  left outer join purchase_order_line pol on pol.sale_order_line=sol.id
  left outer join stock_move sm on sm.purchase_line_id=pol.id
  left outer join stock_picking sp on sm.picking_id=sp.id
  LEFT outer JOIN stock_picking_type spt on (spt.id=sp.picking_type_id)
  where sol.id in %s
""", (tuple(ids),))

        tmp = {}
        # https://www.odoo.com/es_ES/forum/help-1/question/showing-delivery-information-on-sales-orders-72892
        for item in self._cr.dictfetchall():
            if item['move_state'] == 'cancel':
                continue

            if item['picking_type'] == 'nada':
                continue

            sign = item['picking_type'] in ('incoming', 'nada') and 1 or -1
            sol = item['sale_order_line_id']
            if not sol in tmp:
                tmp[sol] = {'done' : 0.0, 'assigned': 0.0}

            tmp[sol][item['move_state']] += sign * item['product_uom_qty']

        for line in self:
            if not line.id in tmp:
                continue

            # Find previously invoiced lines
            def collect(line, zum=0):
                _logger.info('CollectX %s %s', line, zum)
                if zum: # All lines except the first one...
                    assert line.invoiced

                zum += line.invoiced_qty
                if not line.id in originators:
                    _logger.info('CollectXX %s %s', line, zum)
                    return zum



                org = self.browse(originators[line.id])
                for o in org:
                    zum += collect(o, 0)
                    _logger.info('CollectXXX %s %s %s', line, o, zum)
                return zum

            _logger.info('Done QTY = %d', tmp[line.id]['done'])
            previous = collect(line)
            delivered = tmp[line.id]['done'] - previous
            assert delivered >= 0
            line.delivered_qty =  delivered
            line.undelivered_qty = tmp[line.id]['assigned']



    @api.multi
    def XX_calc_delivered_qty(self):
        ids = [x.id for x in self]
        self._cr.execute("""
        select sol.originating_from as org_id, sol.id as lineid from sale_order_line sol where sol.originating_from in %s
        """, (tuple(ids),))
        originators = {}
        for item in self._cr.dictfetchall():
            originators[item['org_id']] = item['lineid']
        _logger.info('ORIGI %s', originators)

        self._cr.execute("""
  select sol.id as sale_order_line_id, sol.order_id, sp.name, sm.product_uom_qty,sm.state as move_state,
    sp.name,coalesce(spt.code, 'nada') as picking_type
  from sale_order_line sol
  --left join sale_order so on so.id=sol.order_id
  left outer join purchase_order_line pol on pol.sale_order_line=sol.id
  left outer join stock_move sm on sm.purchase_line_id=pol.id
  left outer join stock_picking sp on sm.picking_id=sp.id
  LEFT outer JOIN stock_picking_type spt on (spt.id=sp.picking_type_id)
  where sol.id in %s
""", (tuple(ids),))

        tmp = {}
        # https://www.odoo.com/es_ES/forum/help-1/question/showing-delivery-information-on-sales-orders-72892
        for item in self._cr.dictfetchall():
            if item['move_state'] == 'cancel':
                continue

            if item['picking_type'] == 'nada':
                continue

            sign = item['picking_type'] in ('incoming', 'nada') and 1 or -1
            sol = item['sale_order_line_id']
            if not sol in tmp:
                tmp[sol] = {'done' : 0.0, 'assigned': 0.0}

            tmp[sol][item['move_state']] += sign * item['product_uom_qty']

            lineinfo = {}
            #newline_id = line.id in originators and originators[line.id] or None
            def dive_in(lineinfo, line, total, original, remain):
                print "DIVE_IN", lineinfo.keys()

                _logger.error('%s dive_in tot=%d org=%d remain=%d', line, total, original, remain)
                newline_id = line.id in originators and originators[line.id] or None
                newline = self.browse(newline_id)
                if newline_id:
                    assert newline.order_id == line.order_id, 'Confused %s vs %s' % (newline.order_id, line.order_id)

                    assignit = min(line.product_uom_qty, remain)
                    _logger.info('assigning %s to %s', assignit, line.id)
                    lineinfo[line.id]['delivered_qty'] = assignit
                    lineinfo[line.id]['undelivered_qty'] = 0

                    remain -= assignit
                    _logger.info('%s dive2 %s', line, newline)
                    dive_in(lineinfo, newline, total, original, remain)
                else:
                    _logger.info('%s dive3 %s', line, remain )
                    _logger.info('assigning2 %s to %s', remain, line.id)
                    lineinfo[line.id]['delivered_qty'] = remain
                    lineinfo[line.id]['undelivered_qty'] = total

        lineinfo = {}
        for n in originators.keys():
            lineinfo[n] = {}
        for n in tmp.keys():
            lineinfo[n] = {}
        for n in originators.values():
            lineinfo[n] = {}

        for order in [x.order_id for x in self]:
            for line in order.order_line:
                lineinfo[line.id] = {}
                if line.id in originators:
                    dive_in(lineinfo, line, tmp[line.id]['assigned'], tmp[line.id]['done'], tmp[line.id]['done'])
                else:
                    lineinfo[line.id]['delivered_qty'] = line.id in tmp and tmp[line.id]['done'] or 0
                    lineinfo[line.id]['undelivered_qty'] = line.id in tmp and tmp[line.id]['assigned'] or 0

        _logger.info('lineinfo %s and %s', lineinfo, self)
        for line in self:
            _logger.info('Looking for %s ... %s', line.id, lineinfo.get(line.id, None))
            if line.id in lineinfo:
                line.delivered_qty = lineinfo[line.id]['delivered_qty']
                line.undelivered_qty = lineinfo[line.id]['undelivered_qty']

            """
            if not line.id in tmp:
                line.delivered_qty = line.product_uom_qty
                line.undelivered_qty = 0
            else:
                line.delivered_qty = tmp[lime.id][]
            """



    delivered_qty = fields.Float('Delivered', compute='_calc_delivered_qty')
    invoiced_qty = fields.Float('Invoiced', copy=False)
    undelivered_qty = fields.Float('Unelivered', compute='_calc_delivered_qty')
    originating_from = fields.Many2one('sale.order.line', string='Originating from', copy=False)

def show_warning_action(self, warning):
    warning_form = self.env.ref('elmatica_purchase_flow.view_send_warning', False)
    assert warning_form, 'Unable to load the form'
    ctx = self._context.copy()
    ctx.update(warning=warning, default_requested_delivery_date=self.requested_delivery_date, default_order=self.id, default_warning=warning)
    _logger.info('WARNING %s', warning)

    #res = {'warning': {
    #        'title': _('Warning'),
    #        'message': _('My warning message.')
    #    }}
    #    #return res
    print('TRYING TO MAKE A WARNING')
    return {
        'name': _('Warning'),
        'type': 'ir.actions.act_window',
        'view_type': 'form',
        'view_mode': 'form',
        'res_model': 'elmatica_purchase_flow.warning',
        'views': [(warning_form.id, 'form')],
        'view_id': warning_form.id,
        'target': 'new',
        'context': ctx,
    }



class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _get_main_product_line(self):
        for order in self:
            for line in order.order_line:
                if line.product_id.product_tmpl_id.ntty_id:
                    order.main_product_line = line

    @api.multi
    def _get_tooling_product_line(self):
        for order in self:
            for line in order.order_line:
                if line.product_id.nre_product:
                    order.tooling_product_line = line

                matches = [x for x in tooling_products if line.name.find(x)==0]
                if matches:
                    order.tooling_product_line = line

    @api.multi
    def action_create_purchase_order(self):
        print "SELF", self, "CTX", self._context

        names_to_skip = [x.upper() for x in ['DHL_DELIVERY',
                                'C_SHIPPING',
                                'LOCAL FREIGHT',
                                'FCA',
                                'info:']]
        domain_to_skip = [('name','ilike',x) for x in names_to_skip]
        pipes = ['|' for x in range(len(domain_to_skip)-1)]
        domain_to_skip = pipes + domain_to_skip

        products_to_skip = self.env['product.product'].search(domain_to_skip)
        _logger.debug('Product names to skip %s - %s', domain_to_skip, products_to_skip)

        for sale in self:
            _logger.info('Creating purchase order %s %s', sale.name, self._context)
            if self._context.get('updated_requested_delivery_date', False):
                sale.requested_delivery_date = self._context.get('updated_requested_delivery_date')

            if not sale.requested_delivery_date:
                raise exceptions.ValidationError(_('Requested delivery date not set for sales order %s' % sale.name))
            elif (fields.Date.from_string(sale.requested_delivery_date) - datetime.date.today()) < datetime.timedelta(days=10):
                skip_check_requested_delivery_date = self._context.get('skip_check_requested_delivery_date', False)
                _logger.info('Skip? %s Requested delivery date %s today %s', skip_check_requested_delivery_date, sale.requested_delivery_date, fields.Date.from_string(sale.requested_delivery_date)-datetime.date.today())
                if not skip_check_requested_delivery_date:
                    warning = _('The requested delivery date for %s does not seem to be valid.' % self.name)
                    return show_warning_action(self, warning)

            customer_location = self.env['ir.property'].with_context(company_id=sale.company_id).search([('name','=','property_stock_customer')])[0]
            #pricelist = self.env['ir.property'].with_context(company_id=sale.company_id).search([('name','=','property_product_pricelist_purchase')])[0]
            #pricelist_ref = int(pricelist.value_reference.split(',')[-1])
            location_ref = int(customer_location.value_reference.split(',')[-1])


            # Use the currency of the supplier pricelist.
            pricelist_ref = sale.selected_supplier.property_product_pricelist_purchase
            if pricelist_ref and pricelist_ref.currency_id:
                purchase_currency = pricelist_ref.currency_id
            else:
                purchase_currency = None

            supplier = sale.selected_supplier
            print "CUSTLOC", customer_location, location_ref, type(location_ref)
            po = {'company_id': sale.company_id.id,
                  'currency_id': purchase_currency and purchase_currency.id,
                  #'name': sale.name,
                  'partner_id': supplier.id,
                  'location_id': location_ref,
                  'pricelist_id': pricelist_ref.id,
                  'invoice_method': 'manual',
                  'date_order': fields.Date.context_today(self),
                  'dest_address_id': sale.partner_shipping_id.id,
                  }
            tooling_po = po.copy()
            po_lines = []
            tooling_lines = []

            lines = self.env['sale.order.line'].search([('order_id','=',sale.id)])
            index = 0
            for line in lines:
                if line.product_id.name.upper() in names_to_skip:
                    _logger.info('Not making PO line for product %s', line.product_id)
                    continue
                else:
                    _logger.info('Making PO line for product %s', line.product_id)

                selling_currency = sale.pricelist_id and sale.pricelist_id.currency_id
                cost_unit = sale.find_cost(selling_currency, purchase_currency, supplier, line, line.product_id, line.out_delay, line.product_uom_qty)
                linedata = {'name': line.name,
                                'product_uom': line.product_uom.id,
                                'sale_order': sale.id,
                                'sale_order_line': line.id,
                                'price_unit': cost_unit,
                                'leadtime': line.delay,
                                'sequence': line.sequence + index,
                                'product_qty' : line.product_uom_qty,
                                'company_id': line.company_id.id,
                                'product_id': line.product_id.id,
                                'date_planned': sale.requested_delivery_date, # Must be updated later.
                    }

                matches = [x for x in tooling_products if line.name.find(x)==0]
                if matches:
                    tooling_lines.append((0 ,0, linedata))
                else:
                    po_lines.append((0, 0, linedata))
                index += 1

            po['order_line'] = po_lines
            _logger.info('Creating purchase order %s', po)
            created_po = self.env['purchase.order'].create(po)
            created_po.force_calculate_shipping_date()
            if len(tooling_lines) > 0:
                tooling_po['order_line'] = tooling_lines
                _logger.info('Creating tooling purchase order %s', tooling_po)
                created_tooling_po = self.env['purchase.order'].create(tooling_po)
                created_tooling_po.force_calculate_shipping_date()
                _logger.info('Created tooling purchase order %s / %s', created_tooling_po, created_tooling_po.name)

            required_shipping_date, delivery_date = created_po.calculate_shipping_date()
            for line in created_po.order_line:
                line.date_planned = required_shipping_date

            _logger.info('Created purchase order %s / %s', created_po, created_po.name)

    def find_cost(self, selling_currency, purchase_currency, supplier, line, product, leadtime, qty):
        self.ensure_one()

        # We are looking at cost in supplier currency now. Right?
        if line.price_unit_supplier_currency:
            return line.price_unit_supplier_currency

        if selling_currency != purchase_currency:
            raise exceptions.Warning(_('Selling currency is %s while supplier currency is %s. '
                                       'And we have no cost in supplier currency.'
                                       % (selling_currency.name, purchase_currency.name)))

        # This is history right now.
        sso = self.super_order_id

        sso_lines = self.env['super.sales.line'].search([('super_order_id','=',sso.id),
            ('product_id','=',product.id)])\

        matching_sso_lines = [ x for x in sso_lines if not round(abs(x.product_qty - qty)) and x.delay==leadtime and x.selected_supplier == self.selected_supplier]

        if len(matching_sso_lines) == 1:
            cost = matching_sso_lines[0].price_unit
        elif len(sso_lines)>0:
            raise exceptions.ValidationError(_('Unable to find line in %s for product %s with \n'
                                               'leadtime %d supplier %s \n'
                                               'and quantity %d.') %
                          (sso.name, product.name, leadtime, self.selected_supplier.name, qty)
                          )
        else:
            _logger.info('Unable to determine SSO line: %s - %s' % (self.name, product.name))
            cost = product.standard_price

        return cost



    @api.multi
    def _has_purchase_order(self):
        po_line_model = self.env['purchase.order.line']
        for order in self:
            has_lines = po_line_model.search_count([('sale_order','=',order.id)])
            print "HAS_PURCHASE_ORDER", has_lines
            order.has_purchase_order = has_lines > 0

    @api.multi
    def _has_super_sales_order(self):
        for order in self:
	     order.has_super_order_id = False
    #        try:
    #            order.has_super_order_id = bool(order.super_order_id)
    #        except:
    #            # Probably elmatica_super_sales_order has not been installed.
    #            order.has_super_order_id = False
    #        print "HAS SSO", order.has_super_order_id

    def _get_all_purchase_orders(self):
        po_line_model = self.env['purchase.order.line']

        lines = po_line_model.search([('sale_order','=',self.id)])
        po_ids = set([x.order_id for x in lines])
        return po_ids


    @api.multi
    def _get_purchase_order(self):
        for order in self:
            po_ids = [x for x in order._get_all_purchase_orders() if not x.is_tooling()]
            if len(po_ids) > 1:
                _logger.error('There are more than one PO related to the SO %s', order.name)
            elif len(po_ids) == 1:
                order.purchase_orders = po_ids.pop()


    @api.multi
    def _get_tooling_purchase_order(self):
        for order in self:
            po_ids = [x for x in order._get_all_purchase_orders() if x.is_tooling()]
            if len(po_ids) > 1:
                raise exceptions.ValidationError('There are more than one tooling PO related to the SO %s' % order.name)
            elif len(po_ids) == 1:
                order.tooling_purchase_order = po_ids.pop()

    @api.multi
    @api.depends('name', 'order_line') # used to be out_delay too
    def _calc_required_shipping(self):
        info_product = self.get_info_product()
        ids = [x.id for x in self if type(x.id)==int]
        if not ids:
            _logger.info('The ids were %s', [(x.id, type(x.id)) for x in self])
            # Hm, For some reason we were called there with only NewId instances.
            for order in self:
                order.required_shipping_date = order.requested_delivery_date
            return

        delays = dict([(x, 0) for x in ids])

        self._cr.execute('select order_id, so.name, sum(1) as sol_delay '
                     'from sale_order_line sol '
                    'join sale_order so on so.id=sol.order_id '
                             'where sol.product_id=%s and so.id in %s'
                         'group by order_id, so.name', (info_product,
                                                                         tuple(ids),))

        for info in self._cr.dictfetchall():
            if info['sol_delay']:
                delays[info['order_id']] += info['sol_delay']
        _logger.info('required_shipping delays %s', delays)
        for order in self.browse(delays.keys()):
            leadtime_for_order = delays[order.id]
            required_shipping_date = fields.Date.from_string(order.requested_delivery_date) - datetime.timedelta(days=leadtime_for_order)
            _logger.info('%s leadtime required_shipping %s', order.name, required_shipping_date)
            order.required_shipping_date = required_shipping_date

    def get_info_product(self):
        " TODO De-duplicate this method (it's in purchase_order.py too) "
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

    @api.multi
    def _get_delivery_dates(self):
        po_line_model = self.env['purchase.order.line']
        for order in self:
            lines = po_line_model.search([('sale_order','=',order.id)])
            purchase_orders = set([x.order_id for x in lines])
            dates = set([x.minimum_planned_date for x in purchase_orders])
            order.delivery_dates = ','.join(dates)



    @api.v8
    def prepare_invoice(self, order, info):
        #line_objs = self.env['account.invoice.line'].browse(lines)
        #companies = set([x.company_id for x in line_objs])
        #assert len(companies)==1
        #company = companies.pop()
        if isinstance(order.id, models.Model):
            order = order.id

        company = calc_invoice_company(order) # Why?
        assert company
        info['company_id'] = company.id
        shipping_country = order.partner_shipping_id

        position_name = calc_fiscal_position(order, company, shipping_country, order.partner_id, order.selected_supplier)
        positions = order.env['account.fiscal.position'].search([])
        fpos = [x.id for x in positions if x.name == position_name]
        #fpos = order.env['account.fiscal.position'].search([('name','=',position_name)])
        _logger.info('Looking for fiscal %s - found %s out of %s', position_name, fpos, [x.name for x in positions])
        if len(fpos)==0:
            raise exceptions.Warning(_('Unknown fiscal position %s' % position_name))
        info['fiscal_position'] = fpos[0]
        info['partner_shipping_id'] = order.partner_shipping_id.id
        info['operational'] = True #Maybe already set but...
        info['incoterm'] = order.incoterm and order.incoterm.id

        print "PREPARE INVOICE", info, position_name
        return info

    @api.v7
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        info = super(sale_order, self)._prepare_invoice(cr, uid, order, lines, context)
        order_obj = self.browse(cr, uid, [order])
        for odre in order_obj:
            info = order_obj.prepare_invoice(odre, info)

        _logger.info('prepare_invoice %s', info)
        x = [(6, 0, lines)]
        assert info['invoice_line'] == x, 'Something wrong with the lines %s' % info['invoice_line']
        return info

    @api.multi
    def _is_portal_user(self):
        user = self.env['res.users'].browse(self._uid)
        groups = user.groups_id
        portal_groups = [x for x in groups if x.is_portal ]
        for order in self:
            order.is_portal_user = bool(portal_groups)

    @api.multi
    def write(self, vals):
        info_product = self.get_info_product()
        _logger.info('%s Writing SO lines %s', self, vals)
        if 'order_line' in vals:
            ids = [x[1] for x in vals['order_line'] if x[1]]
            ids += [x.id for x in self]
            _logger.info('Looking for ids %s', ids)
            self._cr.execute('select sol.id, order_id, so.state as so_state, so.name as so_name from sale_order_line sol '
                             'join sale_order so on so.id=sol.order_id '
                             'where sol.id in %s', (tuple(ids),))
            lines_states = {}
            for item in self._cr.dictfetchall():
                lines_states[item['id']] = (item['so_state'], item['so_name'])

            _logger.info('lines_states %s', lines_states)

            for ol in vals['order_line']:
                _logger.info('Writing SO lines %s %s', ol, ol[1] in lines_states)
                if ol[0] == 4:
                    continue
                elif ol[0] == 1:
                    state = lines_states[ol[1]][0]
                    if state not in ('draft', 'sent'):
                        raise exceptions.Warning(_('%s: Can not update lines in the current state %s.\n'
                                                   'Only add new lines for changing leadtime.' % (lines_states[ol[1]][1]), state))
                elif ol[0] == 0:
                    # Check that the product is an info product
                    lineinfo = ol[2]
                    if not lineinfo['product_id']:
                        raise exceptions.Warning(_('%s: Trying to add line without product' % lines_states[ol[1]][1]))
                    elif lineinfo['product_id'] != info_product:
                        for so in self:
                             if so.state not in ('draft', 'sent'):
                                raise exceptions.Warning(_('%s: Trying to add line with product that is not a leadtime product.' % so.name))
                    else:
                        _logger.info('Adding infoline to SO %s', self)

        return super(sale_order, self).write(vals)

    @api.multi
    @api.depends('required_shipping_date', 'purchase_delivery_date')
    def _calc_required_shipping_date_not_met(self):
        for order in self:
            assert order.required_shipping_date, 'Missing shipping date %s' % order.name
            if not order.required_shipping_date or not order.purchase_delivery_date:
                order.required_shipping_date_not_met = False
            else:
                order.required_shipping_date_not_met = order.required_shipping_date != order.purchase_delivery_date


    order_line = fields.One2many('sale.order.line', 'order_id', 'Order Lines', readonly=True, states={'manual': [('readonly', False)],'accept': [('readonly', False)], 'draft': [('readonly', False)], 'sent': [('readonly', False)]}, copy=True)
    #order_line_addable = fields.One2many('sale.order.line', compute='_get_order_lines', inverse='_write_order_line')
    has_purchase_order = fields.Boolean('Has purchase order', compute='_has_purchase_order')
    has_super_order_id = fields.Boolean('Has super sales order', compute='_has_super_sales_order')
    is_portal_user = fields.Boolean('Is portal user', compute='_is_portal_user')
    purchase_orders = fields.Many2one('purchase.order', compute='_get_purchase_order', string='PCB Purchase Order')
    tooling_purchase_order = fields.Many2one('purchase.order', compute='_get_tooling_purchase_order', string='Tooling Purchase Order')
    delivery_dates = fields.Char('Delivery date', compute='_get_delivery_dates')
    requested_delivery_date = fields.Date('Requested delivery', required=True, readonly=False, default=fields.Date.today())
    required_shipping_date = fields.Date('Required shipping', compute='_calc_required_shipping', store=True)
    required_shipping_date_not_met = fields.Boolean('Mismatch in dates', compute='_calc_required_shipping_date_not_met', store=True)
    main_product_line = fields.Many2one('sale.order.line', string='Main line', compute='_get_main_product_line')
    tooling_product_line = fields.Many2one('sale.order.line', string='Tooling line', compute='_get_tooling_product_line')
    purchase_delivery_date = fields.Date(related='purchase_orders.delivery_date')
