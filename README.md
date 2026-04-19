# Sistema ERP Municipal (MVP)

Monorepo de demonstração para processo licitatório, com frontend Next.js, backend FastAPI, PostgreSQL, JWT (access + refresh), RBAC, Docker Compose e Nginx.

## Estrutura

- `/apps/frontend`: Next.js + TypeScript
- `/apps/backend`: FastAPI + SQLAlchemy + Alembic
- `/infra/nginx`: proxy reverso Nginx
- `/docker-compose.yml`: stack integrada

## Perfis e autenticação

Perfis suportados:
- `admin`
- `accountant`
- `hr`
- `procurement`
- `patrimony`
- `employee`
- `read_only`

Fluxos:
- Login/logout
- Refresh token
- Rotas protegidas por papel
- Fluxo de reset de senha para demo (`/auth/request-password-reset` + `/auth/reset-password`)

## Escopo atual (vertical slices)

### ✅ Fase 1 implementada
- Usuários
- Departamentos
- Exercício fiscal
- Anexos
- Log de auditoria para C/U/D
- Login e rotas protegidas no frontend
- JWT com refresh token
- RBAC com papéis: `admin`, `accountant`, `hr`, `procurement`, `patrimony`, `employee`, `read_only`

### ✅ Fase 2 implementada (workflow demonstrável ponta a ponta)
- Login admin
- Criar departamento
- Criar fornecedor
- Criar dotação orçamentária
- Criar empenho
- Liquidar empenho
- Registrar pagamento
- Listas internas com busca/filtros/paginação
- Exportação CSV em listagem-chave
- Publicação em portal de transparência público
- Auditoria de operações C/U/D nas ações do fluxo

### ⏳ Não incluído neste recorte de entrega
- Fase 3 completa (RH/folha e portal do servidor em fluxo fim a fim de demo)
- Fase 4 completa (patrimônio em fluxo fim a fim de demo)

## Seed demo (automático no startup)

Base fictícia consistente com:
- 1 município
- 5 departamentos
- 20 servidores
- 15 fornecedores
- 12 empenhos
- 10 pagamentos
- 8 contratos
- 30 bens patrimoniais
- 3 usuários por papel

Credencial padrão: `demo123`

Exemplos:
- `admin1 / demo123`
- `accountant1 / demo123`
- `hr1 / demo123`
- `procurement1 / demo123`
- `patrimony1 / demo123`
- `employee1 / demo123`
- `read_only1 / demo123`

## Como executar

1. Copie variáveis de ambiente:
   - `cp .env.example .env`
2. Suba a stack:
   - `docker compose up --build`
3. Acesse:
   - Frontend (via Nginx): `http://localhost`
   - API OpenAPI: `http://localhost/api/docs`

## Migrações

Alembic configurado em `/apps/backend/alembic`.

No container backend, a migração roda automaticamente:
- `alembic upgrade head`

## Testes básicos

Backend:
- `cd apps/backend && pip install -r requirements.txt && pytest`

Frontend:
- `cd apps/frontend && npm ci && npm run lint && npm run build`

## Passo a passo exato da demo (Fase 2)

1. Suba a stack com `docker compose up --build`
2. Acesse `http://localhost/login`
3. Faça login com `admin1 / demo123`
4. Abra `http://localhost/fase-2`
5. Execute os formulários nesta ordem:
   - Criar departamento
   - Criar fornecedor
   - Criar dotação orçamentária
   - Criar empenho
   - Liquidar empenho (botão na lista interna)
   - Registrar pagamento
6. Valide as listas internas:
   - Fornecedores com busca/paginação
   - Empenhos com filtro por status + paginação + CSV
   - Pagamentos com paginação
7. Acesse `http://localhost/public` e confirme o empenho/pagamento exposto no portal público
8. Acesse `http://localhost/api/docs` e consulte `GET /core/audit-logs` para validar os registros de auditoria

## Screenshots (placeholder)

- [ ] Login
- [ ] Dashboard por perfil
- [ ] Transparência pública
- [ ] Folha com PDF
- [ ] Patrimônio

## Lacunas conhecidas (MVP)

- O recorte desta entrega prioriza Fase 1 + Fase 2.
- Fases 3 e 4 permanecem fora do escopo de demonstração principal desta rodada.
