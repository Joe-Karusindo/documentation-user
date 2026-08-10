# Import Container Deposit Management

Replacement/refactor for `custom_safety_deposit`.

## Main business correction

Container deposit is not landed cost. It is a temporary receivable / asset until final settlement.
Only the deducted / charged amount after container return is posted to FTM landed cost.

## Recommended process

1. Draft
2. Waiting Confirmation
3. Confirmed
4. Deposit Paid
5. Waiting Settlement
6. Settlement Received
7. Waiting Approval
8. Approved
9. Posted
10. Done
11. Cancelled

## Key models

- `import.container.deposit`
- `import.container.deposit.line`
- `import.container.deposit.settlement.line`
- `import.container.deposit.operation`

## Important fields

- FTM Reference: `custom.declaration.import`
- Purchase Orders and Transfers are auto-filled from FTM when available
- Deposit Account: asset/receivable account for refundable deposit
- Settlement lines split refund amount and final deducted charge
- Final deducted charge can create a draft FTM landed cost

## Installation notes

This module depends on the same custom import/FTM stack used by the original module:

- `custom_import`
- `stock_landed_costs`
- accounting, purchase, stock

Install on a test database first. Do not install directly on production before UAT.


Version 16.0.1.0.4
-------------------
- Prevents duplicate account.move names when posting module-generated vendor bills.
- Draft bills explicitly use name `/`.
- On posting, only bills linked to a Container Deposit Settlement receive a deterministic unique number (`CD-BILL-########` or `CD-CN-########`).
- Ordinary vendor bill numbering remains unchanged.


Version 16.0.1.0.5
------------------
- FTM Currency and FTM Currency Rate are hidden from the Container Deposit Settlement form.
- New container deposit documents always keep the company currency (IDR in PTKJ) and are no longer overwritten by the selected FTM currency.
- Deposit Vendor Bills and refund Vendor Credit Notes are explicitly created in company currency.
- Operational amount fields are displayed as plain numbers without a currency symbol.
- No migration is included: historical documents and the workflow from version 16.0.1.0.4 remain unchanged.


## 16.0.1.0.6
- Fix duplicate account.move numbering when Register Payment posts a payment for a container-deposit vendor bill.
- Payment journal entries receive a scoped unique `CD-PAY-########` number.
- No historical records or workflow stages are changed.


Version 16.0.1.0.7
------------------
- Product/account mapping on Deposit / Initial Charges:
  - Uang Muka Jaminan Container (also accepts legacy spelling Kontainer) -> account 1700002.
  - Uang Muka Jaminan Sewa Container -> account 1700003.
- The Account column is filled automatically on onchange and enforced again on create/write.
- Account lookup is company-specific and active-account only.
- Existing historical lines are not migrated or rewritten during module upgrade.


Version 16.0.1.0.8
-------------------
- Selecting an FTM Reference automatically sets account 1200002 Piutang Pihak Ketiga.
- Selecting an FTM Reference automatically sets the general journal named Landed Cost Journal.
- Existing historical records are not migrated; defaults apply when a new FTM is selected or a new record is created with an FTM.


## 16.0.1.0.9
- Robust company-aware lookup for accounts 1700002 and 1700003.
- Uses sudo/allowed-company context to avoid accounting record-rule visibility issues.
- Handles harmless whitespace and legacy account-name fallback.
- Does not migrate or modify historical records.


Version 16.0.1.0.10
---------------------
- Robust account mapping for 1700002/1700003 using exact database lookup in the document company.
- Handles product internal references and Container/Kontainer spelling.
- Fixes account lookup hidden by custom multi-company/account record rules on unsaved one2many lines.


## Version 16.0.1.0.11
- Fixed PostgreSQL `btrim(jsonb)` error on translated `account.account.name`.
- Account lookup now normalizes account codes and uses ORM for translated-name fallback.
- Mapping remains 1700002 for container deposit and 1700003 for container rental deposit.


## 16.0.1.0.12
- Fix account 1700002 lookup when the account is visible in the COA but linked to a legacy/shared company record.
- Keep exact company lookup first; add safe global fallback by normalized account code and translated name.
- No workflow or historical data migration changes.


## 16.0.1.0.13
- Fixed automatic account assignment for product "Uang Muka Jaminan Kontainer".
- Replaced fragile SQL/strict-company lookup with ORM plus Python-side account-code normalisation.
- Keeps mapping 1700002/1700003 and does not migrate historical records or change workflow.


Version 16.0.1.0.14
-------------------
- Fixed deterministic account mapping for product Uang Muka Jaminan Container/Kontainer to account 1700002.
- Uses product/category accounting properties first, then a code-only SQL lookup that is safe with JSONB translated account names.
- Keeps mapping of Uang Muka Jaminan Sewa Container/Kontainer to 1700003.
- No historical data or workflow changes.


Version 16.0.1.0.15
-------------------
- Root cause: account 1700002 (Uang Muka Jaminan Container) was deprecated in COA while 1700003 stayed active, so Account auto-filled only for the Sewa product.
- Lookup now prefers non-deprecated accounts but still accepts the mapped code when it was accidentally deprecated.
- Install/upgrade hook reactivates accounts 1700002 and 1700003 when they are deprecated.
- Accepts short product aliases such as "Uang Muka Sewa Container".
- No historical deposit lines or workflow stages are migrated.


Version 16.0.1.0.16
-------------------
- Settlement Final Deduction auto-fills as Original Deposit Amount - Refund Amount when Refund Amount changes.
- Start Settlement no longer copies Uang Muka Jaminan deposit products into Landed Cost Product; pick a real landed-cost charge product instead.
- Clearer Create FTM Landed Cost error when the selected product is not Landed Cost enabled.


Version 16.0.1.0.17
-------------------
- Renamed menu/action labels from Container Deposit Settlement to Container Deposit Management.
- Removed Container Deposit Asset Account from the form header.
- Deposit / Initial Charges: removed Line Type column; Product limited to Uang Muka Jaminan Container and Uang Muka Jaminan Sewa Container; Vendor filtered by Is Vendor status; Account renamed to Deposit Account and limited to 1700002 / 1700003.


Version 16.0.1.0.18
-------------------
- Fixed Product / Charge dropdown showing only one option by resolving approved products via ORM + JSONB fallback instead of [('name', 'in', ...)] domain.
- Deposit Account dropdown now lists both 1700002 and 1700003 reliably and auto-fills from the selected product.


Version 16.0.1.0.19
-------------------
- Added an editable Taxes column next to Refund Amount on settlement lines.
- New settlement lines inherit purchase taxes from their source deposit lines; users can add or remove taxes before approval.
- Create Refund Credit Note now copies each settlement line's taxes to the corresponding credit-note line.
- Refund Amount remains the tax-excluded settlement amount; tax is calculated separately by Odoo on the Vendor Credit Note.


Version 16.0.1.0.20
-------------------
- Hide the custom Invoice Prepare tab on landed costs created from Container Deposit Management.
- Other landed-cost workflows keep the Invoice Prepare tab unchanged.
- Added an explicit dependency on ab_foreign_trade, which provides the Invoice Prepare tab.


Version 16.0.1.0.21
-------------------
- Link newly created FTM Landed Costs to their Custom Declaration Import (No FTM).
- Purchase Orders, Custom Doc. Number and Vendor are consequently derived from the linked FTM.
- Link the first related deposit Vendor Bill as the primary Vendor Bill and retain all related bills in Bill Cost when that custom field is available.
- Replace Partner with the Vendor (`vendor_id`) of the primary related Vendor Bill on the Landed Cost form.
- Backfill these FTM and Vendor Bill links on existing Landed Costs created from Container Deposit Management during module upgrade.


Version 16.0.1.0.30
-------------------
- Support the Karusindo chart of accounts where deposit accounts are coded 1720002 / 1720003 (under 1720 Uang Muka Pembelian) instead of the legacy 1700002 / 1700003.
- Deposit Account auto-fill, dropdown domain, and validation now accept both account layouts; the product's configured Expense Account is preferred when it matches an approved code.
- Install/upgrade hook reactivates any of the four mapped deposit accounts when deprecated.


Version 16.0.1.0.31
-------------------
- Removed legacy accounts 1700002 / 1700003 from the module entirely; the COA no longer uses them.
- Deposit Account mapping, dropdown domain, validation, and install/upgrade hook now use only 1720002 (Uang Muka Jaminan Container) and 1720003 (Uang Muka Jaminan Sewa Container).


Version 16.0.1.0.32
-------------------
- (Superseded by 16.0.1.0.53) Earlier builds allowed Set to Draft on Cancelled; Cancelled is now final.


Version 16.0.1.0.33
-------------------
- The bill list opened from the CDM document (Vendor Bills / Refunds smart buttons) now uses a restricted tree view: New, Upload, and Create Landed Costs are removed, and Register Payment is highlighted as the primary action.


Version 16.0.1.0.34
-------------------
- Register Payment in the CDM bills list is now visually highlighted (Odoo 16 ignores the class attribute on list header buttons, so this is done via a scoped stylesheet).
- Added a Cancel header button in the CDM bills list: cancels the selected bills/credit notes (blocked when payments exist) and unlinks them from the deposit/settlement lines, restoring the document to the state before Create Deposit Bill was clicked.


Version 16.0.1.0.35
-------------------
- Fixed the Register Payment highlight not showing: Odoo 16 ships Bootstrap 5.1, which has no --bs-btn-* button variables (introduced in 5.2), so the stylesheet now sets background/border/text colors directly.


Version 16.0.1.0.36
-------------------
- Register Payment highlight now uses the theme's own btn-primary styling (via Bootstrap's button-variant($primary) mixin at SCSS compile time) instead of a hardcoded color, so it matches other highlighted buttons such as Mark Deposit Paid.


Version 16.0.1.0.37
-------------------
- Register Payment in the CDM bills list now posts selected draft bills automatically before opening the payment wizard, fixing the "You can only register payment for posted journal entries" error (the restricted list has no separate Post action).


Version 16.0.1.0.38
-------------------
- Register Payment in the CDM bills list now blocks selections that mix bills of different vendors (clear popup listing the vendors), preventing the "Another entry with the same name already exists" error on Create Payment. Payment must be registered per vendor.


Version 16.0.1.0.39
-------------------
- Fixed "Another entry with the same name already exists" when creating a payment for a single CDM bill: payment journal-entry numbering (od_journal_sequence vs the standard sequence mixin) could produce a name that already exists in the journal. CDM payments now pre-assign a verified unique entry name (P<CODE>/<year>/<roman>/#####) before posting.


Version 16.0.1.0.40
-------------------
- CDM payment journal entries now follow the same numbering convention as Vendor Bills: drawn from the journal's own entry sequence (PREFIX/YYYY/Roman/#### with the sequence's padding), continuing the journal's last number, with a uniqueness guard that skips already-used numbers.
- Repairs the literal '#CODE' placeholder left by od_journal_sequence in bank/cash journal sequence prefixes (replaced with the journal code) when a CDM payment is numbered.


Version 16.0.1.0.51
-------------------
- Fixed Register Payment KeyError: 'rom_month' when posting draft CDM vendor bills.
- Journal sequences that still use %(rom_month)s are normalized to %(Rmonth)s before post, with a roman-month interpolation fallback on ir.sequence so od_journal_sequence can finish numbering (e.g. BILL/2026/VIII/####).


Version 16.0.1.0.52
-------------------
- Block Set to Draft (full reopen to Draft) and Cancel while any deposit Vendor Bill is Paid / In Payment / Partial (e.g. status Deposit Paid with posted+paid bills).
- The block is lifted after those deposit vendor bills are Reversed and the refund is paid (`payment_state` becomes `reversed`), or the payment is undone so the bill is no longer paid.
- Settlement unlock via Set to Draft from Waiting Settlement onward remains allowed while the deposit stays paid (returns to Waiting Settlement, does not reopen the deposit).
- Clear UserError lists the blocking bills; reversed deposit bills are unlinked on full reopen so Create Deposit Bill can run again.


Version 16.0.1.0.53
-------------------
- Cancelled documents are final: Set to Draft is hidden on Cancelled status and blocked server-side (cannot reopen a cancelled Container Deposit).
