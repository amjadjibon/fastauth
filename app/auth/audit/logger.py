import json
import logging
import re

from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.db_models import AuditLog

logger = logging.getLogger("fastauth.audit")


def _mask_email(email: str) -> str:
    parts = email.split("@")
    if len(parts) != 2:
        return "***"
    local, domain = parts
    masked = local[:2] + "***" if len(local) > 2 else "***"
    return f"{masked}@{domain}"


def _mask_ip(ip: str | None) -> str | None:
    if not ip:
        return ip
    # Mask last octet for IPv4
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3]) + ".***"
    return ip


async def audit_log(
    session: AsyncSession,
    event_type: str,
    *,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict | None = None,
    outcome: str = "success",
) -> AuditLog:
    metadata_json = None
    if metadata:
        # Mask sensitive fields
        safe_meta = {}
        for k, v in metadata.items():
            if k == "email" and isinstance(v, str):
                safe_meta[k] = _mask_email(v)
            else:
                safe_meta[k] = v
        metadata_json = json.dumps(safe_meta)

    entry = AuditLog(
        event_type=event_type,
        user_id=user_id,
        ip_address=_mask_ip(ip_address),
        user_agent=user_agent,
        metadata_json=metadata_json,
        outcome=outcome,
    )
    session.add(entry)
    await session.commit()

    logger.info(
        "audit event",
        extra={
            "event_type": event_type,
            "user_id": user_id,
            "outcome": outcome,
        },
    )
    return entry
