from typing import Any, Dict, Optional


class SatQueryException(Exception):
    """Base exception for all SatQuery AI application errors."""
    def __init__(
        self,
        message: str,
        code: str = "SATQUERY_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 400
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code

    def to_dict(self) -> Dict[str, Any]:
        job_id = self.details.get("job_id") or self.details.get("request_id")
        workflow = self.details.get("workflow") or self.details.get("workflow_id")
        err: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "job_id": job_id
        }
        if workflow:
            err["workflow"] = workflow
        return {"error": err}


class InvalidInputError(SatQueryException):
    """Raised when user input (files or query) is malformed or invalid."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, code: str = "INVALID_INPUT"):
        super().__init__(message, code=code, details=details, status_code=400)


class InvalidRequestError(InvalidInputError):
    """Raised when an API request payload or parameters are invalid."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, status_code: int = 400):
        super().__init__(message, details=details, code="INVALID_REQUEST")
        self.status_code = status_code


class UnsupportedFormatError(SatQueryException):
    """Raised when an uploaded file is not a supported raster format."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="UNSUPPORTED_MEDIA", details=details, status_code=415)


UnsupportedMediaError = UnsupportedFormatError


class ModalityDetectionError(SatQueryException):
    """Raised when modality cannot be determined or is unsupported."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="MODALITY_DETECTION_ERROR", details=details, status_code=422)


class PairValidationError(SatQueryException):
    """Raised when two uploaded rasters fail pair-compatibility checks."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="INVALID_TEMPORAL_PAIR", details=details, status_code=422)


InvalidTemporalPairError = PairValidationError


class TemporalAlignmentRequiredError(SatQueryException):
    """Raised when bi-temporal rasters lack spatial co-registration or CRS alignment."""
    def __init__(self, message: str = "Bi-temporal rasters are not co-registered or lack alignment.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="TEMPORAL_ALIGNMENT_REQUIRED", details=details, status_code=422)


class ModelUnavailableError(SatQueryException):
    """Raised when a requested model checkpoint is missing or disabled."""
    def __init__(self, model_name: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None, code: str = "MODEL_CHECKPOINT_MISSING"):
        msg = message or f"Model checkpoint for '{model_name}' is not configured or missing."
        det = details or {}
        det["model"] = model_name
        super().__init__(msg, code=code, details=det, status_code=503)


class ModelNotConfiguredError(ModelUnavailableError):
    """Raised when a requested model is not configured."""
    def __init__(self, model_name: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(model_name=model_name, message=message, details=details, code="MODEL_NOT_CONFIGURED")


class InferenceError(SatQueryException):
    """Raised when model inference execution fails."""
    def __init__(self, message: str, model_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None, code: str = "MODEL_INFERENCE_ERROR"):
        det = details or {}
        if model_name:
            det["model"] = model_name
        super().__init__(message, code=code, details=det, status_code=500)


ModelInferenceError = InferenceError


class IndexNotAvailableError(SatQueryException):
    """Raised when a requested spectral index cannot be computed due to missing bands."""
    def __init__(self, index_name: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        msg = message or f"Spectral index '{index_name}' cannot be calculated: required bands missing."
        det = details or {}
        det["index"] = index_name
        super().__init__(msg, code="INDEX_NOT_AVAILABLE", details=det, status_code=400)


class VisualizationNotAvailableError(SatQueryException):
    """Raised when a requested visualization layer is unsupported or not generated."""
    def __init__(self, layer_id: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        msg = message or f"Visualization layer '{layer_id}' is not available for this job."
        det = details or {}
        det["layer_id"] = layer_id
        super().__init__(msg, code="VISUALIZATION_NOT_AVAILABLE", details=det, status_code=404)


class ArtifactNotFoundError(SatQueryException):
    """Raised when an evidence artifact file cannot be found on disk."""
    def __init__(self, artifact_name: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        msg = message or f"Artifact '{artifact_name}' was not found."
        det = details or {}
        det["artifact"] = artifact_name
        super().__init__(msg, code="ARTIFACT_NOT_FOUND", details=det, status_code=404)


class NoRelevantEventsFoundError(SatQueryException):
    """Raised when video analysis query finds no matching activity in footage."""
    def __init__(self, message: str = "No relevant events detected matching the query in footage.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="NO_RELEVANT_EVENTS_FOUND", details=details, status_code=404)


class JobNotFoundError(SatQueryException):
    """Raised when a queried job ID does not exist."""
    def __init__(self, job_id: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        msg = message or f"Job '{job_id}' does not exist."
        det = details or {}
        det["job_id"] = job_id
        super().__init__(msg, code="JOB_NOT_FOUND", details=det, status_code=404)


class WorkflowError(SatQueryException):
    """Raised when workflow execution or validation fails."""
    def __init__(self, message: str, workflow_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        det = details or {}
        if workflow_id:
            det["workflow_id"] = workflow_id
        super().__init__(message, code="WORKFLOW_ERROR", details=det, status_code=500)


class DatabaseUnavailableError(SatQueryException):
    """Raised when PostgreSQL database is unreachable or unavailable."""
    def __init__(self, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        msg = message or "PostgreSQL database is currently unavailable."
        super().__init__(msg, code="DATABASE_UNAVAILABLE", details=details, status_code=503)
