# Production gates

This code is an implemented MVP, not a claim of accounting compliance.

Before production:
- Verify Mercury 2 API endpoint/auth/schema and implement the adapter.
- Add a real OCR service for scans.
- Add authentication, MFA, RBAC and tenant authorization middleware.
- Use PostgreSQL in production with migrations.
- Use private encrypted object storage for documents.
- Add durable Redis queue and idempotency.
- Implement country/jurisdiction-specific GST/tax rules with accountant review.
- Add immutable audit/event storage.
- Add bank/CSV/Excel reconciliation.
- Add P&L and balance sheet reports from the ledger.
- Add Tally adapter after exact customer setup is known.
- Add rate limiting, security headers, CSRF protections where applicable, secret management.
- Add backups, restore tests, monitoring and alerting.
- Add end-to-end, concurrency and disaster-recovery tests.
- Have qualified accounting/legal professionals validate the final product before commercial financial use.
