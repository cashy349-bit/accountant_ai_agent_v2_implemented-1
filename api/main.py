from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from database.db import engine, db_session, Base
from database.models import Company, Document, Invoice, Journal, JournalLineModel, AuditLog
from api.auth import get_current_user
from api.policy import require_company_access, require_role
from database.models import User
from documents.pipeline import fingerprint, extract_text, extract_image_text
from agent.agent import AccountantAgent
from agent.mercury2 import Mercury2Client
from agent.schemas import InvoiceDraft
from accounting.engine import purchase_journal, validate_journal
from decimal import Decimal
import os, csv, io

app = FastAPI(title="Accountant AI Agent", version="2.0.0")
agent = AccountantAgent()
mercury = Mercury2Client()
storage = Path(os.getenv("STORAGE_DIR","storage")); storage.mkdir(exist_ok=True)

def get_db():
    yield from db_session()


def get_authenticated_user(
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    from api.auth import hash_api_key
    user = db.scalar(
        select(User).where(
            User.api_key_hash == hash_api_key(x_api_key)
        )
    )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not user.active:
        raise HTTPException(status_code=403, detail="User is inactive")

    return user

@app.get("/health")
def health():
    return {"status":"ok","service":"accountant-ai-agent"}

@app.post("/v1/companies")
def create_company(name: str, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)):
    c = Company(name=name); db.add(c); db.commit(); db.refresh(c)
    return {"id":c.id,"name":c.name}

@app.post("/v1/documents/upload")
async def upload(
    company_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    require_company_access(user, company_id)
    if not db.get(Company, company_id):
        raise HTTPException(404,"Company not found")
    original_filename = Path(file.filename or "upload").name
    suffix = Path(original_filename).suffix.lower()
    if suffix not in {".pdf",".png",".jpg",".jpeg",".txt"}:
        raise HTTPException(400,"Unsupported file type")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")

    max_mb = int(os.getenv("MAX_DOCUMENT_MB", "20"))
    max_bytes = max_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(413, "File too large")

    doc_id = uuid4().hex
    path = storage / f"{doc_id}{suffix}"
    path.write_bytes(data)
    fp = fingerprint(str(path))
    duplicate = db.scalar(select(Document).where(Document.company_id==company_id, Document.fingerprint==fp))
    doc = Document(id=doc_id, company_id=company_id, filename=original_filename, path=str(path), fingerprint=fp, status="duplicate" if duplicate else "uploaded")
    db.add(doc); db.add(AuditLog(company_id=company_id, action="upload", entity_id=doc_id, detail=f"fingerprint={fp}")); db.commit()
    text = ""
    extraction = None
    draft_result = None
    processing_error = None

    try:
        if suffix in {".pdf",".txt"}:
            text = extract_text(str(path))
        elif suffix in {".png",".jpg",".jpeg"}:
            text = extract_image_text(str(path))

        if not text.strip():
            processing_error = {
                "code": "NO_TEXT",
                "message": "No readable text could be extracted from the document."
            }
        else:
            extraction = mercury.extract_invoice(text, doc_id)
            invoice_draft = InvoiceDraft(**extraction)

            duplicate_invoice = db.scalar(select(Invoice).where(
                Invoice.company_id == company_id,
                Invoice.invoice_number == invoice_draft.invoice_number,
                Invoice.vendor_name == invoice_draft.vendor_name,
                Invoice.total == invoice_draft.total
            ))

            inv = Invoice(
                company_id=company_id,
                document_id=doc_id,
                vendor_name=invoice_draft.vendor_name,
                invoice_number=invoice_draft.invoice_number,
                invoice_date=invoice_draft.invoice_date,
                subtotal=invoice_draft.subtotal,
                tax=invoice_draft.tax,
                total=invoice_draft.total,
                category=invoice_draft.category,
                confidence=invoice_draft.confidence,
                status="duplicate_review" if duplicate_invoice else "pending_approval"
            )

            db.add(inv)
            db.flush()

            decision = agent.decide(invoice_draft, bool(duplicate_invoice))

            db.add(AuditLog(
                company_id=company_id,
                action="draft_created",
                entity_id=inv.id,
                detail=str(decision)
            ))

            db.commit()
            db.refresh(inv)

            draft_result = {
                "invoice_id": inv.id,
                "decision": decision
            }

    except Exception as e:
        db.rollback()
        processing_error = {
            "code": "DOCUMENT_PROCESSING_FAILED",
            "message": str(e)
        }

    if processing_error:
        raise HTTPException(
            status_code=422,
            detail={
                "document_id": doc_id,
                "error": processing_error,
            },
        )

    return {
        "document_id": doc_id,
        "duplicate": bool(duplicate),
        "text": text,
        "extraction": extraction,
        "draft": draft_result,
    }

@app.post("/v1/invoices/draft")
def create_draft(
    company_id: str,
    document_id: str,
    draft: InvoiceDraft,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    require_company_access(user, company_id)
    doc = db.get(Document, document_id)
    if not doc or doc.company_id != company_id: raise HTTPException(404,"Document not found")
    duplicate = db.scalar(select(Invoice).where(
        Invoice.company_id==company_id,
        Invoice.invoice_number==draft.invoice_number,
        Invoice.vendor_name==draft.vendor_name,
        Invoice.total==draft.total
    ))
    inv = Invoice(company_id=company_id, document_id=document_id, vendor_name=draft.vendor_name,
                  invoice_number=draft.invoice_number, invoice_date=draft.invoice_date,
                  subtotal=draft.subtotal, tax=draft.tax, total=draft.total,
                  category=draft.category, confidence=draft.confidence,
                  status="duplicate_review" if duplicate else "pending_approval")
    try:
        db.add(inv)
        db.flush()
        decision = agent.decide(draft, bool(duplicate))
        db.add(AuditLog(
            company_id=company_id,
            action="draft_created",
            entity_id=inv.id,
            detail=str(decision),
        ))
        db.commit()
        db.refresh(inv)
        return {"invoice_id": inv.id, "decision": decision}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, "Unable to create invoice draft")

@app.post("/v1/invoices/{invoice_id}/approve")
def approve(
    invoice_id: str,
    company_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    require_company_access(user, company_id)
    require_role(user, "admin", "reviewer")
    inv=db.get(Invoice,invoice_id)
    if not inv: raise HTTPException(404,"Invoice not found")
    if inv.status not in {"pending_approval"}: raise HTTPException(409,f"Invoice status is {inv.status}")
    try:
        inv.status = "approved"
        db.add(AuditLog(
            company_id=inv.company_id,
            action="approved",
            entity_id=invoice_id,
            detail="Human approval recorded",
        ))
        db.commit()
        return {"invoice_id": invoice_id, "status": "approved"}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, "Unable to approve invoice")

@app.post("/v1/invoices/{invoice_id}/post")
def post(
    invoice_id: str,
    company_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    require_company_access(user, company_id)
    require_role(user, "admin")
    inv=db.get(Invoice,invoice_id)
    if not inv: raise HTTPException(404,"Invoice not found")
    if inv.status!="approved": raise HTTPException(409,"Invoice must be approved before posting")
    if inv.subtotal is None or inv.tax is None or inv.total is None: raise HTTPException(400,"Incomplete amounts")
    gst_rate = (Decimal(str(inv.tax))/Decimal(str(inv.subtotal))*100) if inv.subtotal else Decimal("0")
    try:
        lines = purchase_journal(
            inv.subtotal,
            gst_rate,
            "Expense",
            "Accounts Payable",
        )

        j = Journal(
            company_id=inv.company_id,
            invoice_id=inv.id,
            status="posted",
        )
        db.add(j)
        db.flush()

        for line in lines:
            db.add(JournalLineModel(
                journal_id=j.id,
                account=line.account,
                debit=line.debit,
                credit=line.credit,
            ))

        inv.status = "posted"
        db.add(AuditLog(
            company_id=inv.company_id,
            action="posted",
            entity_id=invoice_id,
            detail=f"journal={j.id}",
        ))
        db.commit()

        return {
            "invoice_id": invoice_id,
            "journal_id": j.id,
            "status": "posted",
        }
    except (SQLAlchemyError, ValueError):
        db.rollback()
        raise HTTPException(500, "Unable to post invoice")

@app.get("/v1/companies/{company_id}/ledger")
def ledger(
    company_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    require_company_access(user, company_id)
    rows=db.execute(select(JournalLineModel,Journal).join(Journal,Journal.id==JournalLineModel.journal_id).where(Journal.company_id==company_id)).all()
    return [{"journal_id":j.id,"account":l.account,"debit":float(l.debit),"credit":float(l.credit)} for l,j in rows]

@app.get("/v1/companies/{company_id}/trial-balance")
def trial_balance(
    company_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    require_company_access(user, company_id)
    rows=db.execute(select(JournalLineModel,Journal).join(Journal,Journal.id==JournalLineModel.journal_id).where(Journal.company_id==company_id)).all()
    out={}
    for l,j in rows:
        out.setdefault(l.account,{"debit":0.0,"credit":0.0})
        out[l.account]["debit"] += float(l.debit); out[l.account]["credit"] += float(l.credit)
    return out

@app.get("/v1/companies/{company_id}/export/ledger.csv")
def export_ledger(
    company_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    require_company_access(user, company_id)
    rows=ledger(company_id,db)
    s=io.StringIO(); w=csv.DictWriter(s,fieldnames=["journal_id","account","debit","credit"]); w.writeheader(); w.writerows(rows)
    return {"csv":s.getvalue()}
