#-.- coding: utf-8 -.-

s_sale = 'n3000'
s_nre = 'd8400'
s_freight = 'n3520'



fpos_config = {
	'cust_no_deliver_no' : [('s1500', 'n3000'), (s_sale, 'n3000'), (s_nre, 'n3000'), (s_freight, 'n3520')],
	'cust_no_deliver_non_eu' : [(s_sale, 'n3100'),  ('s1500', 'n3100'), (s_nre, 'n3000'), (s_freight, 'n3521')],
	'cust_non_eu_deliver_non_eu': [(s_sale, 'n3100'), ('s1500', 'n3100'), (s_nre,'n3100'), (s_nre, 'n3100'), (s_freight, 'n3521')],
	'cust_no_deliver_eu_supply_eu': [(s_sale, 'd4130'), ('s1500', 'd4130'), (s_nre, 'd4130'), (s_freight, 'd4132')],
	'cust_no_deliver_eu_supply_non_eu': [('s1500', 'd4125'), (s_sale, 'd4125'),  (s_nre, 'd4125'), (s_freight, 'd4126')],
	'cust_de_deliver_de': [(s_sale, 'd4400'),  ('s1500', 'd4400'), (s_nre, 'd4400'), (s_freight, 'd4405')],
	'cust_eu_deliver_non_eu': [(s_sale, 'd4339'), ('s1500', 'd4339'), (s_nre, 'd4339'), (s_freight, 'd4338')],
	'cust_de_deliver_eu_supply_non_eu': [('s1500', 'd4125'), (s_sale, 'd4125'), (s_nre, 'd4125'), (s_freight, 'd4126')],
	'cust_eu_deliver_eu_supply_non_eu': [('s1500', 'd4125'), (s_sale, 'd4125'), (s_nre, 'd4125'), (s_freight, 'd4126')],
	'cust_de_deliver_eu_supply_eu': [(s_sale, 'd4130'), ('s1500', 'd4130'), (s_nre, 'd4130'), (s_freight, 'd4132')],
	'cust_eu_deliver_eu_supply_eu': [(s_sale, 'd4130'), ('s1500', 'd4130'), (s_nre, 'd4130'), (s_freight, 'd4132')],
	'triangular': [('s1500', 'd4130'), (s_sale, 'd4130'), (s_nre, 'd4130'), (s_freight, 'd4132')],
	'cust_eu_deliver_de': [(s_sale, 'd4400'),  ('s1500', 'd4400'), (s_nre, 'd4400'), (s_freight, 'd4405')],

}

fpos_text = {
	'cust_no_deliver_no' : u'',
	'cust_no_deliver_non_eu' : u'',
	'cust_non_eu_deliver_non_eu': u'',
	'cust_no_deliver_eu_supply_eu': u'',
	'cust_no_deliver_eu_supply_non_eu': u'',
	'cust_de_deliver_de': u'',
	'cust_eu_deliver_non_eu': u'',
	'cust_de_deliver_eu_supply_non_eu': u'',
	'cust_eu_deliver_eu_supply_non_eu':u'',
	'cust_de_deliver_eu_supply_eu': u"Steuerfreie innergemeinschaftliche Lieferung. \n" \
                + u"Tax free intracommunity delivery - the acquirer is liable for reverse charge",
	'cust_eu_deliver_eu_supply_eu': u"Steuerfreie innergemeinschaftliche Lieferung. \n" \
                + u"Tax free intracommunity delivery - the acquirer is liable for reverse charge",
	'triangular': u"Innergemeinschaftliches Dreiecksgeschäft (Art. 141 MwStSyst RL); " \
                + u"Für die Mehrwertsteuer muss der Empfänger aufkommen\n" \
                + u"VAT: EC Article 28 c E (3) Simplification Invoice; the recipient is liable\n" \
                + u"for VAT",
	'cust_eu_deliver_de': u'',

}