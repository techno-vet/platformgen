"""Widget manifest API — returns widget list with locked/unlocked state."""
import json
from pathlib import Path
from fastapi import APIRouter
import yaml

router = APIRouter()

_MANIFEST_PATH = Path(__file__).parent.parent / "data" / "widget_manifests.yaml"
_STATE_PATH = Path.home() / ".genny" / "platform_state.json"


def _load_state() -> dict:
    if _STATE_PATH.exists():
        try:
            return json.loads(_STATE_PATH.read_text())
        except Exception:
            pass
    return {"unlocked_widgets": [], "in_progress": [], "platform_type": "general"}


def _save_state(state: dict):
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(state, indent=2))


@router.get("/widgets")
async def get_widgets():
    """Return all widgets with lock state computed from depends_on."""
    try:
        manifest = yaml.safe_load(_MANIFEST_PATH.read_text())
    except Exception as e:
        return {"error": str(e), "widgets": []}

    state = _load_state()
    unlocked = set(state.get("unlocked_widgets", []))

    widgets = []
    for name, cfg in manifest.get("widgets", {}).items():
        depends_on = cfg.get("depends_on", [])
        deps_met = all(d in unlocked for d in depends_on)
        is_unlocked = name in unlocked or (not depends_on)  # foundation widgets always unlocked
        widgets.append({
            "id": name,
            "title": cfg.get("title", name),
            "purpose": cfg.get("purpose", ""),
            "depends_on": depends_on,
            "deps_met": deps_met,
            "unlocked": is_unlocked,
            "in_progress": name in state.get("in_progress", []),
        })

    return {"widgets": widgets, "state": state}


@router.post("/widgets/{widget_id}/unlock")
async def unlock_widget(widget_id: str):
    """Mark a widget as unlocked (called by Genny after setup complete)."""
    state = _load_state()
    if widget_id not in state["unlocked_widgets"]:
        state["unlocked_widgets"].append(widget_id)
    if widget_id in state.get("in_progress", []):
        state["in_progress"].remove(widget_id)
    _save_state(state)
    return {"ok": True, "unlocked": widget_id}
