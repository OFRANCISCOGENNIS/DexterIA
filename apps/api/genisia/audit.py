from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .models import AuditEvent
from .security import redact


def record(
    db: Session,
    action: str,
    *,
    actor_id: str | None = None,
    actor_label: str = "user",
    project_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    """Registra um evento de auditoria (o commit fica a cargo do chamador)."""
    safe_details = {k: (redact(v) if isinstance(v, str) else v) for k, v in (details or {}).items()}
    event = AuditEvent(
        action=action,
        actor_id=actor_id,
        actor_label=actor_label,
        project_id=project_id,
        target_type=target_type,
        target_id=target_id,
        details=safe_details,
    )
    db.add(event)
    return event
