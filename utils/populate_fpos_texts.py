#!/usr/bin/env python
import odoorpc
from fpos_config import fpos_config, fpos_text

o = odoorpc.ODOO.load('staging')
#o = odoorpc.ODOO.load('dev_tut')
acc_m = o.env['account.account']
fp_m = o.env['account.fiscal.position']
afp_m = o.env['account.fiscal.position.account']

companies = {'Elmatica AS': 1,
             'Elmatica GmbH': 3,
            'Elmatica AB': 5}

countries = {'n': 1,
             'd': 3,
             's': 5}

def add_pair(acc):
    print "add_pair", acc

    os.exit(0)

def get_acc_txt(a):
    idd = a[0]
    acc_data = acc_m.read([idd], ['company_id', 'code'])[0]
    comp_name = acc_data['company_id'][1]

    if comp_name == 'Elmatica AS':
        comp = 'n'
    elif comp_name == 'Elmatica GmbH':
        comp = 'd'
    elif comp_name == 'Elmatica AB':
        comp = 's'
    else:
        assert False, '??? %s' % comp_name

    return str(comp + acc_data['code'])

for k,v in fpos_config.items():
    print k
    print v
    idd = fp_m.search([('name','=',k)])
    print idd
    assert len(idd)==1
    accounts = fp_m.read(idd, ['account_ids'])[0]['account_ids']
    found_pairs = set()
    for acc in afp_m.read(accounts, ['account_src_id', 'account_dest_id']):
        print 'ACC', acc
        pair = (get_acc_txt(acc['account_src_id']), get_acc_txt(acc['account_dest_id']))
        print k, "PAIR", pair, pair in v
        assert pair in v, 'Please add to config %s into %s' % (pair, v)
        found_pairs.add(pair)
        #if not pair in v:
        #    add_pair(acc)

    print "FOUND", found_pairs, "VS", v
    print k, "D1", found_pairs.difference(v)
    print k, "D2", set(v).difference(found_pairs)


for k,v in fpos_text.items():
    config_txt = v # .encode('utf-8')
    idd = fp_m.search([('name','=',k)])
    print idd
    assert len(idd)==1
    dbtxt = fp_m.read(idd, ['situation_text'])[0]['situation_text']
    #print "COMP", dbtxt, 'vs', config_txt, 'CHECK', type(dbtxt), type(config_txt)
    if dbtxt != config_txt:
        print "WRITING", dbtxt
        fp_m.write(idd, {'situation_text': config_txt})