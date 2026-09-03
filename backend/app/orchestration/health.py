"""
SatQuery AI — Model & Workflow Health Monitor
Tracks operational reliability: latency, execution durations, failure counts,
and common failure stages. Strictly labeled as operational telemetry.
"""
from typing import Any, Dict, List, Optional
from collections import defaultdict
from backend.app.logging import logger


class OperationalHealthMonitor:
    """
    In-memory operational metrics tracker for models, tools, and workflows.
    """
    def __init__(self):
        self._workflow_runs: Dict[str, int] = defaultdict(int)
        self._workflow_failures: Dict[str, int] = defaultdict(int)
        self._workflow_durations_ms: Dict[str, List[float]] = defaultdict(list)
        self._model_latencies_ms: Dict[str, List[float]] = defaultdict(list)
        self._model_failures: Dict[str, int] = defaultdict(int)

    def record_workflow_execution(self, workflow_id: str, duration_ms: float, success: bool = True) -> None:
        self._workflow_runs[workflow_id] += 1
        if not success:
            self._workflow_failures[workflow_id] += 1
        self._workflow_durations_ms[workflow_id].append(duration_ms)
        # Keep last 100 runs per workflow
        if len(self._workflow_durations_ms[workflow_id]) > 100:
            self._workflow_durations_ms[workflow_id].pop(0)

    def record_model_run(self, model_name: str, latency_ms: float, success: bool = True) -> None:
        if not success:
            self._model_failures[model_name] += 1
        self._model_latencies_ms[model_name].append(latency_ms)
        if len(self._model_latencies_ms[model_name]) > 100:
            self._model_latencies_ms[model_name].pop(0)

    def get_health_summary(self) -> Dict[str, Any]:
        """Returns aggregate operational telemetry."""
        workflows = {}
        for w_id, runs in self._workflow_runs.items():
            fails = self._workflow_failures[w_id]
            durs = self._workflow_durations_ms[w_id]
            avg_ms = sum(durs) / len(durs) if durs else 0.0
            workflows[w_id] = {
                "total_runs": runs,
                "failures": fails,
                "success_rate_percent": round((1.0 - fails / runs) * 100.0, 1) if runs > 0 else 100.0,
                "average_duration_ms": round(avg_ms, 1)
            }

        models = {}
        for m_name, lats in self._model_latencies_ms.items():
            fails = self._model_failures[m_name]
            avg_lat = sum(lats) / len(lats) if lats else 0.0
            models[m_name] = {
                "total_inferences": len(lats) + fails,
                "failures": fails,
                "average_latency_ms": round(avg_lat, 1)
            }

        return {
            "workflows": workflows,
            "models": models,
            "metric_type": "OPERATIONAL_TELEMETRY"
        }


operational_health = OperationalHealthMonitor()
