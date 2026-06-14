import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.auth.models import AuditLog
from app.auth.deps import SessionDep
from app.auth.rbac.deps import RequireRoles

router = APIRouter(prefix="/auth/audit", tags=["audit"])


@router.get("/logs", dependencies=[RequireRoles(["admin"])])
async def list_audit_logs(
    session: SessionDep,
    user_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=50, le=1000),
    offset: int = Query(default=0),
):
    query = select(AuditLog)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if since:
        query = query.where(AuditLog.created_at >= since)
    if until:
        query = query.where(AuditLog.created_at <= until)
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)  # type: ignore
    result = await session.execute(query)
    logs = list(result.scalars().all())
    return {
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "user_id": log.user_id,
                "ip_address": log.ip_address,
                "outcome": log.outcome,
                "created_at": log.created_at.isoformat(),
                "metadata": json.loads(log.metadata_json) if log.metadata_json else None,
            }
            for log in logs
        ],
        "total": len(logs),
    }


@router.get("/logs/export", dependencies=[RequireRoles(["admin"])])
async def export_audit_logs(
    session: SessionDep,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    limit: int = Query(default=10000, le=50000),
):
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)  # type: ignore
    )
    logs = list(result.scalars().all())

    if format == "json":
        data = json.dumps(
            [
                {
                    "id": log.id,
                    "event_type": log.event_type,
                    "user_id": log.user_id,
                    "ip_address": log.ip_address,
                    "outcome": log.outcome,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ]
        )
        return StreamingResponse(
            iter([data]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "event_type", "user_id", "ip_address", "outcome", "created_at"])
    for log in logs:
        writer.writerow(
            [log.id, log.event_type, log.user_id, log.ip_address, log.outcome, log.created_at.isoformat()]
        )

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
