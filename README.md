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

### ✅ Fase 3A demonstrável no frontend (RH + portal do servidor)
- RH via UI (`/rh`):
  - login RH
  - cadastro de servidor
  - lançamento de evento de folha
  - cálculo de folha mensal
  - listagem de resultados de folha (holerites) com download de PDF
- Portal do servidor via UI (`/portal-servidor`):
  - login servidor
  - acesso ao portal do servidor
  - visualização de holerites próprios
  - download do próprio holerite
  - demonstrativo de rendimentos (demo)

### ✅ Fase 3B demonstrável no frontend (Patrimônio)
- Patrimônio via UI (`/patrimonio`):
  - login patrimônio
  - cadastro de bem com departamento/local/responsável
  - classificação do bem
  - transferência de bem com atualização de local/responsável
  - baixa de bem
  - listagem com filtros/paginação
  - exportação CSV da listagem de bens
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

### Demo UI completa RH/Servidor
1. Faça login com `hr1 / demo123`
2. Abra `http://localhost/rh`
3. Execute o fluxo:
   - Cadastrar servidor
   - Criar evento de folha
   - Clicar em **Calcular folha mensal**
   - Validar listas de servidores/eventos/holerites (filtros + paginação)
   - Baixar PDF de holerite na tabela de resultados
4. Faça logout e login com `employee1 / demo123`
5. Abra `http://localhost/portal-servidor`
6. Valide:
   - dados do servidor
   - demonstrativo de rendimentos
   - lista de holerites próprios
   - download do próprio holerite PDF

### Demo UI completa Patrimônio
1. Faça login com `patrimony1 / demo123`
2. Abra `http://localhost/patrimonio`
3. Execute o fluxo:
   - Cadastrar bem com classificação/departamento/local/responsável
   - Transferir bem (departamento/local/responsável)
   - Baixar bem
   - Validar listagem com filtros + paginação
   - Exportar CSV da listagem de bens
   - Conferir histórico de movimentações
   - Gerar relatório por departamento

## Screenshot

- RH/folha (UI demonstrável): https://github.com/user-attachments/assets/600fcae7-e8c6-478a-8a85-7e3512bd24ad

## Implementado vs parcial

- **Implementado e validado ponta a ponta no frontend**: Fase 1 + Fase 2 + Fase 3A (RH/portal servidor) + Fase 3B (patrimônio).
- **Parcial**: regras de negócio avançadas seguem simplificadas para demonstração.
