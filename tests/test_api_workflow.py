from io import BytesIO

from agent.mercury2 import Mercury2Client


def test_invoice_workflow(client, monkeypatch):
    def fake_extract_invoice(self, text, document_id):
        return {
            "vendor_name": "Integration Test Store",
            "invoice_number": "API-001",
            "invoice_date": None,
            "subtotal": 100,
            "tax": 18,
            "total": 118,
            "category": "Expense",
            "confidence": 0.99,
        }

    monkeypatch.setattr(
        Mercury2Client,
        "extract_invoice",
        fake_extract_invoice,
    )

    company_response = client.post(
        "/v1/companies",
        params={"name": "Integration Test Company"},
    )
    assert company_response.status_code == 200
    company_id = company_response.json()["id"]

    upload_response = client.post(
        "/v1/documents/upload",
        params={"company_id": company_id},
        files={
            "file": (
                "invoice.txt",
                BytesIO(
                    b"Invoice No: API-001\n"
                    b"Vendor: Integration Test Store\n"
                    b"Subtotal: 100\n"
                    b"Tax: 18\n"
                    b"Total: 118\n"
                ),
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200
    upload = upload_response.json()

    assert upload["duplicate"] is False
    assert upload["extraction"]["invoice_number"] == "API-001"
    assert upload["extraction"]["total"] == 118
    assert upload["draft"]["decision"]["errors"] == []
    assert upload["draft"]["decision"]["can_post"] is True

    invoice_id = upload["draft"]["invoice_id"]

    approve_response = client.post(
        f"/v1/invoices/{invoice_id}/approve",
        params={"company_id": company_id},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    post_response = client.post(
        f"/v1/invoices/{invoice_id}/post",
        params={"company_id": company_id},
    )
    assert post_response.status_code == 200
    assert post_response.json()["status"] == "posted"

    ledger_response = client.get(
        f"/v1/companies/{company_id}/ledger"
    )
    assert ledger_response.status_code == 200

    ledger = ledger_response.json()
    assert len(ledger) == 3

    total_debit = sum(row["debit"] for row in ledger)
    total_credit = sum(row["credit"] for row in ledger)

    assert total_debit == 118
    assert total_credit == 118

    trial_response = client.get(
        f"/v1/companies/{company_id}/trial-balance"
    )
    assert trial_response.status_code == 200

    trial_balance = trial_response.json()
    assert trial_balance["Expense"]["debit"] == 100
    assert trial_balance["GST Input"]["debit"] == 18
    assert trial_balance["Accounts Payable"]["credit"] == 118

def test_mercury_failure_is_handled(client, monkeypatch):
    def failing_extract_invoice(self, text, document_id):
        raise RuntimeError("Mercury-2 temporarily unavailable")

    monkeypatch.setattr(
        Mercury2Client,
        "extract_invoice",
        failing_extract_invoice,
    )

    company_response = client.post(
        "/v1/companies",
        params={"name": "Failure Test Company"},
    )
    assert company_response.status_code == 200
    company_id = company_response.json()["id"]

    upload_response = client.post(
        "/v1/documents/upload",
        params={"company_id": company_id},
        files={
            "file": (
                "failure-test.txt",
                BytesIO(b"Invoice No: FAIL-001\nTotal: 100\n"),
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 422

    result = upload_response.json()
    assert result["detail"]["error"]["code"] == "DOCUMENT_PROCESSING_FAILED"
    assert "Mercury-2 temporarily unavailable" in result["detail"]["error"]["message"]

def test_invalid_ai_extraction_is_blocked(client, monkeypatch):
    def bad_extract_invoice(self, text, document_id):
        return {
            "vendor_name": "Bad Invoice Store",
            "invoice_number": "BAD-001",
            "invoice_date": None,
            "subtotal": 500,
            "tax": 90,
            "total": 580,
            "category": "Expense",
            "confidence": 0.99,
        }

    monkeypatch.setattr(
        Mercury2Client,
        "extract_invoice",
        bad_extract_invoice,
    )

    company_response = client.post(
        "/v1/companies",
        params={"name": "Validation Test Company"},
    )
    assert company_response.status_code == 200
    company_id = company_response.json()["id"]

    upload_response = client.post(
        "/v1/documents/upload",
        params={"company_id": company_id},
        files={
            "file": (
                "bad-invoice.txt",
                BytesIO(
                    b"Invoice No: BAD-001\n"
                    b"Vendor: Bad Invoice Store\n"
                    b"Subtotal: 500\n"
                    b"Tax: 90\n"
                    b"Total: 580\n"
                ),
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    result = upload_response.json()
    decision = result["draft"]["decision"]

    assert "Arithmetic mismatch: expected 590.00, got 580.00" in decision["errors"]
    assert decision["can_post"] is False

def test_duplicate_invoice_requires_review(client, monkeypatch):
    def fake_extract_invoice(self, text, document_id):
        return {
            "vendor_name": "Duplicate Test Store",
            "invoice_number": "DUP-001",
            "invoice_date": None,
            "subtotal": 200,
            "tax": 36,
            "total": 236,
            "category": "Expense",
            "confidence": 0.99,
        }

    monkeypatch.setattr(
        Mercury2Client,
        "extract_invoice",
        fake_extract_invoice,
    )

    company_response = client.post(
        "/v1/companies",
        params={"name": "Duplicate Test Company"},
    )
    assert company_response.status_code == 200
    company_id = company_response.json()["id"]

    invoice_content = (
        b"Invoice No: DUP-001\n"
        b"Vendor: Duplicate Test Store\n"
        b"Subtotal: 200\n"
        b"Tax: 36\n"
        b"Total: 236\n"
    )

    first = client.post(
        "/v1/documents/upload",
        params={"company_id": company_id},
        files={"file": ("invoice1.txt", BytesIO(invoice_content), "text/plain")},
    )
    assert first.status_code == 200
    first_result = first.json()

    second = client.post(
        "/v1/documents/upload",
        params={"company_id": company_id},
        files={"file": ("invoice2.txt", BytesIO(invoice_content), "text/plain")},
    )
    assert second.status_code == 200
    second_result = second.json()

    assert second_result["duplicate"] is True
    assert second_result["draft"]["decision"]["status"] == "approval_required"
    assert "Possible duplicate invoice" in second_result["draft"]["decision"]["errors"]
    assert second_result["draft"]["decision"]["can_post"] is False

def test_empty_upload_rejected(client):
    company_response = client.post(
        "/v1/companies",
        params={"name": "Upload Security Test"},
    )
    company_id = company_response.json()["id"]

    response = client.post(
        "/v1/documents/upload",
        params={"company_id": company_id},
        files={
            "file": (
                "empty.txt",
                BytesIO(b""),
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Empty file"


def test_unsupported_file_type_rejected(client):
    company_response = client.post(
        "/v1/companies",
        params={"name": "Extension Test"},
    )
    company_id = company_response.json()["id"]

    response = client.post(
        "/v1/documents/upload",
        params={"company_id": company_id},
        files={
            "file": (
                "malware.exe",
                BytesIO(b"test"),
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"


def test_oversized_upload_rejected(client, monkeypatch):
    monkeypatch.setenv("MAX_DOCUMENT_MB", "0")

    company_response = client.post(
        "/v1/companies",
        params={"name": "Size Test"},
    )
    company_id = company_response.json()["id"]

    response = client.post(
        "/v1/documents/upload",
        params={"company_id": company_id},
        files={
            "file": (
                "large.txt",
                BytesIO(b"x"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "File too large"


def test_document_draft_cannot_cross_company(client, db, monkeypatch):
    def fake_extract_invoice(self, text, document_id):
        return {
            "vendor_name": "Tenant Test Store",
            "invoice_number": "TENANT-001",
            "invoice_date": None,
            "subtotal": 100,
            "tax": 18,
            "total": 118,
            "category": "Expense",
            "confidence": 0.99,
        }

    monkeypatch.setattr(
        Mercury2Client,
        "extract_invoice",
        fake_extract_invoice,
    )

    company_a = client.post(
        "/v1/companies",
        params={"name": "Company A"},
    ).json()["id"]

    company_b = client.post(
        "/v1/companies",
        params={"name": "Company B"},
    ).json()["id"]

    # Test principal must belong to Company A for the legitimate upload.
    from api.auth import hash_api_key
    from database.models import User

    user = db.query(User).filter(
        User.api_key_hash == hash_api_key("test-api-key")
    ).one()
    user.company_id = company_a
    db.commit()

    upload = client.post(
        "/v1/documents/upload",
        params={"company_id": company_a},
        files={
            "file": (
                "tenant.txt",
                BytesIO(b"Invoice No: TENANT-001\nTotal: 118\n"),
                "text/plain",
            )
        },
    )

    assert upload.status_code == 200
    document_id = upload.json()["document_id"]

    cross_company = client.post(
        "/v1/invoices/draft",
        params={
            "company_id": company_b,
            "document_id": document_id,
        },
        json={
            "vendor_name": "Tenant Test Store",
            "invoice_number": "TENANT-002",
            "invoice_date": None,
            "subtotal": 100,
            "tax": 18,
            "total": 118,
            "category": "Expense",
            "confidence": 0.99,
        },
    )

    assert cross_company.status_code == 403


def test_invoice_approval_requires_company_scope(client, db, monkeypatch):
    def fake_extract_invoice(self, text, document_id):
        return {
            "vendor_name": "Approval Tenant Store",
            "invoice_number": "TENANT-APPROVE-001",
            "invoice_date": None,
            "subtotal": 100,
            "tax": 18,
            "total": 118,
            "category": "Expense",
            "confidence": 0.99,
        }

    monkeypatch.setattr(
        Mercury2Client,
        "extract_invoice",
        fake_extract_invoice,
    )

    company_a = client.post(
        "/v1/companies",
        params={"name": "Approval Company A"},
    ).json()["id"]

    company_b = client.post(
        "/v1/companies",
        params={"name": "Approval Company B"},
    ).json()["id"]

    # Test principal must belong to Company A to create/approve its invoice.
    from api.auth import hash_api_key
    from database.models import User

    user = db.query(User).filter(
        User.api_key_hash == hash_api_key("test-api-key")
    ).one()
    user.company_id = company_a
    db.commit()

    upload = client.post(
        "/v1/documents/upload",
        params={"company_id": company_a},
        files={
            "file": (
                "approval.txt",
                BytesIO(b"Invoice No: TENANT-APPROVE-001\nTotal: 118\n"),
                "text/plain",
            )
        },
    )

    invoice_id = upload.json()["draft"]["invoice_id"]

    # This documents the security boundary we are about to enforce.
    response = client.post(
        f"/v1/invoices/{invoice_id}/approve",
        params={"company_id": company_b},
    )

    assert response.status_code == 403
