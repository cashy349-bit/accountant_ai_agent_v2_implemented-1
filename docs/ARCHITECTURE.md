# Architecture

AI is a planner/extractor only. The accounting engine is deterministic.

Upload -> fingerprint -> extraction/OCR -> AI draft -> validation -> duplicate detection -> approval -> accounting engine -> balanced journal -> ledger/reporting -> audit.

The API currently exposes company creation, upload, draft creation, approval, posting, ledger, trial balance and CSV export.
