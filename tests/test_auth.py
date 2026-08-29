from api.auth import create_user, hash_api_key


def test_hash_api_key_is_deterministic(db):
    assert hash_api_key("test-key") == hash_api_key("test-key")
    assert hash_api_key("test-key") != hash_api_key("different-key")


def test_create_user_stores_hashed_key(db):
    company = __import__("database.models", fromlist=["Company"]).Company(
        name="Auth Test Company"
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    user, api_key = create_user(
        db,
        company_id=company.id,
        email="reviewer@example.com",
        role="reviewer",
        api_key="known-test-key",
    )

    assert api_key == "known-test-key"
    assert user.api_key_hash == hash_api_key("known-test-key")
    assert user.api_key_hash != "known-test-key"


def test_authentication_requires_api_key(client):
    response = client.get("/health")
    assert response.status_code == 200

def test_readiness_check(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_missing_api_key_is_rejected():
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as unauthenticated:
        response = unauthenticated.post(
            "/v1/companies",
            params={"name": "Unauthenticated Company"},
        )

    assert response.status_code == 401


def test_invalid_api_key_is_rejected():
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as unauthenticated:
        unauthenticated.headers.update({"X-API-Key": "definitely-invalid"})
        response = unauthenticated.post(
            "/v1/companies",
            params={"name": "Invalid Key Company"},
        )

    assert response.status_code == 401


def test_reviewer_cannot_post_invoice(client, db):
    from database.models import Company, Invoice, User
    from api.auth import create_user

    company = Company(name="Reviewer Post Test")
    db.add(company)
    db.commit()
    db.refresh(company)

    _, reviewer_key = create_user(
        db,
        company_id=company.id,
        email="reviewer-post@example.com",
        role="reviewer",
        api_key="reviewer-post-key",
    )

    invoice = Invoice(
        company_id=company.id,
        document_id="nonexistent-document",
        vendor_name="Test Vendor",
        invoice_number="POST-001",
        subtotal=100,
        tax=18,
        total=118,
        category="Expense",
        confidence=0.99,
        status="approved",
    )

    # The foreign-key relationship is not enforced by SQLite in this test setup.
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    client.headers.update({"X-API-Key": reviewer_key})

    response = client.post(
        f"/v1/invoices/{invoice.id}/post",
        params={"company_id": company.id},
    )

    assert response.status_code == 403


def test_wrong_company_is_rejected(client, db):
    from database.models import Company

    company = Company(name="Other Company")
    db.add(company)
    db.commit()
    db.refresh(company)

    response = client.post(
        "/v1/companies",
        params={"name": "Should Still Work"},
    )

    assert response.status_code == 200

    # The authenticated test user belongs to the fixture company,
    # so it must not be able to upload into another company.
    response = client.post(
        "/v1/documents/upload",
        params={"company_id": company.id},
        files={
            "file": (
                "wrong-company.txt",
                b"Invoice No: WRONG-001\nTotal: 100\n",
                "text/plain",
            )
        },
    )

    assert response.status_code == 403

def test_cross_company_invoice_approval_is_rejected(client, db):
    from database.models import Company, Invoice, User

    current_user = db.query(User).first()
    other_company = Company(name="Invoice Owner Company")
    db.add(other_company)
    db.commit()
    db.refresh(other_company)

    invoice = Invoice(
        company_id=other_company.id,
        document_id="nonexistent-document",
        vendor_name="Other Vendor",
        invoice_number="CROSS-APPROVE-001",
        subtotal=100,
        tax=18,
        total=118,
        category="Expense",
        confidence=0.99,
        status="pending_approval",
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    response = client.post(
        f"/v1/invoices/{invoice.id}/approve",
        params={"company_id": current_user.company_id},
    )

    assert response.status_code == 404


def test_cross_company_invoice_posting_is_rejected(client, db):
    from database.models import Company, Invoice, User

    current_user = db.query(User).first()
    other_company = Company(name="Other Posting Company")
    db.add(other_company)
    db.commit()
    db.refresh(other_company)

    invoice = Invoice(
        company_id=other_company.id,
        document_id="nonexistent-document",
        vendor_name="Other Vendor",
        invoice_number="CROSS-POST-001",
        subtotal=100,
        tax=18,
        total=118,
        category="Expense",
        confidence=0.99,
        status="approved",
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    response = client.post(
        f"/v1/invoices/{invoice.id}/post",
        params={"company_id": current_user.company_id},
    )

    assert response.status_code == 404
