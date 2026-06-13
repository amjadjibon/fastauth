from fastapi import Request


def parse_user_agent(request: Request) -> dict:
    """Extract device_type, browser, os from User-Agent header."""
    ua = request.headers.get("user-agent", "")
    ip = _get_client_ip(request)

    browser = _detect_browser(ua)
    os_name = _detect_os(ua)
    device_type = _detect_device_type(ua)
    device_name = f"{browser} on {os_name}" if browser and os_name else ua[:128]

    return {
        "user_agent": ua[:512],
        "ip_address": ip,
        "browser": browser,
        "os": os_name,
        "device_type": device_type,
        "device_name": device_name,
    }


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _detect_browser(ua: str) -> str:
    if "Edg/" in ua:
        return "Edge"
    if "OPR/" in ua or "Opera/" in ua:
        return "Opera"
    if "Firefox/" in ua:
        return "Firefox"
    if "Chrome/" in ua:
        return "Chrome"
    if "Safari/" in ua:
        return "Safari"
    return "Unknown"


def _detect_os(ua: str) -> str:
    if "Windows" in ua:
        return "Windows"
    if "Mac OS X" in ua or "Macintosh" in ua:
        return "macOS"
    if "iPhone" in ua or "iPad" in ua:
        return "iOS"
    if "Android" in ua:
        return "Android"
    if "Linux" in ua:
        return "Linux"
    return "Unknown"


def _detect_device_type(ua: str) -> str:
    if "Mobile" in ua or "iPhone" in ua or "Android" in ua:
        return "mobile"
    if "iPad" in ua or "Tablet" in ua:
        return "tablet"
    return "desktop"
