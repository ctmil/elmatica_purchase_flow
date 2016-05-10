# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Bringsvor Consulting AS
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Elmatica - Purchase flow',
    'version': '1.0',
    'author': 'Elmatica AS',
    'website': 'http://www.bringsvor.com',
    'category': 'Localization/Adaptations',
    'description': """
""",
    # 'depends': ['purchase','sale', 'sale_stock', 'stock_account', 'elmatica_invoice', 'elmatica_super_sales_order'],
    'depends': ['purchase','sale', 'sale_stock', 'stock_account', 'elmatica_invoice'],
    'data': [
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',
        'views/res_partner_view.xml',
        # 'views/super_sales_order.xml',
        'views/stock_picking_view.xml',
        'views/purchase_order_line_view.xml',
        'views/delivery_mismatch.xml',
        'data/shipping_days.xml',
        'wizards/warning.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'test': [
        ],
    'installable': True,
    'auto_install': False,
}

