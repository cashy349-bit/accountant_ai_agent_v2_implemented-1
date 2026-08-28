from agent.agent import AccountantAgent
from agent.schemas import InvoiceDraft

def test_mismatch_is_blocked():
    d=InvoiceDraft(invoice_number="A1",subtotal=100,tax=18,total=120,confidence=.99)
    r=AccountantAgent().decide(d)
    assert r["can_post"] is False

def test_invoice_schema_accepts_ocr_extraction():
    d = InvoiceDraft(
        vendor_name="OCR Test Store",
        invoice_number="IMG-TEST",
        subtotal=500,
        tax=90,
        total=590,
        confidence=0.99,
    )
    result = AccountantAgent().decide(d)
    assert result["errors"] == []
    assert result["can_post"] is True
