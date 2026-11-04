"""Six-module municipal core E2E smoke against ephemeral Docker Compose.

Requires the same protected DEMO-only gate as smoke_browser_erp.py. No real
personal data; exercises persisted PostgreSQL records and actual uploaded bytes.
"""
from datetime import date
import json
import os
import sys
import uuid
import urllib.error
import urllib.request

from smoke_browser_erp import BASE, CLIENT, PASSWORD, USER, call, require


def multipart_upload(path: str, filename: str, data: bytes, mime: str, csrf: str):
    boundary = "ERPNucleo" + uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    headers = {
        "Origin": BASE, "X-CSRF-Token": csrf,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    request = urllib.request.Request(BASE + path, data=body, headers=headers, method="POST")
    try:
        with CLIENT.open(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")


def main():
    if os.environ.get("ERP_SMOKE_ALLOW_DEMO") != "1":
        raise SystemExit("Allowed exclusively for disposable demo CI")
    for page in (
        "/nucleo/unidades", "/nucleo/pessoas", "/nucleo/lotacoes",
        "/nucleo/documentos", "/nucleo/tarefas", "/nucleo/central",
    ):
        status, payload = call("GET", page)
        require(status, 200, payload, f"Next.js screen {page}")
    status, payload = call("GET", "/api/auth/browser/csrf")
    require(status, 200, payload, "issue CSRF for municipal core")
    csrf = payload["csrf_token"]
    status, payload = call("POST", "/api/auth/browser/login",
                           {"username": USER, "password": PASSWORD}, csrf=csrf)
    require(status, 200, payload, "cookie-based administrator login")
    status, me = call("GET", "/api/auth/browser/me")
    require(status, 200, me, "read current user")
    user_id = me["id"]
    status, deps = call("GET", "/api/core/departments")
    require(status, 200, deps, "list departments")
    department_id = (deps["items"] if isinstance(deps, dict) else deps)[0]["id"]
    unique = uuid.uuid4().hex[:10].upper()

    status, unit = call("POST", "/api/nucleo/unidades", {
        "code": "E2E-" + unique, "name": "Unidade CI " + unique,
        "department_id": department_id, "address": "Somente demonstração",
    }, csrf=csrf)
    require(status, 201, unit, "create entity-owned municipal unit")
    status, found = call("GET", "/api/nucleo/unidades?search=" + unique)
    require(status, 200, found, "search municipal unit")
    assert any(row["id"] == unit["id"] for row in found)
    status, updated = call("PATCH", f"/api/nucleo/unidades/{unit['id']}",
                           {"name": "Unidade CI validada"}, csrf=csrf)
    require(status, 200, updated, "edit municipal unit")

    status, party = call("POST", "/api/nucleo/pessoas", {
        "kind": "fornecedor", "name": "Fornecedor fictício CI " + unique,
        "email": "empresa-ci@example.org",
    }, csrf=csrf)
    require(status, 201, party, "create municipal supplier contact")
    status, parties = call("GET", "/api/nucleo/pessoas?kind=fornecedor")
    require(status, 200, parties, "query municipal supplier contacts")
    assert any(row["id"] == party["id"] for row in parties)

    status, membership = call("POST", "/api/nucleo/lotacoes", {
        "user_id": user_id, "unit_id": unit["id"],
    }, csrf=csrf)
    require(status, 201, membership, "assign current user to unit")
    status, myunits = call("GET", "/api/nucleo/lotacoes/minhas")
    require(status, 200, myunits, "read own municipal assignments")
    assert any(row["id"] == membership["id"] for row in myunits)

    status, protocol = call("POST", "/api/protocolo/protocolos", {
        "tipo": "requerimento",
        "assunto": "Integração Núcleo CI " + unique,
        "interessado": "Pessoa fictícia",
        "data_entrada": date.today().isoformat(),
        "origem_department_id": department_id,
        "destino_department_id": department_id,
    }, csrf=csrf)
    require(status, 200, protocol, "create process for GED and task")

    status, document = call("POST", "/api/nucleo/documentos", {
        "code": "DOC-" + unique,
        "title": "Documento vinculado ao protocolo CI",
        "classification": "interno", "protocol_id": protocol["id"],
    }, csrf=csrf)
    require(status, 201, document, "register municipal document")
    binary = ("Memorando CI " + unique).encode()
    status, version = multipart_upload(
        f"/api/nucleo/documentos/{document['id']}/versions",
        "memorando.txt", binary, "text/plain", csrf,
    )
    require(status, 201, version, "upload immutable document revision")
    status, all_versions = call("GET", f"/api/nucleo/documentos/{document['id']}/versions")
    require(status, 200, all_versions, "list immutable document revisions")
    assert len(all_versions) == 1 and all_versions[0]["version"] == 1
    with CLIENT.open(BASE + f"/api/nucleo/documentos/{document['id']}/versions/{version['id']}/download",
                     timeout=15) as response:
        assert response.read() == binary
    print("PASS verified document download contents")

    status, task = call("POST", "/api/nucleo/tarefas", {
        "protocol_id": protocol["id"],
        "title": "Analisar documentos do processo CI",
        "assigned_user_id": user_id,
        "priority": "alta",
        "due_date": date.today().isoformat(),
    }, csrf=csrf)
    require(status, 201, task, "assign task to authenticated user")
    status, inbox = call("GET", "/api/nucleo/central/notificacoes")
    require(status, 200, inbox, "read assigned-task notification")
    assert any(n["kind"] == "tarefa" and n["reference_id"] == task["id"] for n in inbox)
    status, started = call("PATCH", f"/api/nucleo/tarefas/{task['id']}/status",
                           {"status": "em_andamento"}, csrf=csrf)
    require(status, 200, started, "start administrative task")
    status, finished = call("PATCH", f"/api/nucleo/tarefas/{task['id']}/status",
                            {"status": "concluida"}, csrf=csrf)
    require(status, 200, finished, "complete administrative task")

    status, ticket = call("POST", "/api/nucleo/central/tickets", {
        "subject": "Suporte teste " + unique,
        "description": "Solicitação operacional de validação automatizada em banco descartável.",
        "priority": "normal",
    }, csrf=csrf)
    require(status, 201, ticket, "open support ticket")
    status, reply = call("POST", f"/api/nucleo/central/tickets/{ticket['id']}/respostas",
                         {"message": "Resposta registrada em ambiente CI."}, csrf=csrf)
    require(status, 201, reply, "reply to support ticket")
    status, answered = call("PATCH", f"/api/nucleo/central/tickets/{ticket['id']}/status",
                            {"status": "resolvido"}, csrf=csrf)
    require(status, 200, answered, "resolve support ticket")
    status, faq = call("GET", "/api/nucleo/central/faq")
    require(status, 200, faq, "load self-service FAQ")
    assert len(faq) >= 18

    status, logout = call("POST", "/api/auth/browser/logout", csrf=csrf)
    require(status, 200, logout, "revoke cookie session")
    status, denied = call("GET", "/api/nucleo/tarefas")
    require(status, 401, denied, "forbid access after logout")
    print("PASS NUCLEO FULL STACK: 6 modules + PostgreSQL + Nginx + Next + cookies + audit")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL: municipal core end-to-end:", exc, file=sys.stderr)
        raise
