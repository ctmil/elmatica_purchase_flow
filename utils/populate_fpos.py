#!/usr/bin/env python

import odoorpc

o = odoorpc.ODOO.load('staging')
acc_m = o.env['account.account']
fp_m = o.env['account.fiscal.position']
afp_m = o.env['account.fiscal.position.account']
so_m = o.env['sale.order']
print 'Checking', so_m.search([('name','=', 'SO146')])

from fpos_config import fpos_config

for k,v in fpos_config.items():
	xx = list(v[0])
	xx[0] = 's1500'
	v.append(tuple(xx))


db = fp_m.read(fp_m.search([]), ['name', 'account_ids'])

def fix(k):
	"""
	KONTI [{u'code': u'3000', u'id': 163, u'company_id': [1, u'Elmatica AS']}, {u'code': u'3100', u'id': 167, u'company_id': [1, u'Elmatica AS']}]
	"""
	rv = k['company_id'][1]=='Elmatica AS' and 'n' or \
		k['company_id'][1]=='Elmatica AB' and 's' or 'd'
	assert k['company_id'][1] in ['Elmatica AS', 'Elmatica GmbH', 'Elmatica AB'], 'COMPANY %s' % k['company_id'][1]
	rv += k['code']
	return rv

positions = [x['name'] for x in db]
for pos in fpos_config:
	if not pos in positions:
		print 'must make it', pos
		idd = fp_m.create({'name': pos})
		print 'IDD', idd
		print 'Bailing out, please rerun'
		os.exit(0)


fpos_info = {}
for fpos in db:
	print 'FPOS', fpos, type(fpos)
	key = fpos['id'], fpos['name']
	if not fpos['name'] in fpos_config:
		continue
	if not key in fpos_info:
		fpos_info[key] = []
	for a in fpos['account_ids']:
		afp_m.unlink(a)
		continue	
		acc = afp_m.read(a, ['account_src_id', 'account_dest_id'])
		print 'checking accounts', acc, acc['account_src_id']
		konti = acc_m.read([acc['account_src_id'][0], acc['account_dest_id'][0]], ['company_id', 'code'])
		k1 = fix(konti[0])
		k2 = fix(konti[1])
		print "KONTI", k1, k2
		print acc
		fpos_info[key].append((k1, k2))

	print fpos

company_map = {'n' : 1, 'd': 3, 's': 5}

print "TESTING"
for k,v in fpos_info.items():
	cfg = fpos_config.get(k[1], None)
	print 'key', k,'valuye', v
	if len(v):
		fp_m.write(k[0], {'account_ids' : []}) # (6,0,[])]})

	print k, v, cfg
	fpos_id = k[0]
	inf = []
	if not cfg:
		continue

	for k in cfg:
		a1 = acc_m.search([('company_id','=',company_map[k[0][0]]),
				('code','=',k[0][1:])])
		a2 = acc_m.search([('company_id','=',company_map[k[1][0]]),
                                ('code','=',k[1][1:])])

		assert len(a1)==1, '%s acc %s %s' % (a1, k[0][0], k[0][1:])
		#if len(a2)==0:
		#	continue
		assert len(a2)==1, 'did not find %s' % k[1]
		print 'kont', a1, a2
		i = {'account_src_id' : a1[0],
			'account_dest_id' : a2[0]}
		inf.append((0,0,i))
	print "WRITING", inf	
	fp_m.write([fpos_id], {'account_ids' : inf})

		
