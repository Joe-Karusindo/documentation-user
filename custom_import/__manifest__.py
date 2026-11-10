# -*- coding: utf-8 -*-
{
    'name': "custom_import",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account', 'purchase', 'viin_foreign_trade','sale_purchase', 'stock','stock_account','stock_landed_costs','ab_stock_picking', 'ab_foreign_trade', 'custom_reports'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'reports/report_perincian_import.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/wizard_views.xml',
        'views/account_move_views.xml',
        'views/stock_landed_cost_views.xml',
        'views/custom_declaration_import_views.xml',
    ],

}
