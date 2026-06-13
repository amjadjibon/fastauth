import logging

logger = logging.getLogger("fastauth.email")


async def send_verification_email(user_id: str, email: str, token: str) -> None:
    """Stub: Replace with real SMTP when ready. Token intentionally omitted from logs."""
    logger.info("Verification email queued for user %s", user_id)
