"""
SatQuery AI — honest refusal for analyses the agent cannot perform.

Routed here when the query asks for spectral indices or SAR polarimetry but the matching capability has
no execution branch, or the input lacks the bands the analysis needs. Previously such queries fell
through to the generic VQA model, which answered "compute NDVI for this scene" with "No." (project/qna.md
Q-013). The answer states what the analysis needs, what the image has, and what is not implemented.
"""
import re

from backend.app.agent.state import AgentState
from backend.app.agent.tools.base import register_tool
from backend.app.agent.tools.raster import inspect_raster

# index -> bands it needs
_INDICES = {
    "ndvi": "red and near-infrared (NIR)",
    "ndwi": "green and near-infrared (NIR)",
    "ndbi": "short-wave infrared (SWIR) and near-infrared (NIR)",
    "false color": "near-infrared (NIR)",
    "false-color": "near-infrared (NIR)",
    "infrared": "near-infrared (NIR)",
    "nir": "near-infrared (NIR)",
    "red edge": "red-edge",
}


@register_tool("explain_unsupported_request")
def explain_unsupported_request(state: AgentState) -> None:
    if not state.metadata:
        inspect_raster(state)
    meta = state.metadata[0] if state.metadata else None
    bands = meta.bands if meta else None
    fmt = meta.format if meta else "unknown format"
    q = state.query.lower()

    requested = next((k for k in _INDICES if re.search(r"\b" + re.escape(k) + r"\b", q)), None)
    if requested:
        name = requested.upper() if requested in ("ndvi", "ndwi", "ndbi", "nir") else requested
        if bands is not None and bands <= 3:
            reason = (f"{name} needs {_INDICES[requested]} bands, and this image has {bands} band(s) ({fmt}), "
                      f"which is visible colour only. It cannot be computed from this image.")
        else:
            reason = (f"{name} needs {_INDICES[requested]} bands. This image has {bands} band(s), but spectral-index "
                      f"computation is not implemented in this version of SatQuery.")
    elif re.search(r"\b(sar|polari[sz]ation|vv|vh|backscatter|decibel|db)\b", q):
        reason = ("SAR polarimetric analysis (VV/VH, backscatter in dB) is not implemented in this version of "
                  f"SatQuery. This image has {bands} band(s) ({fmt}).")
    else:
        reason = "This analysis is not implemented in this version of SatQuery."

    state.answer = (f"Not supported: {reason} For this image you can ask for a scene description, a question "
                    f"about its contents, or to find and segment an object.")
    state.confidence = None
    state.confidence_final = True
    state.warnings.append(f"Unsupported analysis requested: {reason}")
