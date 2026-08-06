# -*- coding: utf-8 -*-
from datetime import datetime

import pytz

from odoo import fields, models, _
from odoo.exceptions import UserError

# Roman numerals for calendar months (1..12). Used when journal sequence
# prefixes contain %(rom_month)s / %(Rmonth)s but the active interpolator
# (e.g. od_journal_sequence) does not provide those keys.
_ROMAN_MONTHS = (
    '', 'I', 'II', 'III', 'IV', 'V', 'VI',
    'VII', 'VIII', 'IX', 'X', 'XI', 'XII',
)


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    def _cdm_repair_sequence_placeholders(self, journal=None):
        """Normalize known incompatible placeholders before next_by_id().

        - ``#CODE`` → journal code (od_journal_sequence bank/cash templates)
        - ``%(rom_month)s`` → ``%(Rmonth)s`` (alias used successfully by CDM /
          other Karusindo sequences such as CD/%(year)s/%(Rmonth)s/)
        """
        for sequence in self:
            vals = {}
            prefix = sequence.prefix or ''
            new_prefix = prefix
            if journal and '#CODE' in new_prefix:
                new_prefix = new_prefix.replace('#CODE', (journal.code or '').upper())
            if '%(rom_month)' in new_prefix:
                new_prefix = new_prefix.replace('%(rom_month)', '%(Rmonth)')
            if new_prefix != prefix:
                vals['prefix'] = new_prefix

            suffix = sequence.suffix or ''
            new_suffix = suffix
            if '%(rom_month)' in new_suffix:
                new_suffix = new_suffix.replace('%(rom_month)', '%(Rmonth)')
            if new_suffix != suffix:
                vals['suffix'] = new_suffix

            if vals:
                sequence.sudo().write(vals)
        return self

    def _cdm_interpolation_dict(self, date=None, date_range=None):
        """Standard date placeholders plus roman-month aliases."""
        self.ensure_one()
        now = range_date = effective_date = datetime.now(
            pytz.timezone(self._context.get('tz') or 'UTC')
        )
        if date or self._context.get('ir_sequence_date'):
            effective_date = fields.Datetime.from_string(
                date or self._context.get('ir_sequence_date')
            )
        if date_range or self._context.get('ir_sequence_date_range'):
            range_date = fields.Datetime.from_string(
                date_range or self._context.get('ir_sequence_date_range')
            )

        formats = {
            'year': '%Y', 'month': '%m', 'day': '%d', 'y': '%y', 'doy': '%j',
            'woy': '%W', 'weekday': '%w', 'h24': '%H', 'h12': '%I',
            'min': '%M', 'sec': '%S',
        }
        res = {}
        for key, fmt in formats.items():
            res[key] = effective_date.strftime(fmt)
            res['range_' + key] = range_date.strftime(fmt)
            res['current_' + key] = now.strftime(fmt)

        for label, dt in (
            ('', effective_date),
            ('range_', range_date),
            ('current_', now),
        ):
            roman = _ROMAN_MONTHS[dt.month]
            res[label + 'rom_month'] = roman
            res[label + 'Rmonth'] = roman
        return res

    def _get_prefix_suffix(self, date=None, date_range=None):
        """Ensure %(rom_month)s / %(Rmonth)s never raise KeyError on post.

        Register Payment from CDM posts draft vendor bills. That path goes
        through od_journal_sequence which interpolates the journal sequence
        prefix. Some prefixes use %(rom_month)s while the interpolator dict
        only exposes other keys, causing KeyError: 'rom_month'.
        """
        self.ensure_one()
        self._cdm_repair_sequence_placeholders()
        try:
            return super()._get_prefix_suffix(date=date, date_range=date_range)
        except KeyError as err:
            missing = err.args[0] if err.args else ''
            if missing not in (
                'rom_month', 'Rmonth',
                'range_rom_month', 'range_Rmonth',
                'current_rom_month', 'current_Rmonth',
            ):
                raise
            d = self._cdm_interpolation_dict(date=date, date_range=date_range)

            def _interpolate(value, values):
                return (value % values) if value else ''

            try:
                return _interpolate(self.prefix, d), _interpolate(self.suffix, d)
            except KeyError as err2:
                raise UserError(_(
                    'Invalid prefix or suffix for sequence "%(name)s" '
                    '(missing placeholder "%(key)s").'
                ) % {
                    'name': self.display_name,
                    'key': err2.args[0] if err2.args else err2,
                })
