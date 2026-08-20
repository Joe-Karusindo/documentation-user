# -*- coding: utf-8 -*-
{
    'name': 'Import Container Deposit Management',
    'summary': 'Manage import container deposits, refunds, deductions, and FTM landed cost posting',
    'description': '''
Import Container Deposit Management
===================================
Refactored replacement for custom_safety_deposit.

Core concept:
- Container deposit is treated as temporary receivable/asset, not import cost.
- Only final deducted/charged amount is posted to FTM landed cost.
- Refund and deduction settlement are separated from initial deposit payment.
''',
    'author': 'PT Karunia Jasindo / ChatGPT assisted',
    'website': 'https://karusindo.com',
    'category': 'Inventory/Inventory',
    'version': '16.0.1.0.59',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'account',
        'purchase',
        'stock',
        'stock_account',
        'stock_landed_costs',
        'custom_import',
        'ab_foreign_trade',
        'custom_reports',
        'ab_accounting',
        'sequence_reset_period',
        'ab_roman_sequence',
        'ar_core',
        'account_move_name_sequence'
    ],
    'data': [
        'security/container_deposit_security.xml',
        'security/ir.model.access.csv',
        'report/container_deposit_report.xml',
        'views/container_deposit_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'container_deposit_management/static/src/scss/cdm_bill_list.scss',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
