import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

_SECURITY_HEADERS = [
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
]


async def test_security_headers_present(client: AsyncClient):
    r = await client.get("/livez")
    for header in _SECURITY_HEADERS:
        assert header in r.headers, f"missing security header: {header}"


async def test_security_header_values(client: AsyncClient):
    r = await client.get("/livez")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


async def test_cors_unlisted_origin_blocked(client: AsyncClient):
    r = await client.get("/livez", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in r.headers


async def test_trace_id_absent_when_otel_disabled(client: AsyncClient, caplog):
    # with OTEL_ENABLED=false (test env default), no active span exists
    # LoggerMiddleware sets trace_id=None when no span is active
    import logging

    with caplog.at_level(logging.INFO, logger="fastauth.access"):
        await client.get("/livez")

    if caplog.records:
        record = caplog.records[-1]
        trace_id = getattr(record, "trace_id", None)
        assert trace_id is None or trace_id == "0" * 32
