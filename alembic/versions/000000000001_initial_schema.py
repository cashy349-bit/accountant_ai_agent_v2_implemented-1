"""initial schema

Revision ID: 000000000001
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "000000000001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index("ix_documents_company_id", "documents", ["company_id"])
    op.create_index("ix_documents_fingerprint", "documents", ["fingerprint"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("vendor_name", sa.String(length=255)),
        sa.Column("invoice_number", sa.String(length=100)),
        sa.Column("invoice_date", sa.String(length=20)),
        sa.Column("subtotal", sa.Numeric(18, 2)),
        sa.Column("tax", sa.Numeric(18, 2)),
        sa.Column("total", sa.Numeric(18, 2)),
        sa.Column("category", sa.String(length=100)),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
    )
    op.create_index("ix_invoices_company_id", "invoices", ["company_id"])
    op.create_index("ix_invoices_document_id", "invoices", ["document_id"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"])

    op.create_table(
        "journals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
    )
    op.create_index("ix_journals_company_id", "journals", ["company_id"])
    op.create_index("ix_journals_invoice_id", "journals", ["invoice_id"])

    op.create_table(
        "journal_lines",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("journal_id", sa.String(length=36), nullable=False),
        sa.Column("account", sa.String(length=200), nullable=False),
        sa.Column("debit", sa.Numeric(18, 2), nullable=False),
        sa.Column("credit", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["journal_id"], ["journals.id"]),
    )
    op.create_index("ix_journal_lines_journal_id", "journal_lines", ["journal_id"])
    op.create_index("ix_journal_lines_account", "journal_lines", ["account"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_logs_company_id", "audit_logs", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_company_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_journal_lines_account", table_name="journal_lines")
    op.drop_index("ix_journal_lines_journal_id", table_name="journal_lines")
    op.drop_table("journal_lines")

    op.drop_index("ix_journals_invoice_id", table_name="journals")
    op.drop_index("ix_journals_company_id", table_name="journals")
    op.drop_table("journals")

    op.drop_index("ix_invoices_invoice_number", table_name="invoices")
    op.drop_index("ix_invoices_document_id", table_name="invoices")
    op.drop_index("ix_invoices_company_id", table_name="invoices")
    op.drop_table("invoices")

    op.drop_index("ix_documents_fingerprint", table_name="documents")
    op.drop_index("ix_documents_company_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_company_id", table_name="users")
    op.drop_table("users")

    op.drop_table("companies")
