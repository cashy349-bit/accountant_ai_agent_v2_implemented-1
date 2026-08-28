# Accountant AI Agent v2 — Implemented MVP

Run locally:
1. `python -m venv .venv`
2. Activate it.
3. `pip install -r requirements.txt`
4. `uvicorn api.main:app --reload`

Run tests:
`pytest -q`

Docker:
`docker compose up --build`

Implemented in this version:
- FastAPI API
- SQLite by default for easy local startup; PostgreSQL via DATABASE_URL
- SQLAlchemy persistence
- Document upload and SHA-256 fingerprinting
- PDF text extraction
- Structured invoice draft workflow
- Deterministic arithmetic/GST validation
- Duplicate detection
- Approval and posting endpoints
- Double-entry journal persistence
- Ledger and trial-balance endpoints
- P&L calculation
- CSV export
- Background automation worker contract
- Role/policy foundation
- Mercury-2 HTTP integration and structured extraction
- PNG/JPG/JPEG OCR with Tesseract and preprocessing

Current limitations:
- Jurisdiction-specific GST compliance/filing.
- Production-grade identity provider/MFA.
- Payment/Tally integrations.
- Production deployment/security hardening.
- Jurisdiction-specific GST compliance/filing.
- Production-grade identity provider/MFA.
- Payment/Tally integrations.

Do not use this for real books until the production gates in docs/PRODUCTION_GATES.md are completed.
