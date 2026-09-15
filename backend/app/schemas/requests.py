from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language user query")
    image_filenames: List[str] = Field(..., min_length=1, max_length=2, description="Uploaded filenames in job workspace")
    request_id: Optional[str] = None
    override_task: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    aoi_geojson: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Area of interest as GeoJSON (Polygon / MultiPolygon / Feature / FeatureCollection). "
                    "RFC 7946 WGS84 lon/lat unless a legacy 'crs' member says otherwise. Requires a georeferenced raster."
    )
    aoi_filename: Optional[str] = Field(default=None, description="A .geojson AOI previously sent to POST /upload/aoi.")
