#!/usr/bin/env python

"""
Tools to handle the different tax and accounting situations.

https://docs.google.com/spreadsheets/d/1SBCQEisRwzAYnosSb0E6Q2OAN2ELFyCJzvsq_6iRVvk/edit#gid=0

Code here is copied from elmatica_complete, since we'll retire that at some point.
"""

from openerp import exceptions, models, _
import logging
_logger = logging.getLogger(__name__)


def combine(cust, deliver, supply):
    if (cust == 'cust_no' and deliver == 'deliver_eu') or \
        (cust in ('cust_de', 'cust_eu') and deliver == 'deliver_eu'):
        return '_'.join([cust, deliver, supply])
    else:
        return '_'.join([cust, deliver])


def calc_fiscal_position(order, company, shipping, customer, supplier, direction='customer'):
    country_obj = order.env['res.country']
    customer_in_eu = customer.is_in_eu
    supplier_in_eu = supplier.is_in_eu
    customer_country = customer.country_id
    supplier_country = supplier.country_id
    shipping_country = shipping.country_id
    """

        self.supplier_in_germany = order_info.supplier.country_id == germany
        self.customer_in_germany = order_info.customer_country == germany
        self.supplier_in_eu = order_info.supplier.is_in_eu
        self.customer_in_eu = order_info.customer.is_in_eu
        self.customer_country = order_info.customer.country_id
        self.shipping_country = order_info.address.country_id
        self.company = order_info.company_id
        self.direction = 'customer'
    """


    _logger.info("calc_fiscal")
    deliver_in_eu = shipping_country.is_in_eu
    germany = country_obj.search([('code', '=', 'DE')])[0]
    norway = country_obj.search([('code', '=', 'NO')])[0]

    _logger.info('calc_fiscal customer_in_eu %s supplier_country %s supplier_in_eu %s' %
                    (customer_in_eu, supplier_country.name, supplier_in_eu))
    fiscal_name = None

    countries = set([customer_country,
        supplier_country,
        shipping_country])
    if len(countries) == 3 and (customer_in_eu or supplier_in_eu):
        fiscal_name = 'triangular'

        if direction == 'supplier':
            fiscal_name = 'supplier_%s' % fiscal_name
        return fiscal_name # The triangular case is settled.

    # Follow the new fules
    # https://docs.google.com/spreadsheets/d/1_8knJNHMG3LDaCwfR7F0e97PrnWDRRscjs7iz9e2wL8/edit#gid=1597961966
    cust = None
    if customer_country == norway:
        cust = 'cust_no'
    elif customer_country == germany:
        cust = 'cust_de'
    elif customer_in_eu:
        cust = 'cust_eu'
    else:
        cust = 'cust_non_eu'

    deliver = None
    if shipping_country == norway:
        deliver = 'deliver_no'
    elif shipping_country == germany:
        deliver = 'deliver_de'
    elif deliver_in_eu:
        deliver = 'deliver_eu'
    else:
        deliver = 'deliver_non_eu'

    supply = None
    if supplier_in_eu:
        supply = 'supply_eu'
    else:
        supply = 'supply_non_eu'
        
    fiscal_name = combine(cust, deliver, supply)    
    return fiscal_name
    # Bygones...

    if direction == 'supplier':  # Supplier invoice
        _logger.info('calc_fiscal supplier')
        if company.country_id == germany:
            _logger.info('calc_fiscal supplier germany')
            # Default config is 19% VAT and 5400/5800. i.e. German supplier

            # if self.get_supplier().country_id == germany:
            #    fiscal_name += 'any_any_DE'
            if customer_in_eu:
                if supplier_in_eu and deliver_in_eu:
                    # Might be three party
                    countries = set([customer_country,
                                    supplier_country,
                                    shipping_country])
                    _logger.info('calc_fiscal supplier countries', countries)
                    if len(countries) == 3:
                        fiscal_name = 'supp_triangular'
                elif not supplier_country == germany and supplier_in_eu:
                    fiscal_name = 'supp_any_non-eu_non-german-eu'
                else:
                    fiscal_name = 'supp_eu_any_non-eu'
            else:
                fiscal_name = 'supp_non-eu_non_eu'


    else:
        _logger.info('calc_fiscal customer country %s customer_in_eu %s deliver_in_eu %s' %
                        (company.country_id.name, customer_in_eu, deliver_in_eu))
        # Customer invoice
        if company.country_id == norway:
            if customer_country == norway or shipping_country == norway:
                fiscal_name = 'cust_nor'
            elif not deliver_in_eu:
                fiscal_name = 'cust_any_non-eu_any'
        else:
            countries = set([customer_country,
                supplier_country,
                shipping_country])
            _logger.info('calc_fiscal cust countries %s', countries)
            if len(countries) == 3:
                fiscal_name = 'triangular'
            elif shipping_country == germany:
                fiscal_name = 'cust_germany'
            else:
                if customer_in_eu and not deliver_in_eu:
                    fiscal_name = 'cust_eu_non-eu'
                else:
                    fiscal_name = 'cust_not_germany'

    _logger.info('calc_fiscal returning name %s' % fiscal_name)

    return fiscal_name


def calc_invoice_company(order):
    """
    Simple rules: If the customer or delivery country is Norway, or customer is outside of EU:
    invoice from Norway. Otherwise: Invoice from Germany.

    :param env: Odoo connection
    :param order: Sales order
    :return:invoicing country
    """
    country_obj = order.env['res.country']
    germany = country_obj.search([('code', '=', 'DE')])[0]
    norway = country_obj.search([('code', '=', 'NO')])[0]
    elmatica_as = order.env['res.company'].search([('partner_id.country_id','=',norway.id)])[0]
    elmatica_gmbh = order.env['res.company'].search([('partner_id.country_id','=',germany.id)])[0]

    customer_country = order.partner_id.country_id
    delivery_country = order.partner_shipping_id.country_id

    if customer_country == norway:
        if delivery_country == norway:
            return elmatica_as
        elif not delivery_country.is_in_eu:
            return elmatica_as
    elif not customer_country.is_in_eu and not customer_country.is_in_eu:
        return elmatica_as

    return elmatica_gmbh

def get_default_account(product, direction='purchase'):
    """
    account = direction=='purchase' and product.property_account_expense or product.property_account_income
    if not account:
        account = direction=='purchase' and product.categ_id.property_account_expense_categ or \
            product.categ_id.property_account_income_categ
    """

    property_name = [('name','=','property_account_income')]
    template_res = [('res_id', '=', 'product.template,%d' % product.product_tmpl_id.id)]
    company = [('company_id','=',product.company_id.id)]
    prop = product.env['ir.property']
    inc_prop = prop.search(property_name + template_res + company) or prop.search(property_name + template_res)

    if not inc_prop:
        # Look at the category
        property_name = [('name','=','property_account_income_categ')]
        categ_res = [('res_id','=','product.category,%d' % product.categ_id.id)]
        inc_prop = prop.search(property_name + categ_res + company) or prop.search(property_name + categ_res)

    account = inc_prop.get_by_record(inc_prop)
    if not account:
        raise exceptions.Warning('No income account set for product %d - %s' % (product.id, product.name))
    assert account, 'No account from %s for %s' % (inc_prop, product)
    return account


def get_default_taxes(pcb_product, direction='purchase'):
    _logger.info('Looking for taxes for product %d - %s' % (pcb_product.id, pcb_product.name))
    taxes_to_apply = []
    taxes_to_apply = [x.id for x in pcb_product.taxes_id]
    if len(taxes_to_apply) == 0:
        if direction=='purchase':
            account = pcb_product.property_account_expense
        else:
            account = pcb_product.property_account_income

        if account:
            taxes_to_apply += [x.id for x in account.tax_ids]
        else:
            if direction=='purchase':
                account = pcb_product.categ_id.property_account_expense_categ
            else:
                account = pcb_product.categ_id.property_account_income_categ
            if account:
                taxes_to_apply += [x.id for x in account.tax_ids]

    if len(taxes_to_apply) > 0:
        _logger.info('TAXES FOR %s is %s' % (pcb_product.name, taxes_to_apply))
        return [(6, 0, taxes_to_apply)]
    else:
        _logger.info('No taxes found for %d - %s' % (pcb_product.id, pcb_product.name))
        return None

def prepare_order_invoice_line(order, info):
        company = calc_invoice_company(order) # Why?
        info['company_id'] = company.id
        shipping_country = order.partner_shipping_id

        position_name = calc_fiscal_position(order, company, shipping_country, order.partner_id, order.selected_supplier)
        fpos = order.env['account.fiscal.position'].search([('name','=',position_name)])
        if not fpos:
            raise exceptions.Warning('Unknown fiscal position %s' % position_name)
        fpos = fpos[0]

        product = order.env['product.product'].browse([info['product_id']])[0]
        if not info['account_id']:
            account = get_default_account(product, 'sale')
        else:
            account = order.env['account.account'].browse([info['account_id']])[0]

        assert account, 'Account not set from either %s or %s' % (info['account_id'], product)
        new_account = fpos.map_account(account)
        assert new_account, 'Position %s has no mapping for account %s' % (position_name, account)

        # TODO Maybe map the taxes too...
        #if not info['invoice_line_tax_id'] or not info['invoice_line_tax_id'][0][2]:
        #    product = order.env['product.product'].browse([info['product_id']])[0]
        taxes_to_apply = [x.id for x in new_account.tax_ids]
        info['invoice_line_tax_id'] = [(6, 0, taxes_to_apply)]
            #info['invoice_line_tax_id'] = get_default_taxes(product, new_account, 'sale')

        info['account_id'] = new_account.id
        return info

def prepare_invoice(order, info):
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