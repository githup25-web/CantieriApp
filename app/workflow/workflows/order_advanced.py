from typing import Any, Dict

from app.workflow.engine import (
    conditional_step,
    emit_step,
    emit_event,
    register_workflow,
    run_steps,
    wait_for_event,
)


@register_workflow("order.advanced")
async def order_advanced(context: dict[str, Any]):
    # Example workflow:
    # - validate order (worker emits order.validate.done)
    # - branch: payment.create if valid else order.reject
    # - wait for payment.done
    steps = [
        emit_step("order.validate", lambda ctx: {"order_id": ctx["order_id"]}),
        lambda ctx: wait_for_event("order.validate.done", ctx, "validation_result"),

        conditional_step(
            lambda ctx: ctx["validation_result"]["valid"],
            emit_step("payment.create", lambda ctx: {"order_id": ctx["order_id"]}),
            emit_step("order.reject", lambda ctx: {"order_id": ctx["order_id"]}),
            context,
        ),

        lambda ctx: wait_for_event("payment.done", ctx, "payment_result"),

        emit_step("shipment.create", lambda ctx: {"order_id": ctx["order_id"]}),
    ]

    await run_steps(steps, context)
    return {"status": "workflow_completed", "order_id": context["order_id"]}
