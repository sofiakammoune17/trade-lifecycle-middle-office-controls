from datetime import date

import pandas as pd

from src.middle_office import (
    build_kpis,
    enrich_operational_controls,
    match_trades,
    sample_trade_data,
    validate_mandatory_fields,
)


def test_missing_settlement_date_is_detected():
    internal, _ = sample_trade_data()
    validated = validate_mandatory_fields(internal).set_index("trade_id")
    assert not bool(validated.loc["TRD006", "mandatory_fields_ok"])
    assert "settlement_date" in validated.loc["TRD006", "missing_fields"]


def test_clean_trade_is_matched():
    internal, confirmations = sample_trade_data()
    matched = match_trades(internal, confirmations).set_index("trade_id")
    assert matched.loc["TRD001", "match_status"] == "MATCHED"


def test_price_break_is_detected():
    internal, confirmations = sample_trade_data()
    matched = match_trades(internal, confirmations).set_index("trade_id")
    assert "PRICE" in matched.loc["TRD002", "break_reason"]


def test_quantity_break_is_detected():
    internal, confirmations = sample_trade_data()
    matched = match_trades(internal, confirmations).set_index("trade_id")
    assert "QUANTITY" in matched.loc["TRD003", "break_reason"]


def test_missing_confirmation_is_detected():
    internal, confirmations = sample_trade_data()
    matched = match_trades(internal, confirmations).set_index("trade_id")
    assert "MISSING_CONFIRMATION" in matched.loc["TRD006", "break_reason"]


def test_unresolved_trade_at_settlement_is_high_priority():
    internal, confirmations = sample_trade_data()
    matched = match_trades(internal, confirmations)
    controls = enrich_operational_controls(matched, date(2026, 9, 4)).set_index("trade_id")
    assert controls.loc["TRD003", "priority"] == "HIGH"


def test_kpis_reconcile_to_total_trades():
    internal, confirmations = sample_trade_data()
    controls = enrich_operational_controls(match_trades(internal, confirmations))
    kpis = build_kpis(controls).set_index("kpi")["value"]
    assert kpis["Matched trades"] + kpis["Exceptions"] == kpis["Total trades"]

