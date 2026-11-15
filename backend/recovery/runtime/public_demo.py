"""Anonymous demo sessions: opaque cookies, per-visitor runs, no forwarded identity trust."""
from __future__ import annotations
import re
import secrets
from http.cookies import SimpleCookie
from urllib.parse import parse_qs
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from .context import visitor_id


class PublicDemoSession:
    def __init__(self, app, service_provider):
        self.app, self.service_provider = app, service_provider

    async def __call__(self, scope, receive, send):
        from ..config import settings
        if not settings.public_demo or scope["type"] != "http" or not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        origin = headers.get(b"origin", b"").decode()
        host = headers.get(b"host", b"").decode()
        if scope["method"] not in ("GET", "HEAD", "OPTIONS") and (
            (origin and origin not in (f"https://{host}", f"http://{host}")) or headers.get(b"sec-fetch-site") == b"cross-site"
        ):
            return await JSONResponse({"code":"ORIGIN_REJECTED","message":"Use this application's own origin."}, status_code=403)(scope, receive, send)
        cookies = SimpleCookie()
        try:
            cookies.load(headers.get(b"cookie", b"").decode())
            cookie = cookies.get("resource_visitor")
            identity = cookie.value if cookie else ""
        except Exception:
            identity = ""
        fresh = not re.fullmatch(r"[a-f0-9]{64}", identity)
        if fresh:
            identity = secrets.token_hex(32)
        token = visitor_id.set(identity)
        async def session_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [(b"cache-control", b"private, no-store")]
                if fresh:
                    secure = "; Secure" if settings.serverless or scope.get("scheme") == "https" else ""
                    value = f"resource_visitor={identity}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400{secure}"
                    message["headers"].append((b"set-cookie", value.encode()))
            await send(message)
        try:
            s = await run_in_threadpool(self.service_provider)
            path = scope["path"]
            query = parse_qs(scope.get("query_string", b"").decode())
            run_id = (query.get("run_id") or [None])[0]
            match = re.match(r"/api/v1/scenario-runs/([^/]+)", path)
            if match and match[1] != "current":
                run_id = match[1]
            if run_id and await run_in_threadpool(s.store.kv_get, f"run_owner:{run_id}") != identity:
                return await JSONResponse({"code":"NOT_FOUND","message":"Run not found."}, status_code=404)(scope, receive, session_send)
            await self.app(scope, receive, session_send)
        finally:
            visitor_id.reset(token)
