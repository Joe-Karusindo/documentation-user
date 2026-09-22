# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    crypto_cash_account_id = fields.Many2one(
        'account.account',
        string='Crypto Cash/Bank Account',
        domain="[('account_type', 'in', ('asset_cash', 'asset_current')), ('company_id', '=', id)]",
    )
    crypto_asset_account_id = fields.Many2one(
        'account.account',
        string='Default Crypto Asset Account',
        domain="[('account_type', 'in', ('asset_current', 'asset_non_current')), ('company_id', '=', id)]",
    )
    crypto_opening_equity_account_id = fields.Many2one(
        'account.account',
        string='Opening Equity Account',
        domain="[('account_type', '=', 'equity'), ('company_id', '=', id)]",
    )
    crypto_gain_account_id = fields.Many2one(
        'account.account',
        string='Crypto Gain Account',
        domain="[('account_type', 'in', ('income', 'income_other')), ('company_id', '=', id)]",
    )
    crypto_loss_account_id = fields.Many2one(
        'account.account',
        string='Crypto Loss Account',
        domain="[('account_type', 'in', ('expense', 'expense_direct_cost')), ('company_id', '=', id)]",
    )
    crypto_fee_account_id = fields.Many2one(
        'account.account',
        string='Trading Fee Account',
        domain="[('account_type', 'in', ('expense', 'expense_direct_cost')), ('company_id', '=', id)]",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    crypto_cash_account_id = fields.Many2one(
        related='company_id.crypto_cash_account_id',
        readonly=False,
    )
    crypto_asset_account_id = fields.Many2one(
        related='company_id.crypto_asset_account_id',
        readonly=False,
    )
    crypto_opening_equity_account_id = fields.Many2one(
        related='company_id.crypto_opening_equity_account_id',
        readonly=False,
    )
    crypto_gain_account_id = fields.Many2one(
        related='company_id.crypto_gain_account_id',
        readonly=False,
    )
    crypto_loss_account_id = fields.Many2one(
        related='company_id.crypto_loss_account_id',
        readonly=False,
    )
    crypto_fee_account_id = fields.Many2one(
        related='company_id.crypto_fee_account_id',
        readonly=False,
    )
