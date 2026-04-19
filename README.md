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

## Módulos implementados

### Núcleo compartilhado
- Usuários
- Departamentos
- Exercício fiscal
- Anexos
- Log de auditoria para C/U/D
- Dashboard inicial

### Contábil
- Fornecedores/credores
- Empenhos, liquidação, pagamentos
- Lançamento de receita
- Relatório de empenhos com exportação CSV
- Dashboard de totais

### Compras e contratos
- Processos licitatórios
- Homologação simplificada
- Contratos e aditivos
- Consulta de contratos a vencer

### Transparência pública
- Endpoints sem login
- Listagens paginadas de empenhos, pagamentos, contratos e fornecedores
- Busca/filtro básico
- Exportação CSV

### RH/Folha
- Cadastro de servidores
- Cálculo simplificado da folha mensal
- Holerite em PDF
- Relatório por departamento

### Portal do servidor
- Perfil
- Consulta de holerites
- Informe de rendimentos demo
- Alteração de senha

### Patrimônio
- Cadastro de bens
- Transferência entre departamentos
- Baixa
- Inventário
- Histórico de movimentações

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

## Walkthrough sugerido da demo

1. Login como `admin1`
2. Visualizar dashboard inicial
3. Abrir transparência pública e exportar CSV de empenhos
4. Validar rota de contratos/compras via OpenAPI
5. Executar cálculo de folha e gerar PDF de holerite
6. Consultar inventário e movimentação patrimonial
7. Visualizar auditoria de alterações C/U/D

## Screenshots (placeholder)

- [ ] Login
- [ ] Dashboard por perfil
- [ ] Transparência pública
- [ ] Folha com PDF
- [ ] Patrimônio

## Lacunas conhecidas (MVP)

- UI ainda focada em demonstração (fluxos principais) e não em cobertura completa de formulários de todos os módulos.
- Relatórios avançados e regras profundas de domínio foram simplificados para priorizar fluxo fim a fim demonstrável.
