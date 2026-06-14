from fastapi import APIRouter, HTTPException, status

from app.auth.deps import CurrentUser, SessionDep
from app.auth.sessions import service as session_service
from app.auth.sessions.schemas import SessionResponse, SessionsListResponse

router = APIRouter(prefix="/auth/sessions", tags=["sessions"])


@router.get("", response_model=SessionsListResponse)
async def list_sessions(current_user: CurrentUser, session: SessionDep):
    sessions = await session_service.list_active_sessions(session, current_user.id)
    items = [
        SessionResponse(
            id=s.id,
            device_type=s.device_type,
            device_name=s.device_name,
            browser=s.browser,
            os=s.os,
            ip_address=s.ip_address,
            last_active_at=s.last_active_at,
            created_at=s.created_at,
            expires_at=s.expires_at,
        )
        for s in sessions
    ]
    return SessionsListResponse(sessions=items, total=len(items))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(session_id: str, current_user: CurrentUser, session: SessionDep):
    revoked = await session_service.revoke_session(session, session_id, current_user.id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_sessions(current_user: CurrentUser, session: SessionDep):
    await session_service.revoke_all_user_sessions(session, current_user.id)
