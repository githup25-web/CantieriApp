from app.worker.event_processor import register_event


@register_event("notification.send")
async def handle_notification(event: dict) -> dict:
    payload = event["payload"]
    event_id = event.get("event_id")
    print(f"[NOTIFICATION] start event_id={event_id} payload={payload}")
    try:
        # placeholder: stampa o log
        print(f"[NOTIFICATION] Sending notification: {payload}")
        result = {"status": "sent"}
        print(f"[NOTIFICATION] result event_id={event_id} result={result}")
        return result
    except Exception as e:
        print(f"[NOTIFICATION] error event_id={event_id} error={e}")
        raise
