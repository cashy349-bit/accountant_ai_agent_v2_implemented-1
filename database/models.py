from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, DateTime, Numeric, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc)

class Company(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id"),
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    api_key_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(40), default="reviewer")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(500))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(40), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    invoice_number: Mapped[str | None] = mapped_column(String(100), index=True)
    invoice_date: Mapped[str | None] = mapped_column(String(20))
    subtotal: Mapped[float | None] = mapped_column(Numeric(18,2))
    tax: Mapped[float | None] = mapped_column(Numeric(18,2))
    total: Mapped[float | None] = mapped_column(Numeric(18,2))
    category: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Journal(Base):
    __tablename__ = "journals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="posted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class JournalLineModel(Base):
    __tablename__ = "journal_lines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    journal_id: Mapped[str] = mapped_column(ForeignKey("journals.id"), index=True)
    account: Mapped[str] = mapped_column(String(200), index=True)
    debit: Mapped[float] = mapped_column(Numeric(18,2), default=0)
    credit: Mapped[float] = mapped_column(Numeric(18,2), default=0)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(36))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
