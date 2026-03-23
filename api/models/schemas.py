"""
Pydantic Schemas
Request and response validation models
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ImageResponse(BaseModel):
    """Image response schema"""
    id: int
    file_name: str
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    brightness: Optional[float] = None
    contrast: Optional[float] = None
    saturation: Optional[float] = None
    edge_density: Optional[float] = None

    features_json: Optional[dict] = None
    similarity: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class SearchResponse(BaseModel):
    """Search response schema including query image features"""
    query_image: dict
    results: list[ImageResponse]
