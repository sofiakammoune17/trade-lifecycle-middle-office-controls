# Trade Lifecycle & Middle-Office Controls

Python case study reproducing a simplified Front-to-Back control workflow for FX, bonds, equities, listed futures and OTC interest-rate swaps.

## Business objective

The project demonstrates how a Middle Office team can monitor trades from execution to settlement:

- validate mandatory trade economics;
- compare Front Office and counterparty confirmations;
- identify quantity, price, currency and settlement-date breaks;
- apply settlement-cycle and cut-off controls;
- prioritise exceptions by operational risk;
- calculate trade status and ageing;
- produce an exception dashboard and control report.

All transactions and counterparties are fictional. The workflow is deliberately simplified and does not represent a specific institution's operating model.

## Simplified lifecycle

1. **Execution:** the Front Office records the product, side, quantity/notional, price/rate and counterparty.
2. **Enrichment:** settlement date, currency, settlement method and standard settlement cycle are assigned.
3. **Confirmation and matching:** internal economics are compared with the counterparty confirmation.
4. **Pre-settlement control:** unmatched trades, missing fields and approaching cut-offs are escalated.
5. **Settlement:** cash and securities movements are monitored.
6. **Reconciliation:** internal status is compared with external settlement information and unresolved breaks are aged.

## Controls implemented

| Control | Purpose |
|---|---|
| Mandatory fields | Detect incomplete booking data |
| Economic matching | Compare product, side, amount, price, currency and dates |
| Price tolerance | Avoid false breaks caused by immaterial rounding |
| Standard settlement | Flag dates inconsistent with the simplified product convention |
| Cut-off monitoring | Escalate unresolved trades close to settlement |
| Ageing and priority | Rank operational breaks by urgency and value |

## Repository structure

```text
src/middle_office.py           Control and reporting engine
tests/test_middle_office.py    Operational-control tests
outputs/                       Generated exception and KPI reports
requirements.txt               Dependencies
```

## Run

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m src.middle_office
pytest -q
```

## Operational insights

The objective of matching is not to reprice a trade but to ensure that both parties agree on the economics before settlement. A high-value unmatched trade settling today is more urgent than a small future-dated rounding difference. Exception management therefore combines the nature of the break, settlement proximity, ageing and exposure.

## Skills demonstrated

Trade Lifecycle • Middle Office • Trading Support • Confirmation • Matching • Settlement • Reconciliation • Exception Management • Operational Risk • Python • Reporting

## Author

Sofia Kammoune — MBA Trading & Finance de Marché, ESLSCA Business School Paris.

