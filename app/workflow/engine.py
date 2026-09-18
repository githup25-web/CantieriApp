import asyncio
import importlib
import pkgutil
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, cast

from app.models.event_queue import EventQueue
from app.models.workflow_instance import WorkflowInstance

WORKFLOWS: Dict[str, Callable[[dict[str, Any]], Awaitable[Any]]] = {}


def register_workflow(name: str):
    def decorator(func: Callable[[dict[str, Any]], Awaitable[Any]]):
        WORKFLOWS[name] = func
        return func

    return decorator


class WaitForEventSignal(Exception):
    """
    Internal signal to make `wait_for_event()` non-blocking.
    """

    def __init__(self, event_name: str, context_key: str, timeout_seconds: int):
        super().__init__(f"waiting for {event_name}.done (context_key={context_key})")
        self.event_name = event_name
        self.context_key = context_key
        self.timeout_seconds = timeout_seconds


class WorkflowEngineError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def create_instance(
    name: str,
    context: dict[str, Any],
    steps: list[Callable[[dict[str, Any]], Awaitable[Any]]],
) -> WorkflowInstance:
    now = _utc_now()
    instance = WorkflowInstance(
        workflow_name=name,
        context=context,
        state="pending",
        current_step=0,
        steps=[f"step_{i}" for i in range(len(steps))],
        created_at=now,
        updated_at=now,
        error=None,
    )
    await instance.insert()
    return instance


async def update_instance(instance: WorkflowInstance, **fields: Any) -> None:
    for k, v in fields.items():
        setattr(instance, k, v)
    instance.updated_at = _utc_now()
    await instance.save()


async def start_workflow(name: str, context: dict[str, Any]):
    wf = WORKFLOWS.get(name)
    if wf is None:
        raise ValueError(f"Workflow not found: {name}")

    # Markers used by run_steps()
    context.setdefault("__workflow_name", name)

    return await wf(context)


async def emit_event(
    event_name: str,
    payload: dict[str, Any],
    *,
    max_attempts: int = 5,
) -> str:
    event_instance_id = f"wf_{event_name}_{_utc_now().timestamp()}".replace(".", "_")
    ev = EventQueue(
        event_instance_id=event_instance_id,
        event_name=event_name,
        payload=payload,
        occurred_at=_utc_now(),
        state="pending",
        attempts=0,
        last_error=None,
        next_attempt_at=None,
        max_attempts=max_attempts,
    )
    await ev.insert()
    return event_instance_id


async def run_steps(
    steps: list[Callable[[dict[str, Any]], Awaitable[Any]]],
    context: dict[str, Any],
):
    """
    Persist workflow progress and support non-blocking waiting for events.
    """
    workflow_name = cast(Optional[str], context.get("__workflow_name"))
    if not workflow_name:
        raise WorkflowEngineError("Missing __workflow_name in context. Workflows must call run_steps().")

    instance_id = cast(Optional[str], context.get("__workflow_instance_id"))

    if instance_id:
        instance = await WorkflowInstance.find_one(WorkflowInstance.id == instance_id)
    else:
        instance = None

    if instance is None:
        instance = await create_instance(workflow_name, context, steps)
        instance_id = str(instance.id)
        context["__workflow_instance_id"] = instance_id

    await update_instance(instance, state="running", context=context)

    # Runtime invariant: instance_id exists
    assert instance_id is not None

    while True:
        # Always reload to get the latest persisted step/state
        instance = await WorkflowInstance.get(instance_id)
        idx = instance.current_step

        if idx >= len(steps):
            await update_instance(instance, state="done", error=None, context=context)
            return

        try:
            await steps[idx](context)

            # Step completed
            await update_instance(
                instance,
                current_step=idx + 1,
                state="running",
                error=None,
                context=context,
            )

        except WaitForEventSignal as sig:
            # Wait step reached (event not ready yet)
            await update_instance(
                instance,
                state="waiting",
                current_step=idx,
                error=None,
                context=context,
            )

            # Store wait parameters for monitoring/diagnostics
            context.setdefault("__wait_for_event", {})
            context["__wait_for_event"] = {
                "event_name": sig.event_name,
                "context_key": sig.context_key,
                "timeout_seconds": sig.timeout_seconds,
            }
            await update_instance(instance, context=context)
            return

        except Exception as e:
            await update_instance(instance, state="error", error=str(e), context=context)
            return


async def conditional_step(
    condition: Callable[[dict[str, Any]], bool],
    step_true: Callable[[dict[str, Any]], Awaitable[Any]],
    step_false: Callable[[dict[str, Any]], Awaitable[Any]],
    context: dict[str, Any],
):
    if condition(context):
        return await step_true(context)
    return await step_false(context)


def emit_step(event_name: str, payload_builder: Callable[[dict[str, Any]], dict[str, Any]]):
    async def _step(context: dict[str, Any]):
        payload = payload_builder(context)
        await emit_event(event_name, payload)

    return _step


async def wait_for_event(
    event_name: str,
    context: dict[str, Any],
    context_key: str,
    timeout_seconds: int = 30,
):
    """
    Non-blocking wait:
    - if done event already exists => set context[context_key] and return result
    - otherwise => raise WaitForEventSignal so engine persists state="waiting"
      and the scheduler can resume later.
    """
    done_event_name = event_name if event_name.endswith(".done") else (event_name + ".done")

    ev = await EventQueue.find_one(
        (EventQueue.event_name == done_event_name) & (EventQueue.state == "done")
    )
    if ev is not None:
        payload = ev.payload or {}
        result = payload.get("result")
        context[context_key] = result
        return result

    raise WaitForEventSignal(event_name=event_name, context_key=context_key, timeout_seconds=timeout_seconds)


_loaded_workflows: bool = False


def _load_workflows() -> None:
    global _loaded_workflows
    if _loaded_workflows:
        return

    pkg = "app.workflow.workflows"
    search_path = pkg.replace(".", "/")

    for _, module_name, _ in pkgutil.iter_modules([search_path]):
        importlib.import_module(f"{pkg}.{module_name}")

    _loaded_workflows = True


async def resume_workflow(instance: WorkflowInstance) -> None:
    """
    Resume a waiting workflow instance by re-invoking its workflow callable.
    """
    wf = WORKFLOWS.get(instance.workflow_name)
    if wf is None:
        await update_instance(instance, state="error", error=f"Workflow not found: {instance.workflow_name}", context=instance.context)
        return

    # Ensure markers exist
    instance_context = instance.context or {}
    instance_context["__workflow_name"] = instance.workflow_name
    instance_context["__workflow_instance_id"] = str(instance.id)

    await update_instance(instance, state="running", context=instance_context)
    try:
        await wf(instance_context)
    except Exception as e:
        await update_instance(instance, state="error", error=str(e), context=instance_context)


# Auto-load workflows on import
_load_workflows()
