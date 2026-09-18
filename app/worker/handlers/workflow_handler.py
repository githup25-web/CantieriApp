from typing import Any, Dict

from app.worker.event_processor import register_event
from app.workflow.engine import start_workflow


@register_event("workflow.start")
async def handle_workflow_start(event: Dict[str, Any]) -> Any:
    payload = event.get("payload") or {}
    workflow_name = payload["name"]
    context = payload.get("context", {})
    return await start_workflow(workflow_name, context)
