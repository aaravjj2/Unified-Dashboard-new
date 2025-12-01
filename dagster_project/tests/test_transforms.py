import pandas as pd
from dagster_project.assets.transforms import clean_picks_df_impl, clean_financial_df_impl


def test_clean_picks_basic():
    raw = pd.DataFrame(
        {
            "ticker": [" aapl ", None, "TSLA"],
            "date": ["2021-01-01", "invalid", "2021-01-03"],
            "price": [100, "N/A", 700],
            "qty": [10, 5, None],
        }
    )

    cleaned = clean_picks_df_impl(raw)
    # Should drop row with invalid date or missing ticker
    assert "AAPL" in cleaned["ticker"].values
    assert "TSLA" in cleaned["ticker"].values
    assert cleaned["price"].dtype.kind in "fi"  # float or int
    assert cleaned["qty"].isnull().sum() == 0


def test_clean_financial_basic():
    raw = pd.DataFrame(
        {
            "symbol": ["AAPL", "AAPL", "TSLA"],
            "timestamp": ["2021-01-01T00:00:00", "2021-01-01T00:00:00", "2021-01-02T00:00:00"],
            "value": [1.2, 1.2, None],
        }
    )

    cleaned = clean_financial_df_impl(raw)
    # duplicates should be removed
    assert cleaned.shape[0] == 2
    assert cleaned["value"].isnull().sum() == 0
