from fastapi import HTTPException

from database.models import User


def require_company_access(user: User, company_id: str) -> None:
    if user.company_id != company_id:
        raise HTTPException(
            status_code=403,
            detail="User does not have access to this company",
        )


def require_role(user: User, *allowed_roles: str) -> None:
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="User role is not authorized for this operation",
        )
