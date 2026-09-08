"""The coverages API.

Every statement in this module is scoped to the caller's own rows, and the
identity it scopes by comes from the verified token and from nowhere else.
That is the whole of the multi-tenancy defence: there is no code path in which
a value from the request body reaches owner_id.
"""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import get_db
from models import Coverage
from schemas import CoverageCreate, CoverageRead
from security import AuthenticatedUser, require_auth

router = APIRouter(prefix="/api/coverages", tags=["coverages"])


@router.post("", response_model=CoverageRead, status_code=status.HTTP_201_CREATED)
def create_coverage(
    payload: CoverageCreate,
    user: AuthenticatedUser = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Coverage:
    """Create a coverage owned by the caller.

    owner_id is taken from the token. The request body has no owner_id field
    to begin with, and the schema forbids unknown keys, so sending one is a
    422 rather than a silent no-op.
    """
    coverage = Coverage(
        owner_id=user.id,
        title=payload.title,
        description=payload.description,
        status=payload.status.value,
        ticker=payload.ticker,
        cik=payload.cik,
    )
    db.add(coverage)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Checking for the row first and inserting after would leave a window
        # between the two statements. The constraint is the only guarantee, so
        # the duplicate is detected by letting it fail.
        if "uq_coverages_owner_cik" in str(exc.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Conflict",
                    "message": "You already cover this filer",
                },
            ) from None
        raise

    db.refresh(coverage)
    return coverage


def _not_found() -> HTTPException:
    """One 404 for "no such row" and for "not yours".

    Answering 403 for someone else's id would confirm the row exists, which
    turns a loop over id values into a census of other tenants. The two cases
    are indistinguishable to the caller by design.
    """
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "Not Found", "message": "Coverage not found"},
    )


@router.get("", response_model=list[CoverageRead])
def list_coverages(
    user: AuthenticatedUser = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Sequence[Coverage]:
    """List the caller's coverages, newest first."""
    return db.scalars(
        select(Coverage)
        .where(Coverage.owner_id == user.id)
        .order_by(Coverage.created_at.desc(), Coverage.id.desc())
    ).all()


@router.get("/{coverage_id}", response_model=CoverageRead)
def get_coverage(
    coverage_id: int,
    user: AuthenticatedUser = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Coverage:
    """Read one coverage the caller owns.

    Ownership is a term in the WHERE clause, not a check on the row after it
    is fetched. A filter cannot be forgotten the way an `if` after the query
    can, and the row never leaves the database in the first place.
    """
    coverage = db.scalars(
        select(Coverage).where(
            Coverage.id == coverage_id,
            Coverage.owner_id == user.id,
        )
    ).one_or_none()

    if coverage is None:
        raise _not_found()
    return coverage
