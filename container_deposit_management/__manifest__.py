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
    'version': '16.0.1.0.32',
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
        'od_journal_sequence',
    ],
    'data': [
        'security/container_deposit_security.xml',
        'security/ir.model.access.csv',
        'report/container_deposit_report.xml',
        'views/container_deposit_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
