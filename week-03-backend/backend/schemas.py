"""Request and response bodies for the coverages API.

owner_id appears in neither direction. It is not accepted on the way in, so a
client cannot choose it, and it is not returned, because every row a caller can
read is already their own.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models import CoverageStatus


class CoverageCreate(BaseModel):
    # Unknown fields are rejected rather than dropped. A client that sends
    # owner_id is told its request was wrong instead of believing it worked.
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: CoverageStatus = CoverageStatus.DRAFT
    ticker: str | None = Field(default=None, max_length=10)
    # Exactly ten digits, zero-padded: 320193 and 0000320193 are the same
    # filer, and only the padded form matches the EDGAR path.
    cik: str = Field(pattern=r"^\d{10}$")


class CoverageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: CoverageStatus
    ticker: str | None
    cik: str
    created_at: datetime
    updated_at: datetime
