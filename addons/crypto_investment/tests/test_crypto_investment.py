# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCryptoInvestment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Asset = cls.env['crypto.asset']
        cls.Transaction = cls.env['crypto.transaction']
        cls.Beginning = cls.env['crypto.beginning.balance']
        cls.Projection = cls.env['crypto.price.projection']
        cls.History = cls.env['crypto.price.history']

        cls.btc = cls.Asset.create({
            'name': 'Bitcoin Test',
            'symbol': 'BTCTEST',
            'current_price': 50000.0,
        })
        cls.eth = cls.Asset.create({
            'name': 'Ethereum Test',
            'symbol': 'ETHTEST',
            'current_price': 3000.0,
        })

    def test_beginning_balance_and_holdings(self):
        beginning = self.Beginning.create({
            'cash_balance': 10000.0,
            'line_ids': [
                (0, 0, {
                    'asset_id': self.btc.id,
                    'quantity': 1.0,
                    'unit_cost': 40000.0,
                }),
            ],
        })
        # Post without requiring accounting accounts
        beginning._create_opening_transactions()
        beginning.state = 'posted'
        self.assertAlmostEqual(self.btc.quantity, 1.0)
        self.assertAlmostEqual(self.btc.average_cost, 40000.0)
        self.assertAlmostEqual(self.btc.cost_basis, 40000.0)

    def test_buy_sell_average_cost_pnl(self):
        # Seed holding via beginning tx
        self.Transaction.create({
            'asset_id': self.btc.id,
            'transaction_type': 'beginning',
            'quantity': 1.0,
            'unit_price': 40000.0,
            'unit_cost': 40000.0,
            'state': 'done',
        })
        buy = self.Transaction.create({
            'asset_id': self.btc.id,
            'transaction_type': 'buy',
            'quantity': 1.0,
            'unit_price': 60000.0,
            'fee': 0.0,
        })
        buy.action_confirm()
        self.btc.invalidate_recordset()
        self.assertAlmostEqual(self.btc.quantity, 2.0)
        self.assertAlmostEqual(self.btc.average_cost, 50000.0)

        sell = self.Transaction.create({
            'asset_id': self.btc.id,
            'transaction_type': 'sell',
            'quantity': 1.0,
            'unit_price': 55000.0,
            'fee': 0.0,
        })
        sell.action_confirm()
        self.assertAlmostEqual(sell.unit_cost, 50000.0)
        self.assertAlmostEqual(sell.realized_pnl, 5000.0)
        self.btc.invalidate_recordset()
        self.assertAlmostEqual(self.btc.quantity, 1.0)

    def test_projection_linear_regression(self):
        from datetime import date, timedelta
        today = date.today()
        for i, price in enumerate([100.0, 110.0, 120.0, 130.0, 140.0]):
            self.History.create({
                'asset_id': self.eth.id,
                'date': today - timedelta(days=20 - i * 4),
                'price': price,
                'source': 'manual',
            })
        self.eth.current_price = 140.0
        projection = self.Projection.create({
            'asset_ids': [(6, 0, [self.eth.id])],
            'horizon_days': 14,
            'lookback_days': 30,
        })
        projection.action_compute()
        self.assertEqual(projection.state, 'done')
        self.assertEqual(len(projection.line_ids), 1)
        line = projection.line_ids[0]
        self.assertEqual(line.trend, 'up')
        self.assertGreater(line.projected_price, line.current_price)

    def test_pnl_wizard(self):
        self.Transaction.create({
            'asset_id': self.btc.id,
            'transaction_type': 'beginning',
            'quantity': 2.0,
            'unit_price': 40000.0,
            'unit_cost': 40000.0,
            'state': 'done',
        })
        sell = self.Transaction.create({
            'asset_id': self.btc.id,
            'transaction_type': 'sell',
            'quantity': 1.0,
            'unit_price': 45000.0,
        })
        sell.action_confirm()
        wizard = self.env['crypto.pnl.wizard'].create({})
        wizard.action_compute()
        self.assertTrue(wizard.line_ids)
        self.assertGreater(wizard.total_realized_pnl, 0.0)
