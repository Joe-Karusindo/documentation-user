# -*- coding: utf-8 -*-
{
    'name': 'Crypto Investment',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Crypto jual-beli, accounting, laporan L/R, dashboard & proyeksi harga',
    'description': """
Crypto Investment Management for Odoo 16 Community
==================================================

Modul custom untuk usaha/investasi jual-beli cryptocurrency:

* Master data aset crypto (symbol, nama, harga pasar)
* Beginning balance (saldo awal kas & holding crypto)
* Transaksi beli/jual dengan harga, fee, dan histori per crypto
* Integrasi jurnal accounting (asset crypto, kas, gain/loss)
* Laporan untung/rugi per rentang tanggal
* Dashboard portfolio crypto
* Treeview posisi & histori transaksi
* Analisa & proyeksi harga naik/turun 14 hari ke depan (regresi linear)
    """,
    'author': 'Crypto Investment',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'account',
        'board',
    ],
    'data': [
        'security/crypto_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/crypto_asset_data.xml',
        'views/crypto_asset_views.xml',
        'views/crypto_beginning_balance_views.xml',
        'views/crypto_transaction_views.xml',
        'views/crypto_price_history_views.xml',
        'views/crypto_projection_views.xml',
        'views/crypto_dashboard_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
        'wizard/crypto_pnl_wizard_views.xml',
        'report/crypto_pnl_report_templates.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crypto_investment/static/src/scss/crypto_dashboard.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
