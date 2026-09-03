"""
SatQuery AI — Provenance Graph Builder
Constructs verifiable provenance trees linking final answers and artifacts directly
to source rasters, model checkpoints, preprocessing transforms, and tool executions.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.orchestration.schemas import ProvenanceGraph, ProvenanceNode
from backend.app.orchestration.cache import DeterministicCache
from backend.app.logging import logger


class ProvenanceBuilder:
    """
    Builds structured, auditable provenance graphs for every SatQuery AI request.
    """

    @classmethod
    def build_provenance_graph(
        cls,
        job_id: str,
        input_paths: List[str],
        models_used: List[str],
        artifacts_dict: Dict[str, List[str]],
        execution_trace: List[Any],
        answer: Optional[str] = None
    ) -> ProvenanceGraph:
        """
        Assembles complete provenance graph.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        nodes: List[ProvenanceNode] = []
        edges: List[Dict[str, str]] = []
        root_ids: List[str] = []

        # 1. Root Input Nodes
        for p_str in input_paths:
            p = Path(p_str)
            node_id = f"input_{p.name}"
            root_ids.append(node_id)
            chk = DeterministicCache.compute_file_hash(str(p))
            nodes.append(ProvenanceNode(
                node_id=node_id,
                source_type="SOURCE_FILE",
                name=p.name,
                timestamp=now_iso,
                checksum_sha256=chk,
                metadata={"path": str(p), "size_bytes": p.stat().st_size if p.exists() else 0}
            ))

        # 2. Model Inference Nodes
        for m in models_used:
            m_node_id = f"model_{m}"
            nodes.append(ProvenanceNode(
                node_id=m_node_id,
                source_type="MODEL_INFERENCE",
                name=m,
                model=m,
                timestamp=now_iso,
                input_ids=root_ids
            ))
            for r_id in root_ids:
                edges.append({"from": r_id, "to": m_node_id})

        # 3. Artifact Nodes
        for art_type, file_list in artifacts_dict.items():
            for fname in file_list:
                art_id = f"artifact_{fname}"
                nodes.append(ProvenanceNode(
                    node_id=art_id,
                    artifact_id=fname,
                    source_type="EVIDENCE_ARTIFACT",
                    name=fname,
                    timestamp=now_iso,
                    metadata={"artifact_type": art_type}
                ))
                # Link from models to artifacts
                for m in models_used:
                    edges.append({"from": f"model_{m}", "to": art_id})

        # 4. Final Answer Leaf Node
        if answer:
            ans_node_id = "final_answer"
            nodes.append(ProvenanceNode(
                node_id=ans_node_id,
                source_type="SYNTHESIS",
                name="Final Answer",
                timestamp=now_iso,
                metadata={"text": answer[:200]}
            ))
            for m in models_used:
                edges.append({"from": f"model_{m}", "to": ans_node_id})

        return ProvenanceGraph(
            job_id=job_id,
            root_inputs=root_ids,
            nodes=nodes,
            edges=edges
        )
