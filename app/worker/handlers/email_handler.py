from app.worker.event_processor import register_event


@register_event("email.send")
async def handle_email(event: dict) -> dict:
    payload = event["payload"]
    event_id = event.get("event_id")
    print(f"[EMAIL] start event_id={event_id} payload={payload}")
    try:
        print(f"[EMAIL] Sending email: {payload}")
        result = {"status": "sent"}
        print(f"[EMAIL] result event_id={event_id} result={result}")
        return result
    except Exception as e:
        print(f"[EMAIL] error event_id={event_id} error={e}")
        raise
