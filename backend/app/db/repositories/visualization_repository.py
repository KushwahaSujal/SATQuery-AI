"""
SatQuery AI — Visualization Layer Repository
Async CRUD operations for persisted visualization layers.
"""
from typing import List, Optional
import uuid
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.visualization import VisualizationLayerRecord
from backend.app.visualization.provenance import LayerMetadata


class VisualizationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_layer(
        self,
        job_id: str,
        layer_meta: LayerMetadata,
        artifact_path: str,
        legend_path: Optional[str] = None
    ) -> VisualizationLayerRecord:
        record = VisualizationLayerRecord(
            id=str(uuid.uuid4()),
            job_id=job_id,
            layer_id=layer_meta.layer_id,
            layer_type=layer_meta.layer_type.value,
            title=layer_meta.title,
            provenance=layer_meta.provenance.value,
            source_model=layer_meta.source_model,
            artifact_path=artifact_path,
            legend_path=legend_path,
            metadata_json=layer_meta.model_dump(),
            created_at=datetime.utcnow()
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_layers_by_job(self, job_id: str) -> List[VisualizationLayerRecord]:
        stmt = select(VisualizationLayerRecord).where(
            VisualizationLayerRecord.job_id == job_id
        ).order_by(VisualizationLayerRecord.created_at.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_layer_by_id(self, job_id: str, layer_id: str) -> Optional[VisualizationLayerRecord]:
        stmt = select(VisualizationLayerRecord).where(
            VisualizationLayerRecord.job_id == job_id,
            VisualizationLayerRecord.layer_id == layer_id
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def delete_layers_by_job(self, job_id: str) -> None:
        stmt = delete(VisualizationLayerRecord).where(VisualizationLayerRecord.job_id == job_id)
        await self.session.execute(stmt)
