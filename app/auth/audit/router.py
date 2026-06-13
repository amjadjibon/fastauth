import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlmodel import select

from app.auth.db_models import AuditLog
from app.auth.deps import CurrentUser, SessionDep
from app.auth.rbac.dependencies import RequireRoles

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
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)  # type: ignore[attr-defined]
    result = await session.exec(query)
    logs = list(result.all())
    return {
        "logs": [
            {
                "id": l.id,
                "event_type": l.event_type,
                "user_id": l.user_id,
                "ip_address": l.ip_address,
                "outcome": l.outcome,
                "created_at": l.created_at.isoformat(),
                "metadata": json.loads(l.metadata_json) if l.metadata_json else None,
            }
            for l in logs
        ],
        "total": len(logs),
    }


@router.get("/logs/export", dependencies=[RequireRoles(["admin"])])
async def export_audit_logs(
    session: SessionDep,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    limit: int = Query(default=10000, le=50000),
):
    result = await session.exec(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)  # type: ignore[attr-defined]
    )
    logs = list(result.all())

    if format == "json":
        data = json.dumps([
            {
                "id": l.id,
                "event_type": l.event_type,
                "user_id": l.user_id,
                "ip_address": l.ip_address,
                "outcome": l.outcome,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ])
        return StreamingResponse(
            iter([data]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "event_type", "user_id", "ip_address", "outcome", "created_at"])
    for l in logs:
        writer.writerow([l.id, l.event_type, l.user_id, l.ip_address, l.outcome, l.created_at.isoformat()])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
