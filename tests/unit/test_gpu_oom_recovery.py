"""CUDA out-of-memory recovery: release resident models, retry, and report what happened."""
import asyncio

import numpy as np
import pytest
import torch

from backend.app.agent.executor import SafeToolExecutor
from backend.app.agent.state import AgentState
from backend.app.agent.tools.base import TOOL_REGISTRY
from backend.app.ml.adapters.changeformer import ChangeFormerAdapter
from backend.app.ml.registry import model_registry


class FlakyNet(torch.nn.Module):
    """Raises OOM for the first `fail_n` calls, then returns 5-scale logits like ChangeFormerV6."""
    def __init__(self, fail_n, fail_at_or_above=None):
        super().__init__()
        self.calls, self.fail_n, self.fail_at_or_above = 0, fail_n, fail_at_or_above

    def forward(self, a, b):
        self.calls += 1
        too_big = self.fail_at_or_above is not None and a.shape[-1] >= self.fail_at_or_above
        if self.calls <= self.fail_n or too_big:
            raise torch.OutOfMemoryError("CUDA out of memory (simulated)")
        return [torch.zeros(1, 2, a.shape[-2], a.shape[-1])]


def _adapter(net, monkeypatch, released=("grounding_dino", "sam2")):
    ad = ChangeFormerAdapter()
    ad._model, ad._loaded, ad.device = net, True, torch.device("cpu")
    monkeypatch.setattr(model_registry, "release_gpu_memory", lambda exclude=(): list(released))
    return ad


def test_changeformer_recovers_by_releasing_other_models(monkeypatch):
    ad = _adapter(FlakyNet(fail_n=1), monkeypatch)
    res = ad.predict(np.zeros((256, 256, 3), np.uint8), np.zeros((256, 256, 3), np.uint8))
    rec = res.metadata["oom_recovery"]
    assert rec == {"released_models": ["grounding_dino", "sam2"], "resolved_by": "released_other_models"}
    assert res.metadata["inference_mode"] == "native"


def test_changeformer_falls_back_to_windows_when_release_is_not_enough(monkeypatch):
    ad = _adapter(FlakyNet(fail_n=0, fail_at_or_above=600), monkeypatch)
    res = ad.predict(np.zeros((1024, 1024, 3), np.uint8), np.zeros((1024, 1024, 3), np.uint8))
    assert res.metadata["oom_recovery"]["resolved_by"] == "windowed_512"
    assert res.metadata["inference_mode"] == "windowed_512"
    assert res.masks[0]["binary_mask"].shape == (1024, 1024)


def test_no_recovery_metadata_when_memory_is_fine(monkeypatch):
    ad = _adapter(FlakyNet(fail_n=0), monkeypatch)
    res = ad.predict(np.zeros((64, 64, 3), np.uint8), np.zeros((64, 64, 3), np.uint8))
    assert res.metadata["oom_recovery"] is None


def test_executor_releases_and_retries_heavy_tool_once(monkeypatch):
    calls = {"n": 0, "released": 0}

    def flaky_tool(state):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("ChangeFormer inference execution failed: CUDA out of memory. Tried to allocate 1024.00 MiB")

    monkeypatch.setitem(TOOL_REGISTRY, "run_change_detection", flaky_tool)
    monkeypatch.setattr(model_registry, "release_gpu_memory", lambda exclude=(): calls.__setitem__("released", calls["released"] + 1) or ["sam2"])
    state = AgentState(request_id="oom-test", query="q", image_paths=[])
    asyncio.run(SafeToolExecutor.execute_tool("run_change_detection", state))
    assert calls == {"n": 2, "released": 1}
    assert any("GPU memory released" in s.step for s in state.execution_trace)


def test_executor_does_not_retry_non_oom_errors(monkeypatch):
    calls = {"n": 0}

    def broken_tool(state):
        calls["n"] += 1
        raise ValueError("bad input")

    monkeypatch.setitem(TOOL_REGISTRY, "run_change_detection", broken_tool)
    state = AgentState(request_id="oom-test-2", query="q", image_paths=[])
    with pytest.raises(ValueError):
        asyncio.run(SafeToolExecutor.execute_tool("run_change_detection", state))
    assert calls["n"] == 1
