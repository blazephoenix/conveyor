from conveyor.tracking.events import emit, format_event


def test_format_event():
    event = format_event("ISS-001", "status_change", "created → queued")
    assert "ISS-001" in event
    assert "status_change" in event
    assert "created → queued" in event


def test_emit_appends_to_log():
    log: list[str] = []
    emit(log, "ISS-001", "status_change", "created → queued")
    assert len(log) == 1
    emit(log, "ISS-001", "agent_started", "backend agent executing")
    assert len(log) == 2
