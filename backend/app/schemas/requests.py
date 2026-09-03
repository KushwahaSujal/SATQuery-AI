from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language user query")
    image_filenames: List[str] = Field(..., min_length=1, max_length=2, description="Uploaded filenames in job workspace")
    request_id: Optional[str] = None
    override_task: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
