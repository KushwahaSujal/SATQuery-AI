"""
SatQuery AI — Visualization Layer SQLAlchemy Database Model
Stores metadata, provenance, and artifact paths for generated visual analytics layers.
Does NOT store large raster binaries in PostgreSQL.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class VisualizationLayerRecord(Base):
    __tablename__ = "visualization_layers"

    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    layer_id = Column(String(64), nullable=False, index=True)
    layer_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    provenance = Column(String(32), nullable=False)
    source_model = Column(String(64), nullable=True)
    artifact_path = Column(String(512), nullable=False)
    legend_path = Column(String(512), nullable=True)
    metadata_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    job = relationship("AnalysisJob", backref="visualization_layers")
