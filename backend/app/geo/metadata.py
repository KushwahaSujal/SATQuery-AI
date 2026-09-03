from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RasterMetadata(BaseModel):
    """Normalized structured metadata extracted from any supported raster or benchmark image."""
    filepath: str
    filename: str
    format: str
    width: int
    height: int
    bands: int
    dtype: str
    crs: Optional[str] = None
    bounds: Optional[List[float]] = None  # [minx, miny, maxx, maxy]
    transform: Optional[List[float]] = None  # 6 or 9 element affine matrix
    resolution: Optional[List[float]] = None  # [res_x, res_y]
    nodata: Optional[float] = None
    band_descriptions: List[str] = Field(default_factory=list)
    tags: Dict[str, Any] = Field(default_factory=dict)
    sensor: Optional[str] = None
    platform: Optional[str] = None
    acquisition_date: Optional[str] = None
    is_georeferenced: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
