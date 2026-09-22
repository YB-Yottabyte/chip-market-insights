from src.clean_financials import normalize_company
from datetime import date, timedelta


def _fact(start, end, fy, fp, value, form="10-Q"):
    return {
        "start": start,
        "end": end,
        "fy": fy,
        "fp": fp,
        "val": value,
        "form": form,
        "filed": (date.fromisoformat(end) + timedelta(days=60)).isoformat(),
        "accn": "1",
    }


def test_q4_derived_only_from_complete_quarters():
    values = [
        _fact("2024-01-01", "2024-03-31", 2024, "Q1", 10),
        _fact("2024-04-01", "2024-06-30", 2024, "Q2", 20),
        _fact("2024-07-01", "2024-09-30", 2024, "Q3", 30),
        _fact("2024-01-01", "2024-12-31", 2024, "FY", 100, "10-K"),
    ]
    payload = {
        "cik": 1097864,
        "facts": {"us-gaap": {"Revenues": {"units": {"USD": values}}}},
    }
    frame = normalize_company("ON", payload)
    assert frame.loc[frame.fiscal_quarter.eq(4), "revenue"].iloc[0] == 40
    assert frame.loc[frame.fiscal_quarter.eq(4), "gross_profit"].isna().all()
    values.pop(1)
    assert 4 not in normalize_company("ON", payload).fiscal_quarter.tolist()


def test_cik_mapping_rejected():
    try:
        normalize_company("ON", {"cik": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("Wrong CIK accepted")


def test_old_comparative_in_new_filing_is_excluded():
    old = _fact("2023-01-01", "2023-03-31", 2024, "Q1", 99)
    old["filed"] = "2024-05-01"
    payload = {
        "cik": 1097864,
        "facts": {"us-gaap": {"Revenues": {"units": {"USD": [old]}}}},
    }
    assert normalize_company("ON", payload).empty


def test_current_filing_uses_latest_period_end_for_quarter():
    earlier_note = _fact("2024-01-01", "2024-03-31", 2024, "Q2", 10)
    current = _fact("2024-04-01", "2024-06-30", 2024, "Q2", 20)
    earlier_note["filed"] = current["filed"]
    payload = {
        "cik": 1097864,
        "facts": {"us-gaap": {"Revenues": {"units": {"USD": [earlier_note, current]}}}},
    }
    frame = normalize_company("ON", payload)
    assert frame.period_end.tolist() == ["2024-06-30"]


def test_onsemi_rd_alternative_us_gaap_tag():
    revenue = _fact("2024-01-01", "2024-03-31", 2024, "Q1", 100)
    research = _fact("2024-01-01", "2024-03-31", 2024, "Q1", 12)
    payload = {
        "cik": 1097864,
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [revenue]}},
                "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost": {
                    "units": {"USD": [research]}
                },
            }
        },
    }
    assert normalize_company("ON", payload).iloc[0].rd_expense == 12
