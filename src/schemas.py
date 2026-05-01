from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Union

class TocEntry(BaseModel):
    enabled: bool = True
    level: int
    title: str
    printed_page: Optional[Union[str, int]] = None
    page_number_type: Literal["arabic", "roman", "unknown"]
    pdf_start_page: Optional[int] = None
    pdf_end_page: Optional[int] = None
    output_name: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

class TocExtractionResult(BaseModel):
    toc_pages: List[int]
    entries: List[TocEntry]
    notes: List[str] = Field(default_factory=list)
    raw_response_text: Optional[str] = None
    model_name: Optional[str] = None

class SplitPlanItem(BaseModel):
    enabled: bool
    title: str
    start_page: int
    end_page: int
    output_name: str
    warnings: List[str] = Field(default_factory=list)

class ModelTocEntry(BaseModel):
    level: int
    title: str
    printed_page: Optional[Union[str, int]] = None
    page_number_type: Literal["arabic", "roman", "unknown"]

class ModelTocResponse(BaseModel):
    entries: List[ModelTocEntry]
