"""
Shared Pydantic response schemas for AlphaMind API.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str
    status_code: int


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


class SuccessResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None
