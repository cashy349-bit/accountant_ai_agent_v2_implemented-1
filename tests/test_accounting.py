from decimal import Decimal
import pytest
from accounting.engine import validate_journal, JournalLine, calculate_gst

def test_balanced():
    validate_journal([JournalLine("Expense",debit=Decimal("100")),JournalLine("AP",credit=Decimal("100"))])

def test_unbalanced_rejected():
    with pytest.raises(ValueError):
        validate_journal([JournalLine("Expense",debit=Decimal("100")),JournalLine("AP",credit=Decimal("99"))])

def test_gst():
    assert calculate_gst("1000","18")== (Decimal("1000.00"),Decimal("180.00"),Decimal("1180.00"))
