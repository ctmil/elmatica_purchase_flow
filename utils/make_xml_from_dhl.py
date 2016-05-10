#!/usr/bin/env python
#import lxml.etree
#import lxml.builder
import sys
from yattag import Doc, indent
import string
import odoorpc

o = odoorpc.ODOO.load('elmatica-staging')
resc = o.env['res.country']


doc, tag, text = Doc().tagtext()
shippingfile = open('shipping_days.tsv')
shippingfile.readline()

model = 'elmatica_purchase_flow.shipping_days'
identifiers = []

with tag('openerp'):
	with tag('data'):
		for line in shippingfile:
			x = line.strip().split('\t')
			country, code, zone, days = line.strip().split('\t')
			#cc = [1]
			cc = resc.search([('code','=',code)])			
			assert len(cc)<2
			if len(cc)==0:
				#print 'CODE NOT FOUND %s - %s' % (code, country)
				continue
			code = code.replace('GB', 'UK')
			"""
        		<record id="shipping_norway" model="elmatica_purchase_flow.shipping_days">
		            <field name="to_country" ref="base.no" />
		            <field name="shipping_days">4</field>
		        </record>
			"""
			countryname = ''.join([x for x in country if x in string.ascii_letters])
			assert not countryname in identifiers
			identifiers.append(countryname)

			with tag('record', id='shipping_%s' % countryname, model=model):
				with tag('field', name='to_country', ref='base.%s' % code.lower()):
					pass
				with tag('field', name='shipping_days'):
					text(days)


result = indent(doc.getvalue(), indentation=4*' ', newline = '\n')

print result
