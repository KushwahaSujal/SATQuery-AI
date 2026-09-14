"""Routing: caption wording, and honest refusal for analyses the agent cannot run (project/qna.md Q-013)."""
import numpy as np
import pytest
import tifffile
from PIL import Image

from backend.app.agent.state import AgentState
from backend.app.agent.tools.base import TOOL_REGISTRY
from backend.app.agent.validator import PlanValidator
from backend.app.orchestration.dependency_graph import DependencyGraph
from backend.app.orchestration.input_analyzer import InputAnalyzer
from backend.app.orchestration.intent_classifier import IntentClassifier
from backend.app.orchestration.matcher import CapabilityMatcher


@pytest.mark.parametrize("query,task", [
    ("describe this image", "single_image_caption"),
    ("give me a description of the scene", "single_image_caption"),
    ("what does this image show?", "single_image_caption"),
    ("summarise this scene", "single_image_caption"),
    ("describe the red car at the bottom", "single_image_grounding"),  # grounding keeps priority
    ("how many buildings are in this image?", "single_image_vqa"),
    ("compute NDVI for this scene", "multispectral_analysis"),
])
def test_intent_wording(query, task):
    assert IntentClassifier.classify_intent(query, num_inputs=1).task == task


def _route(query, path):
    facts, _ = InputAnalyzer.analyze([str(path)])
    intent = IntentClassifier.classify_intent(query, num_inputs=1, modalities=facts.modalities)
    return CapabilityMatcher.match(intent, facts)[0].capability_id


@pytest.fixture
def rgb_png(tmp_path):
    p = tmp_path / "rgb.png"
    Image.fromarray(np.zeros((64, 64, 3), np.uint8)).save(p)
    return p


@pytest.fixture
def ms_tif(tmp_path):
    p = tmp_path / "ms.tif"
    tifffile.imwrite(p, np.random.default_rng(0).integers(0, 4000, (4, 64, 64), dtype=np.uint16))
    return p


def test_spectral_request_on_rgb_routes_to_explanation_not_vqa(rgb_png):
    assert _route("compute NDVI for this scene", rgb_png) == "unsupported_analysis"
    assert _route("show SAR backscatter in dB", rgb_png) == "unsupported_analysis"


def test_spectral_request_on_multispectral_routes_to_explanation_while_unimplemented(ms_tif):
    assert not DependencyGraph.has_branch_for("multispectral_analysis")
    assert _route("compute NDVI for this scene", ms_tif) == "unsupported_analysis"


def test_explanation_names_missing_bands_or_missing_implementation(rgb_png, ms_tif):
    tool = TOOL_REGISTRY["explain_unsupported_request"]
    rgb = AgentState(request_id="u1", query="compute NDVI for this scene", image_paths=[str(rgb_png)])
    tool(rgb)
    assert rgb.answer.startswith("Not supported: NDVI needs red and near-infrared (NIR) bands, and this image has 3 band(s)")
    assert rgb.confidence is None and rgb.confidence_final

    ms = AgentState(request_id="u2", query="compute NDWI", image_paths=[str(ms_tif)])
    tool(ms)
    assert "This image has 4 band(s), but spectral-index computation is not implemented" in ms.answer

    sar = AgentState(request_id="u3", query="show VV VH polarization", image_paths=[str(rgb_png)])
    tool(sar)
    assert "SAR polarimetric analysis" in sar.answer


def test_every_tool_in_every_executable_dag_is_whitelisted_and_registered():
    # PlanValidator keeps its own tool whitelist, separate from the registry and capability definitions;
    # a new capability missing from it fails at run time with a "security violation" (found in Q-013).
    for cap in DependencyGraph.KNOWN_CAPABILITIES:
        for node in DependencyGraph.build_dag_for_capability(cap).nodes:
            assert node.tool_name in PlanValidator.PERMITTED_TOOLS, (cap, node.tool_name)
            assert node.tool_name in TOOL_REGISTRY, (cap, node.tool_name)
