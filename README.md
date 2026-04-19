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

### ✅ Fluxos validados adicionalmente neste ciclo (hardening)
- RH/Servidor via API:
  - login RH
  - cadastro de servidor
  - lançamento de evento de folha
  - cálculo de folha mensal
  - geração de holerite PDF
  - login servidor e consulta/download de próprio holerite
- Patrimônio via API:
  - login patrimônio
  - cadastro de bem com departamento/local/responsável
  - transferência de bem com atualização de local/responsável
  - histórico de movimentações
  - relatório por departamento

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
    - Frontend (direto): `http://localhost:3000`
    - Backend (direto): `http://localhost:8000`
    - API OpenAPI: `http://localhost/api/docs`

## Checklist de verificação de saúde (stack)

- [ ] Nginx: `http://localhost`
- [ ] Frontend (Next): `http://localhost:3000`
- [ ] Backend (FastAPI): `http://localhost:8000/`
- [ ] OpenAPI via Nginx: `http://localhost/api/docs`
- [ ] OpenAPI direto: `http://localhost:8000/docs`
- [ ] Login com usuários demo por perfil (senha padrão: `demo123`):
  - `admin1`
  - `accountant1`
  - `hr1`
  - `procurement1`
  - `patrimony1`
  - `employee1`
  - `read_only1`

Comandos rápidos:

```bash
curl -I http://localhost/                # rota protegida redireciona para /login
curl http://localhost:8000/              # healthcheck backend
curl -o /dev/null -w '%{http_code}\n' http://localhost/api/docs
```

## Migrações

Alembic configurado em `/apps/backend/alembic`.

No container backend, a migração roda automaticamente:
- `alembic upgrade head`

Se precisar executar manualmente:
- `docker compose exec backend alembic upgrade head`

## Testes e validações

Backend:
- `cd apps/backend && pip install -r requirements.txt && pytest tests/test_auth.py`
  - cobre: login sucesso/falha, RBAC, ciclo empenho→liquidação→pagamento, folha+holerite, patrimônio+movimentação

Frontend:
- `cd apps/frontend && npm ci && npm run lint && npm run build`
  - smoke de navegação:
    - login (`/login`)
    - redirect de rota protegida (`/` sem cookie => `/login`)
    - render de listas públicas (`/public`)

## Script exato de demo (validado)

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

### Demo rápida RH/Servidor (API)
1. Login `hr1 / demo123` em `POST /auth/login`
2. Criar servidor em `POST /hr/employees`
3. Criar evento em `POST /hr/payroll-events`
4. Calcular folha em `POST /hr/payroll/calculate`
5. Login `employee1 / demo123` e consultar `GET /employee-portal/payslips`
6. Baixar holerite em `GET /hr/payslips/{id}/pdf`

### Demo rápida Patrimônio (API)
1. Login `patrimony1 / demo123`
2. Criar bem em `POST /patrimony/assets`
3. Transferir em `POST /patrimony/assets/{id}/transfer`
4. Conferir histórico em `GET /patrimony/movements`
5. Conferir relatório em `GET /patrimony/reports/by-department`

## Screenshot

- Fluxo validado: https://github.com/user-attachments/assets/c2ae2c1c-da9f-4322-9b13-9149c3c3e6c0

## Implementado vs parcial

- **Implementado e validado ponta a ponta no frontend**: Fase 1 + Fase 2.
- **Implementado e validado via API (sem tela dedicada de fluxo completo)**: RH/Servidor e Patrimônio.
- Regras avançadas de domínio (fiscal/folha/patrimonial) seguem simplificadas para demo.
