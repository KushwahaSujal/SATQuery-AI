"""Repository-backed Markdown documentation endpoints."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.app.config import settings

router = APIRouter(tags=["Documentation"])

_MAX_DOCUMENT_BYTES = 512 * 1024
_EXCLUDED_PARTS = {".git", ".next", "node_modules", ".venv", "__pycache__", "checkpoints", "results"}
# Internal assistant/user preference files are kept in the repository but are not
# part of the user-facing documentation library.
_HIDDEN_DOCUMENTS = {
    ".commandcode/taste/taste.md",
    ".commandcode/taste/user-taste-profile/taste.md",
    ".pytest_cache/README.md",
    "frontend-v2/.commandcode/taste/taste.md",
    "frontend-v2/.commandcode/taste/user-taste-profile/taste.md",
    "frontend/AGENTS.md",
    "frontend/CLAUDE.md",
    "frontend/README.md",
    "frontend/SATQUERY_AI_FRONTEND_API_CONTRACT.md",
    "frontend/FRONTEND_POLISH.md",
    "frontend/SatQuery_FRONTEND_POLISH_2026-09-14.md",
    "project/handoff/ask-ayushman.md",
    "project/handoff/ppt-assets/README.md",
    "project/handoff/ppt-results.md",
    "project/memory.md",
    "project/plan-2026-09-14-agent-parity-geo.md",
    "project/split-ushnik-ayushman.md",
    "project/tasks.md",
    "project/decisions.md",
    "project/design.md",
    "project/phases.md",
    "project/prd.md",
    "project/qna.md",
    "project/restructure.md",
    "project/rules.md",
    "third_party/GeoChat/README.md",
    "third_party/GeoChat/docs/Customize_Component.md",
    "third_party/GeoChat/docs/Data.md",
    "third_party/GeoChat/docs/Evaluation.md",
    "third_party/GeoChat/docs/LoRA.md",
    "third_party/GeoChat/docs/MODEL_ZOO.md",
}


def _repository_root() -> Path:
    return settings.root_dir.resolve()


def _is_allowed(path: Path) -> bool:
    root = _repository_root()
    try:
        relative = path.resolve().relative_to(root)
    except ValueError:
        return False
    relative_path = relative.as_posix()
    return (
        path.suffix.lower() == ".md"
        and relative_path not in _HIDDEN_DOCUMENTS
        and not any(part in _EXCLUDED_PARTS for part in relative.parts)
    )


def _title(path: Path, content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ").replace("-", " ").title()


def _summary(content: str) -> str:
    for line in content.splitlines():
        text = line.strip()
        if text and not text.startswith("#") and not text.startswith("```") and len(text) > 24:
            return text[:220] + ("..." if len(text) > 220 else "")
    return "Repository Markdown documentation."


def _catalog() -> list[dict[str, Any]]:
    root = _repository_root()
    documents = []
    for path in root.rglob("*.md"):
        if not _is_allowed(path):
            continue
        relative = path.resolve().relative_to(root).as_posix()
        content = path.read_text(encoding="utf-8", errors="replace")
        documents.append({
            "path": relative,
            "title": _title(path, content),
            "summary": _summary(content),
            "bytes": path.stat().st_size,
            "sections": sum(1 for line in content.splitlines() if line.startswith("#")),
            "updated_at": path.stat().st_mtime,
            "search_text": content.lower(),
        })
    return sorted(documents, key=lambda item: item["path"].lower())


@router.get("/documentation")
async def list_documentation() -> dict[str, Any]:
    documents = _catalog()
    return {"documents": documents, "count": len(documents)}


@router.get("/documentation/content")
async def get_documentation_content(path: str = Query(..., min_length=1)) -> dict[str, Any]:
    root = _repository_root()
    document = (root / path).resolve()
    if not _is_allowed(document) or not document.is_file():
        raise HTTPException(status_code=404, detail="Documentation file not found")
    if document.stat().st_size > _MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Documentation file is too large to display")
    return {
        "path": document.relative_to(root).as_posix(),
        "content": document.read_text(encoding="utf-8", errors="replace"),
    }
