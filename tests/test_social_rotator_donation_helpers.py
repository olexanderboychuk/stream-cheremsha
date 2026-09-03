from __future__ import annotations

from stream_cheremsha.ui.donations_qml_api import (
    donation_row_amount_name_donatello,
    donation_row_amount_name_donatik,
)


def test_donation_row_helpers() -> None:
    name, amt = donation_row_amount_name_donatik(
        {"name": "A", "payment": {"amount": "250.5", "currency": "UAH"}}
    )
    assert name == "A"
    assert amt == 250.5
    name2, amt2 = donation_row_amount_name_donatello(
        {"clientName": "B", "amount": 100, "currency": "UAH"}
    )
    assert name2 == "B"
    assert amt2 == 100.0
