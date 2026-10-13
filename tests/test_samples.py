import json
from pathlib import Path

import pytest

from bill2quote import config
from bill2quote.checks import check_bill
from bill2quote.schema import BillFacts

CFG = config.load("config.example.toml")
TRUTHS = sorted(Path("samples").glob("*.truth.json"))

EXPECTED = {  # bill -> flag ids that must be present; everything else must be absent
    "05_estimated_read": {"C15"},
    "06_credit_dual_fuel": {"C13"},
    "07_inconsistent": {"C01"},
}


def test_there_are_eight_bills_worth_of_truth():
    assert len(TRUTHS) == 8


@pytest.mark.parametrize("path", TRUTHS, ids=lambda p: p.name)
def test_truth_validates_and_flags_match_design(path):
    facts = BillFacts.model_validate(json.loads(path.read_text(encoding="utf-8")))
    got = {f.id for f in check_bill(facts, CFG)}
    assert got == EXPECTED.get(path.name.split(".")[0], set())
