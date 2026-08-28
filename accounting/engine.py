from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass

MONEY = Decimal("0.01")

def money(value):
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)

@dataclass(frozen=True)
class JournalLine:
    account: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")

def validate_journal(lines):
    lines = list(lines)
    if not lines:
        raise ValueError("Journal is empty")
    debit = sum((money(x.debit) for x in lines), Decimal("0"))
    credit = sum((money(x.credit) for x in lines), Decimal("0"))
    if debit != credit:
        raise ValueError(f"Unbalanced journal: debit={debit}, credit={credit}")
    for x in lines:
        if x.debit < 0 or x.credit < 0:
            raise ValueError("Negative debit/credit is invalid")
        if x.debit and x.credit:
            raise ValueError("A line cannot contain both debit and credit")
    return True

def calculate_gst(net, rate_percent):
    net = money(net)
    tax = money(net * Decimal(str(rate_percent)) / Decimal("100"))
    return net, tax, money(net + tax)

def purchase_journal(net, gst_rate, expense_account="Expense", payable_account="Accounts Payable"):
    net, tax, total = calculate_gst(net, gst_rate)
    lines = [
        JournalLine(expense_account, debit=net),
        JournalLine("GST Input", debit=tax),
        JournalLine(payable_account, credit=total),
    ]
    validate_journal(lines)
    return lines

def sales_journal(net, gst_rate, revenue_account="Sales Revenue", receivable_account="Accounts Receivable"):
    net, tax, total = calculate_gst(net, gst_rate)
    lines = [
        JournalLine(receivable_account, debit=total),
        JournalLine(revenue_account, credit=net),
        JournalLine("GST Output", credit=tax),
    ]
    validate_journal(lines)
    return lines
