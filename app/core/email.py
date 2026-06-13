import logging

logger = logging.getLogger("fastauth.email")


async def send_verification_email(user_id: str, email: str, token: str) -> None:
    """Stub: logs the verification token. Replace with real SMTP when ready."""
    logger.debug("Email verification token for user %s (%s): %s", user_id, email, token)
