
from typing import Generic, TypeVar, List, Dict, Any, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")

class MetaData(BaseModel):
    total: Optional[int] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class StandardResponse(BaseModel, Generic[T]):
    status: str = Field(default="success", description="Response status (success/error)")
    data: T
    meta: Optional[MetaData] = None
