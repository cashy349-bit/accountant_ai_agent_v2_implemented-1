from decimal import Decimal
from accounting.engine import money
from .schemas import InvoiceDraft

class AccountantAgent:
    def validate(self, draft: InvoiceDraft):
        errors = []
        if draft.subtotal is None or draft.total is None:
            errors.append("Missing subtotal or total")
        if draft.subtotal is not None and draft.tax is not None and draft.total is not None:
            expected = money(draft.subtotal) + money(draft.tax)
            if expected != money(draft.total):
                errors.append(f"Arithmetic mismatch: expected {expected}, got {money(draft.total)}")
        if not draft.invoice_number:
            errors.append("Missing invoice number")
        if draft.confidence < 0.80:
            errors.append("Low extraction confidence")
        return errors

    def duplicate_key(self, draft):
        return (draft.vendor_name or "").strip().lower(), (draft.invoice_number or "").strip().lower(), money(draft.total or 0)

    def decide(self, draft, duplicate=False):
        errors = self.validate(draft)
        if duplicate:
            errors.append("Possible duplicate invoice")
        return {
            "status": "approval_required",
            "errors": errors,
            "can_post": not errors
        }
