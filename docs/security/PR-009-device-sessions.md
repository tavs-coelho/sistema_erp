# PR #9 — sessões por dispositivo e rotação de refresh tokens

Escopo: segurança do ERP Público, com base na `main` que incorporou MFA no PR #8. Referência de trabalho: Issue #5. Este documento **não** afirma conformidade com o Pregão nº 66/2026 de Dois Córregos/SP.

## Alterações efetivas
- `app/models.py`: `UserSession` registra identificador opaco por dispositivo, `user_id`, `tenant_id`, versão global, hash SHA-256 do refresh token atual, user-agent truncado, criação/uso/expiração e revogação.
- `alembic/versions/0020_device_sessions.py`: migração incremental que cria a tabela e índices, dependente de `0019_user_mfa_sessions`.
- `app/session_service.py`: login cria uma sessão persistente; refresh renova credencial com `jti` aleatório, substitui seu hash e usa bloqueio transacional `SELECT ... FOR UPDATE` no PostgreSQL; reapresentar refresh antigo revoga **somente** aquela sessão.
- `app/deps.py`: access token com `sid` só é aceito se a sessão estiver ativa, íntegra, vinculada ao usuário/entidade e não expirada.
- `app/routers/auth.py`: `POST /auth/logout` encerra somente o dispositivo atual; `POST /auth/logout-all` revoga todas as sessões; `GET /auth/sessions` lista até 50 sessões ativas; `DELETE /auth/sessions/{id}` só encerra sessões do usuário na entidade solicitante; reset de senha e alterações de MFA encerram todas.
- `apps/frontend/src/components/device-sessions.tsx`: visualização de dispositivos, última atividade, sessão atual, encerramento individual e global.
- `apps/frontend/src/components/header-nav.tsx`: saída integrada à revogação no backend.

## Semântica e compatibilidade
- Os tokens de acesso e refresh novos contêm `sid`; refresh também recebe identificador aleatório `jti`.
- O backend **não persiste refresh tokens em texto puro**, apenas o hash do token atual. O frontend existente não implementa renovação automática nem sessão por cookie HttpOnly nesta etapa.
- Refresh antigo sem `sid` é aceito **somente em DEMO_MODE=true** por compatibilidade com testes/contas de demonstração. Fora do modo demo, exige novo login e sessão rastreada. Tokens de acesso antigos sem `sid` também são rejeitados fora de demo.
- Logout individual não afeta outros dispositivos; logout global, reset de senha e mudanças de MFA revogam todos.
- A identificação de dispositivo usa User-Agent não autenticado, portanto é **informativa**, não prova criptográfica de um aparelho.

## Verificação a realizar
- `tests/test_device_sessions.py`: login em dispositivos distintos, hash sem token bruto, rotação, replay, expulsão individual/global, isolamento multi-entidade, expiração, revogação após reset e rejeição de tokens legados em produção.
- `tests/test_device_session_migration.py`: smoke-test de upgrade/downgrade SQLite da migração 0020.
- GitHub Actions: job de segurança, suite de backend, lint/build Next.js e sintaxe Compose.
- Registrar resultado e SHA do workflow antes de alterar o status dos requisitos.

## Pendências e riscos residuais
1. Refresh automático em frontend exige uma implementação com cookies HttpOnly + proteção CSRF. Armazenar refresh token em `localStorage` não é aceitável como solução final.
2. Tokens bearer de acesso atuais continuam armazenados em `localStorage`; priorizar BFF/servidor com cookies HttpOnly e CSP.
3. Revogação por reutilização intencional de refresh pode desconectar um dispositivo em condição de corrida de requisições simultâneas; implementar fila/serialização de refresh no cliente e avaliar tolerância controlada.
4. Limite de sessões simultâneas, política de limpeza/retention e observabilidade ainda pendentes.
5. Teste transacional real e validação de cadeia inteira de Alembic em PostgreSQL ainda são necessários. A migração histórica inicial emprega `Base.metadata.create_all()` e pode colidir com migrações subsequentes.
6. Revisar proxy e validação de cabeçalho Host. Isolamento de dados ainda não cobre todos os 21 módulos; testes atuais provam apenas escopos delimitados.
7. Não mapear itens tecnológicos do TR como demonstráveis sem a matriz oficial e evidências de teste.
