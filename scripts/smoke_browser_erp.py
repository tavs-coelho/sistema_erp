"""End-to-end smoke against running Nginx + Next.js + FastAPI + PostgreSQL.

Only run against isolated DEMO_MODE=true test deployment. Creates a synthetic
administrative protocol and validates a complete authenticated workflow.
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import time
import uuid
import urllib.error
import urllib.request


BASE = os.environ.get("ERP_SMOKE_URL", "http://localhost").rstrip("/")
USER = os.environ.get("ERP_SMOKE_USER", "admin2")
PASSWORD = os.environ.get("ERP_SMOKE_PASSWORD", "demo123")
COOKIES = http.cookiejar.CookieJar()
CLIENT = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIES))


def call(method: str, path: str, body: dict | None = None, csrf: str = ""):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if method not in ("GET", "HEAD"):
        headers["Origin"] = BASE
        if csrf:
            headers["X-CSRF-Token"] = csrf
    request = urllib.request.Request(
        BASE + path, data=data, headers=headers, method=method
    )
    try:
        with CLIENT.open(request, timeout=15) as response:
            payload = response.read()
            try:
                parsed = json.loads(payload)
            except (ValueError, UnicodeDecodeError):
                parsed = payload.decode("utf-8", errors="replace")
            return response.status, parsed
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            parsed = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            parsed = raw.decode("utf-8", errors="replace")
        return error.code, parsed


def require(status: int, expected: int, result, description: str):
    if status != expected:
        raise AssertionError(f"{description}: HTTP {status}, expected {expected}: {str(result)[:400]}")
    print("PASS", description)


def main():
    if not os.environ.get("ERP_SMOKE_ALLOW_DEMO"):
        raise SystemExit("Set ERP_SMOKE_ALLOW_DEMO=1 only for disposable demo CI")
    # Verify both frontend and API routing through a real reverse proxy.
    for _ in range(80):
        try:
            status, result = call("GET", "/api/")
            if status == 200:
                break
        except (OSError, TimeoutError):
            pass
        time.sleep(3)
    else:
        raise AssertionError("ERP did not become healthy via Nginx /api/")
    require(status, 200, result, "backend health via Nginx")
    status, page = call("GET", "/login")
    require(status, 200, page, "Next.js login page")
    assert isinstance(page, str) and ("login" in page.lower() or "acesso" in page.lower())

    status, data = call("GET", "/api/auth/browser/csrf")
    require(status, 200, data, "issue browser CSRF")
    csrf = data["csrf_token"]
    assert any(cookie.name == "erp_csrf" for cookie in COOKIES)

    credentials = {"username": USER, "password": PASSWORD}
    status, data = call("POST", "/api/auth/browser/login", credentials)
    require(status, 403, data, "reject login without CSRF")
    status, data = call("POST", "/api/auth/browser/login", credentials, csrf=csrf)
    require(status, 200, data, "login with cookie session")
    assert "access_token" not in data and "refresh_token" not in data
    cookie_map = {cookie.name: cookie for cookie in COOKIES}
    assert "erp_access" in cookie_map and cookie_map["erp_access"].has_nonstandard_attr("HttpOnly")
    assert "erp_refresh" in cookie_map and cookie_map["erp_refresh"].has_nonstandard_attr("HttpOnly")
    status, data = call("GET", "/api/auth/browser/me")
    require(status, 200, data, "read authenticated user")
    status, data = call("GET", "/api/core/departments")
    require(status, 200, data, "list municipal departments")
    departments = data["items"] if isinstance(data, dict) and "items" in data else data
    assert len(departments) > 0
    department_id = departments[0]["id"]

    status, data = call("GET", "/api/protocolo/protocolos?page=1&size=5")
    require(status, 200, data, "list existing administrative protocols")
    protocol = {
        "tipo": "requerimento",
        "assunto": "Validação de fluxo completo da implantação",
        "interessado": "Solicitante de teste automatizado",
        "data_entrada": "2026-11-03",
        "origem_department_id": department_id,
        "destino_department_id": department_id,
        "prioridade": "normal",
    }
    status, data = call("POST", "/api/protocolo/protocolos", protocol, csrf=csrf)
    require(status, 200, data, "create administrative protocol")
    protocol_id = data["id"]
    assert data["numero"].startswith("PROT-2026-")

    status, data = call(
        "POST", f"/api/protocolo/protocolos/{protocol_id}/tramitar",
        {"para_department_id": department_id, "acao": "encaminhado", "despacho": "Encaminhado pela CI"},
        csrf=csrf,
    )
    require(status, 200, data, "process administrative protocol")
    status, data = call("GET", f"/api/protocolo/protocolos/{protocol_id}")
    require(status, 200, data, "read administrative protocol")
    assert data["status"] == "em_tramitacao"

    status, data = call("POST", "/api/auth/browser/refresh", csrf=csrf)
    require(status, 200, data, "rotate HttpOnly refresh session")
    status, data = call("POST", "/api/auth/browser/logout", csrf=csrf)
    require(status, 200, data, "revoke current browser session")
    status, data = call("GET", "/api/auth/browser/me")
    require(status, 401, data, "block revoked session")
    print("E2E ERP PASS: Nginx, Next.js, FastAPI, PostgreSQL, cookies, CSRF, protocolo and logout")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("E2E ERP FAILED:", str(exc), file=sys.stderr)
        raise
