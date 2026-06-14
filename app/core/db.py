# Re-export from shared.database so callers that import from app.core.db continue to work.
from app.shared.database import Base, engine, get_session  # noqa: F401
