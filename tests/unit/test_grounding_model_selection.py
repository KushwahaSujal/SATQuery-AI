"""Which detector run_grounding asks the grounding pipeline for."""

import pytest

from backend.app.agent.state import AgentState
from backend.app.agent.tools.inference import _resolve_grounding_model


def _state(parameters=None, selected=None):
    state = AgentState.__new__(AgentState)
    state.parameters = parameters or {}
    state.selected_models = selected or ["grounding_dino", "sam2"]
    return state


def test_default_is_auto(monkeypatch):
    monkeypatch.delenv("SATQUERY_GROUNDING_MODEL", raising=False)
    assert _resolve_grounding_model(_state()) == "auto"


def test_env_selects_locate_anything(monkeypatch):
    monkeypatch.setenv("SATQUERY_GROUNDING_MODEL", "locate_anything")
    assert _resolve_grounding_model(_state()) == "locate_anything"


def test_request_parameter_wins_over_env(monkeypatch):
    monkeypatch.setenv("SATQUERY_GROUNDING_MODEL", "locate_anything")
    assert _resolve_grounding_model(_state({"grounding_model": "Grounding_DINO"})) == "grounding_dino"


def test_selected_models_still_honoured(monkeypatch):
    monkeypatch.delenv("SATQUERY_GROUNDING_MODEL", raising=False)
    assert _resolve_grounding_model(_state(selected=["locate_anything"])) == "locate_anything"


def test_unknown_value_is_rejected(monkeypatch):
    monkeypatch.delenv("SATQUERY_GROUNDING_MODEL", raising=False)
    with pytest.raises(ValueError):
        _resolve_grounding_model(_state({"grounding_model": "yolo"}))
