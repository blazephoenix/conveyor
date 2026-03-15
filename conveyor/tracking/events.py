from datetime import datetime, timezone


def format_event(entity_id: str, event_type: str, detail: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"[{ts}] {entity_id} {event_type}: {detail}"


def emit(log: list[str], entity_id: str, event_type: str, detail: str) -> str:
    entry = format_event(entity_id, event_type, detail)
    log.append(entry)
    return entry
