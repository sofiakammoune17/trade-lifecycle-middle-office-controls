"""Simplified trade-lifecycle, matching and exception-monitoring engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


MANDATORY_FIELDS = [
    "trade_id",
    "trade_date",
    "product",
    "side",
    "quantity",
    "price",
    "currency",
    "counterparty",
    "settlement_date",
]

STANDARD_SETTLEMENT_DAYS = {
    "EQUITY": 2,
    "BOND": 2,
    "FX_SPOT": 2,
    "FUTURE": 1,
    "IRS": 2,
}


@dataclass(frozen=True)
class Tolerances:
    quantity: float = 0.01
    price: float = 0.0001
    notional_high_eur: float = 1_000_000.0


def sample_trade_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create deterministic fictional internal and counterparty trade records."""
    internal = pd.DataFrame(
        [
            ["TRD001", "2026-09-01", "FX_SPOT", "BUY", 1_000_000, 1.1650, "USD", "Bank A", "2026-09-03", "MATCHED"],
            ["TRD002", "2026-09-01", "BOND", "BUY", 2_000_000, 98.4500, "EUR", "Bank B", "2026-09-03", "PENDING"],
            ["TRD003", "2026-09-02", "EQUITY", "SELL", 25_000, 42.1800, "EUR", "Broker C", "2026-09-04", "PENDING"],
            ["TRD004", "2026-09-02", "IRS", "PAY", 5_000_000, 0.0275, "EUR", "Bank D", "2026-09-04", "PENDING"],
            ["TRD005", "2026-09-03", "FUTURE", "SELL", 46, 132.1000, "EUR", "Broker E", "2026-09-04", "PENDING"],
            ["TRD006", "2026-09-03", "BOND", "SELL", 750_000, 101.2500, "EUR", "Bank F", None, "PENDING"],
        ],
        columns=MANDATORY_FIELDS + ["internal_status"],
    )
    confirmation = pd.DataFrame(
        [
            ["TRD001", "FX_SPOT", "BUY", 1_000_000, 1.1650, "USD", "2026-09-03"],
            ["TRD002", "BOND", "BUY", 2_000_000, 98.4750, "EUR", "2026-09-03"],
            ["TRD003", "EQUITY", "SELL", 24_500, 42.1800, "EUR", "2026-09-04"],
            ["TRD004", "IRS", "PAY", 5_000_000, 0.0275, "EUR", "2026-09-05"],
            ["TRD005", "FUTURE", "SELL", 46, 132.1000, "USD", "2026-09-04"],
        ],
        columns=["trade_id", "cp_product", "cp_side", "cp_quantity", "cp_price", "cp_currency", "cp_settlement_date"],
    )
    return internal, confirmation


def validate_mandatory_fields(trades: pd.DataFrame) -> pd.DataFrame:
    result = trades.copy()
    missing_columns = set(MANDATORY_FIELDS).difference(result.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")
    result["missing_fields"] = result[MANDATORY_FIELDS].apply(
        lambda row: ", ".join(field for field, value in row.items() if pd.isna(value) or value == ""),
        axis=1,
    )
    result["mandatory_fields_ok"] = result["missing_fields"].eq("")
    return result


def match_trades(
    internal: pd.DataFrame,
    confirmations: pd.DataFrame,
    tolerances: Tolerances = Tolerances(),
) -> pd.DataFrame:
    result = validate_mandatory_fields(internal).merge(
        confirmations, on="trade_id", how="left", indicator=True
    )
    result["confirmation_received"] = result["_merge"].eq("both")

    exact_pairs = [
        ("product", "cp_product", "PRODUCT"),
        ("side", "cp_side", "SIDE"),
        ("currency", "cp_currency", "CURRENCY"),
        ("settlement_date", "cp_settlement_date", "SETTLEMENT_DATE"),
    ]

    def breaks(row: pd.Series) -> str:
        items: list[str] = []
        if not row["mandatory_fields_ok"]:
            items.append("MISSING_FIELD")
        if not row["confirmation_received"]:
            items.append("MISSING_CONFIRMATION")
            return ", ".join(items)
        for internal_field, cp_field, label in exact_pairs:
            left = "" if pd.isna(row[internal_field]) else str(row[internal_field])
            right = "" if pd.isna(row[cp_field]) else str(row[cp_field])
            if left != right:
                items.append(label)
        if abs(float(row["quantity"]) - float(row["cp_quantity"])) > tolerances.quantity:
            items.append("QUANTITY")
        if abs(float(row["price"]) - float(row["cp_price"])) > tolerances.price:
            items.append("PRICE")
        return ", ".join(items)

    result["break_reason"] = result.apply(breaks, axis=1)
    result["match_status"] = np.where(result["break_reason"].eq(""), "MATCHED", "EXCEPTION")
    return result.drop(columns="_merge")


def enrich_operational_controls(
    matched: pd.DataFrame,
    as_of: date = date(2026, 9, 4),
    tolerances: Tolerances = Tolerances(),
) -> pd.DataFrame:
    result = matched.copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"])
    result["settlement_date"] = pd.to_datetime(result["settlement_date"])
    as_of_ts = pd.Timestamp(as_of)
    result["days_to_settlement"] = (result["settlement_date"] - as_of_ts).dt.days
    result["age_business_days"] = result["trade_date"].apply(
        lambda value: int(np.busday_count(value.date(), as_of))
    )
    result["gross_amount"] = result["quantity"].abs() * result["price"].abs()
    result["cutoff_alert"] = (
        result["match_status"].eq("EXCEPTION")
        & result["days_to_settlement"].le(0).fillna(True)
    )
    result["priority"] = "LOW"
    result.loc[result["match_status"].eq("EXCEPTION"), "priority"] = "MEDIUM"
    result.loc[
        result["cutoff_alert"] | (result["gross_amount"] >= tolerances.notional_high_eur),
        "priority",
    ] = "HIGH"
    result.loc[result["match_status"].eq("MATCHED"), "priority"] = "NONE"
    return result


def build_kpis(controls: pd.DataFrame) -> pd.DataFrame:
    total = len(controls)
    exceptions = int(controls["match_status"].eq("EXCEPTION").sum())
    return pd.DataFrame(
        [
            {"kpi": "Total trades", "value": total},
            {"kpi": "Matched trades", "value": total - exceptions},
            {"kpi": "Exceptions", "value": exceptions},
            {"kpi": "Match rate", "value": (total - exceptions) / total if total else np.nan},
            {"kpi": "High-priority breaks", "value": int(controls["priority"].eq("HIGH").sum())},
            {"kpi": "Cut-off alerts", "value": int(controls["cutoff_alert"].sum())},
        ]
    )


def save_outputs(output_dir: Path = Path("outputs")) -> None:
    internal, confirmations = sample_trade_data()
    matched = match_trades(internal, confirmations)
    controls = enrich_operational_controls(matched)
    kpis = build_kpis(controls)

    output_dir.mkdir(parents=True, exist_ok=True)
    controls.to_csv(output_dir / "trade_control_report.csv", index=False)
    controls.loc[controls["match_status"].eq("EXCEPTION")].to_csv(
        output_dir / "exception_queue.csv", index=False
    )
    kpis.to_csv(output_dir / "operational_kpis.csv", index=False)

    exceptions = controls.loc[controls["match_status"].eq("EXCEPTION"), "break_reason"]
    counts = exceptions.str.get_dummies(sep=", ").sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    counts.plot.bar(ax=ax, color="#315b7d")
    ax.set_title("Middle-Office exceptions by break type")
    ax.set_xlabel("Break type")
    ax.set_ylabel("Number of trades")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "exceptions_by_type.png", dpi=180)
    plt.close(fig)

    print(kpis.to_string(index=False))
    print("\nException queue")
    print(
        controls.loc[
            controls["match_status"].eq("EXCEPTION"),
            ["trade_id", "product", "break_reason", "days_to_settlement", "priority"],
        ].to_string(index=False)
    )


if __name__ == "__main__":
    save_outputs()

