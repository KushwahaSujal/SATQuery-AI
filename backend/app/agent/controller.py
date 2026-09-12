from typing import List, Optional
from datetime import datetime
import time
from backend.app.agent.state import AgentState
from backend.app.agent.validator import PlanValidator
from backend.app.agent.executor import SafeToolExecutor
from backend.app.geo.modality import ModalityDetector
from backend.app.geo.raster import RasterInspector
from backend.app.evidence.confidence import ConfidenceEvaluator
from backend.app.evidence.consistency import ConsistencyChecker
from backend.app.schemas.agent import JobStatus, TaskType
from backend.app.schemas.responses import AnalyzeResponse
from backend.app.artifacts.manager import artifact_manager
from backend.app.exceptions import SatQueryException
from backend.app.logging import logger
from backend.app.db.session import get_session_maker
from backend.app.db.repositories.job_repository import JobRepository

# Advanced Orchestration Layer Imports
from backend.app.orchestration.planner import AdvancedWorkflowPlanner, OrchestratedPlan
from backend.app.orchestration.dependency_checker import DependencyChecker
from backend.app.orchestration.resource_manager import ResourceManager
from backend.app.orchestration.policy_engine import PolicyEngine
from backend.app.orchestration.cache import orchestration_cache
from backend.app.orchestration.output_validator import OutputQualityValidator
from backend.app.orchestration.provenance import ProvenanceBuilder
from backend.app.orchestration.health import operational_health


class AgentController:
    """
    Main Agentic Controller for SatQuery AI.
    Drives job state machine: QUEUED -> VALIDATING -> PLANNING -> RUNNING -> GENERATING_EVIDENCE -> COMPLETED / FAILED.
    Synchronizes observable execution states, model runs, results, and artifacts with PostgreSQL.
    """
    async def _safe_db_op(self, coro_func):
        """Helper to execute database operations without crashing pipeline if DB is unavailable."""
        try:
            session_factory = get_session_maker()
            async with session_factory() as session:
                await coro_func(session)
                await session.commit()
        except Exception as e:
            logger.warning(f"Database persistence step non-fatal warning: {e}")

    async def run_pipeline(self, state: AgentState) -> AnalyzeResponse:
        pipeline_start = time.perf_counter()
        logger.info(f"Starting SatQuery advanced agent orchestration pipeline for request [{state.request_id}]")
        state.status = JobStatus.VALIDATING
        state.add_trace("Pipeline initialized", status="success")

        # Persist initial VALIDATING status in DB
        await self._safe_db_op(
            lambda s: JobRepository.create_or_get_job(
                s,
                job_id=state.request_id,
                query=state.query,
                status=JobStatus.VALIDATING.value
            )
        )

        orchestrated_plan: Optional[OrchestratedPlan] = None

        try:
            # 1. Advanced Planning: Input Analysis, Intent Classification, Capability Matching & DAG Generation
            state.status = JobStatus.PLANNING
            orchestrated_plan = AdvancedWorkflowPlanner.plan(state)
            plan = AdvancedWorkflowPlanner.to_legacy_workflow_plan(orchestrated_plan, state.parameters)

            state.plan = plan
            state.task = plan.task
            state.workflow_id = plan.workflow_id
            state.reason = plan.reason
            state.selected_models = plan.selected_models
            state.capability_id = orchestrated_plan.capability.capability_id
            state.routing_confidence = orchestrated_plan.routing_confidence
            state.query_entities = orchestrated_plan.intent.extracted_entities.model_dump(exclude_none=True)
            state.dag_plan = orchestrated_plan.dag_plan.model_dump()

            state.add_trace(
                f"Workflow planned: {plan.workflow_id}",
                status="success",
                details=f"Capability: {orchestrated_plan.capability.name}. Routing Confidence: {orchestrated_plan.routing_confidence:.2f}. Reason: {plan.reason}"
            )

            # Persist PLANNING status in DB
            await self._safe_db_op(
                lambda s: JobRepository.update_job_status(
                    s,
                    job_id=state.request_id,
                    status=JobStatus.PLANNING.value,
                    task_type=state.task.value if state.task else None
                )
            )

            # 2. Pre-Execution Dependency Check
            DependencyChecker.verify_plan_dependencies(
                capability=orchestrated_plan.capability,
                nodes=orchestrated_plan.dag_plan.nodes,
                num_images=len(state.image_paths)
            )
            state.add_trace("Pre-execution dependencies verified", status="success")

            # 3. System & GPU Resource Check
            ResourceManager.verify_resource_availability(
                model_name=plan.selected_models[0] if plan.selected_models else None
            )
            state.add_trace("System & VRAM memory headroom confirmed", status="success")

            # 4. Whitelist Plan Validation
            PlanValidator.validate_plan(plan)
            state.add_trace("Plan validated against tool whitelist", status="success")

            # 5. Check Deterministic Result Cache
            cache_key = orchestration_cache.compute_cache_key(
                image_paths=state.image_paths,
                query=state.query,
                capability_id=orchestrated_plan.capability.capability_id,
                parameters=state.parameters
            )
            cached_data = orchestration_cache.get(cache_key)

            if cached_data:
                state.answer = cached_data.get("answer")
                state.confidence = cached_data.get("confidence")
                state.cache_hit = True
                state.add_trace("Reused verified deterministic cache result", status="success")
            else:
                # 6. Execute Tools
                state.status = JobStatus.RUNNING
                await self._safe_db_op(
                    lambda s: JobRepository.update_job_status(
                        s,
                        job_id=state.request_id,
                        status=JobStatus.RUNNING.value
                    )
                )

                for tool_name in plan.steps:
                    if tool_name == "generate_report":
                        state.status = JobStatus.GENERATING_EVIDENCE
                    await SafeToolExecutor.execute_tool(tool_name, state)

                # 7. Output Quality Validation
                w = state.metadata[0].width if state.metadata else 256
                h = state.metadata[0].height if state.metadata else 256
                for mr in state.model_results:
                    if mr.model_name == "changeformer":
                        ch_warnings = OutputQualityValidator.validate_changeformer_output(mr, w, h)
                        if ch_warnings:
                            state.warnings.extend(ch_warnings)
                            state.quality_status = "REVIEW_REQUIRED"
                            state.quality_flags.extend(ch_warnings)

                # 8. Evaluate Confidence & Multi-Model Consistency
                scores = [r.confidence for r in state.model_results]
                state.confidence = ConfidenceEvaluator.evaluate(scores)

                # Check change consistency if applicable
                ch_res = next((r for r in state.model_results if r.task == "change_detection"), None)
                vqa_res = next((r for r in state.model_results if r.task in ["change_vqa", "vqa"]), None)
                ch_pixels = state.evidence.spatial.statistics.changed_pixels if state.evidence.spatial.statistics else 0
                consistency = ConsistencyChecker.check_change_consistency(ch_res, vqa_res, ch_pixels)
                state.evidence.consistency = consistency

                # Cache valid result
                if state.answer:
                    orchestration_cache.put(cache_key, {
                        "answer": state.answer,
                        "confidence": state.confidence
                    })

            # 9. Provenance Graph Construction
            state.artifacts = artifact_manager.list_artifacts(state.request_id)
            prov_graph = ProvenanceBuilder.build_provenance_graph(
                job_id=state.request_id,
                input_paths=state.image_paths,
                models_used=state.selected_models,
                artifacts_dict=state.artifacts,
                execution_trace=state.execution_trace,
                answer=state.answer
            )
            state.provenance_graph = prov_graph.model_dump()

            # Record operational health
            total_dur_ms = (time.perf_counter() - pipeline_start) * 1000.0
            operational_health.record_workflow_execution(
                workflow_id=plan.workflow_id,
                duration_ms=total_dur_ms,
                success=True
            )

            state.status = JobStatus.COMPLETED
            state.add_trace("Analysis completed successfully", status="success")

        except SatQueryException as e:
            state.status = JobStatus.FAILED
            state.errors.append(e.message)
            logger.error(f"[{state.request_id}] Pipeline aborted due to domain error: {e.message}")
            state.add_trace(f"Pipeline failed: {e.code}", status="error", details=e.message)
            if state.workflow_id:
                operational_health.record_workflow_execution(state.workflow_id, 0.0, success=False)
        except Exception as e:
            state.status = JobStatus.FAILED
            err_msg = str(e)
            state.errors.append(err_msg)
            logger.exception(f"[{state.request_id}] Unexpected error in agent pipeline: {err_msg}")
            state.add_trace("Pipeline failed with unexpected error", status="error", details=err_msg)
            if state.workflow_id:
                operational_health.record_workflow_execution(state.workflow_id, 0.0, success=False)

        # Build final response with orchestration metadata
        state.artifacts = artifact_manager.list_artifacts(state.request_id)
        orchestration_meta = None
        if orchestrated_plan:
            orchestration_meta = {
                "capability_id": orchestrated_plan.capability.capability_id,
                "capability_name": orchestrated_plan.capability.name,
                "routing_confidence": orchestrated_plan.routing_confidence,
                "query_entities": orchestrated_plan.intent.extracted_entities.model_dump(exclude_none=True),
                "dag_plan": orchestrated_plan.dag_plan.model_dump(),
                "provenance_graph": state.provenance_graph,
                "quality_status": state.quality_status,
                "quality_flags": state.quality_flags,
                "cache_hit": state.cache_hit
            }

        response = AnalyzeResponse(
            request_id=state.request_id,
            status=state.status,
            task=state.task or TaskType.UNSUPPORTED,
            workflow_id=state.workflow_id or "unknown",
            workflow_reason=state.reason or "No workflow determined.",
            answer=state.answer,
            confidence=state.confidence,
            models_used=state.selected_models,
            parameters=state.parameters,
            evidence=state.evidence,
            execution_trace=state.execution_trace,
            warnings=state.warnings,
            errors=state.errors,
            artifacts=state.artifacts,
            orchestration=orchestration_meta
        )

        # Persist result and trace JSON to filesystem
        artifact_manager.save_result_json(state.request_id, response.model_dump())
        artifact_manager.save_trace_json(state.request_id, [s.model_dump() for s in state.execution_trace])

        # Persist final state, results, model runs, execution steps, and artifacts to PostgreSQL
        async def _persist_final_db_records(s):
            # Update job status
            err_code = state.errors[0] if state.errors else None
            await JobRepository.update_job_status(
                s,
                job_id=state.request_id,
                status=state.status.value,
                error_code="PIPELINE_ERROR" if state.status == JobStatus.FAILED else None,
                error_message="; ".join(state.errors) if state.errors else None,
                task_type=state.task.value if state.task else None
            )

            # Model runs
            model_runs = []
            for mr in state.model_results:
                model_runs.append({
                    "model_name": mr.model_name,
                    "status": getattr(mr, "status", "SUCCESS"),
                    "device": getattr(mr, "device", None),
                    "duration_seconds": getattr(mr, "duration_seconds", None)
                })
            if not model_runs and state.selected_models:
                for m in state.selected_models:
                    model_runs.append({"model_name": m, "status": "SUCCESS"})
            if model_runs:
                await JobRepository.save_model_runs(s, state.request_id, model_runs)

            # Execution trace steps
            steps_data = [step.model_dump() for step in state.execution_trace]
            if steps_data:
                await JobRepository.save_execution_steps(s, state.request_id, steps_data)

            # Analysis results
            await JobRepository.save_analysis_result(
                s,
                job_id=state.request_id,
                answer=state.answer,
                confidence=state.confidence,
                result_json=response.model_dump()
            )

            # Artifacts
            art_items = []
            for art_type, file_list in state.artifacts.items():
                for fname in file_list:
                    fpath = artifact_manager.get_artifact_path(state.request_id, art_type, fname)
                    art_items.append({
                        "artifact_type": art_type,
                        "filesystem_path": str(fpath) if fpath else fname,
                        "mime_type": None
                    })
            if art_items:
                await JobRepository.save_artifacts(s, state.request_id, art_items)

        await self._safe_db_op(_persist_final_db_records)

        return response


# Global controller instance
agent_controller = AgentController()
