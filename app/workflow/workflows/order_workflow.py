from app.workflow.engine import emit_event, register_workflow


@register_workflow("order.process")
async def order_process(context: dict) -> dict:
    order_id = context["order_id"]

    # Step 1: valida ordine
    await emit_event("order.validate", {"order_id": order_id})

    # Step 2: se validato, genera pagamento
    await emit_event("payment.create", {"order_id": order_id})

    # Step 3: dopo pagamento, genera spedizione
    await emit_event("shipment.create", {"order_id": order_id})

    return {"status": "workflow_started", "order_id": order_id}
