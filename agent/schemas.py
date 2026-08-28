from pydantic import BaseModel, Field

class InvoiceDraft(BaseModel):
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    category: str | None = None
    confidence: float = Field(ge=0, le=1, default=0)
