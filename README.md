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
- 6 departamentos (inclui cenário demo)
- 20 servidores + holerite demo para `employee1`
- 16 fornecedores (inclui cenário demo)
- 13 empenhos / 11 pagamentos / 1 liquidação demo explícita
- 8 contratos
- 31 bens patrimoniais + 1 movimentação demo explícita
- 3 usuários por papel

### Cenário seeded coerente (pronto para apresentação)
- Departamento: **Secretaria Demo Integrada**
- Fornecedor: **Fornecedor Demo Integrado**
- Dotação: **BA-DEMO-001**
- Empenho: **EMP-DEMO-001** (já liquidado e pago)
- Evento de folha: **Evento Demo Integrado** (mês `2026-04`)
- Bem patrimonial: **PAT-DEMO-001** (com histórico de movimentação)

Credencial padrão: `demo123`

Usuários demo principais:
- `admin1 / demo123`
- `hr1 / demo123`
- `employee1 / demo123`
- `patrimony1 / demo123`
- `read_only1 / demo123`

## Como executar

1. Copie variáveis de ambiente:
   - `cp .env.example .env`
2. Suba a stack:
   - `docker compose up --build`
3. Acesse:
    - Frontend integrado (recomendado, via Nginx): `http://localhost`
    - Frontend direto (somente validação do serviço Next.js): `http://localhost:3000`
    - Backend direto: `http://localhost:8000`
    - API OpenAPI via Nginx: `http://localhost/api/docs`
    - API OpenAPI direto: `http://localhost:8000/docs`

> **Importante:** na stack padrão do `docker compose`, o frontend foi preparado para uso integrado via Nginx (`http://localhost`) com `NEXT_PUBLIC_API_URL=/api`.
> Se abrir o frontend direto em `http://localhost:3000`, as chamadas para `/api` não passam pelo proxy do Nginx.
> Para usar `:3000` de forma independente, ajuste `NEXT_PUBLIC_API_URL=http://localhost:8000` no frontend e mantenha CORS no backend para essa origem.

## Checklist de verificação de saúde (stack)

- [ ] Fluxo integrado via Nginx: `http://localhost`
- [ ] Frontend direto (verificação do serviço Next.js): `http://localhost:3000`
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

## Matriz de aderência ao escopo da demo (procurement-demo-ready)

| Requisito | Módulo | Tela/rota | Endpoint backend | Passos de demo | Status | Notas/limitações |
|---|---|---|---|---|---|---|
| Login por perfil | Autenticação | `/login` | `POST /auth/login` | Passo 1 de cada fluxo | **Implementado** | Logout simplificado por cookie no frontend |
| Criar departamento | Core | `/fase-2` | `POST /core/departments` | Admin passo 2 | **Implementado** | Sem edição/exclusão na UI |
| Criar fornecedor | Contábil | `/fase-2` | `POST /accounting/vendors` | Admin passo 3 | **Implementado** | Documento sem máscara automática |
| Criar dotação | Contábil | `/fase-2` | `POST /accounting/budget-allocations` | Admin passo 4 | **Implementado** | Regras orçamentárias avançadas simplificadas |
| Criar empenho | Contábil | `/fase-2` | `POST /accounting/commitments` | Admin passo 5 | **Implementado** | Sem validações fiscais avançadas |
| Liquidar empenho | Contábil | `/fase-2` | `POST /accounting/liquidate/{id}` | Admin passo 6 | **Implementado** | Operação por botão na lista |
| Registrar pagamento | Contábil | `/fase-2` | `POST /accounting/payments` | Admin passo 7 | **Implementado** | Sem integração bancária real |
| Listas com filtro/paginação + CSV | Contábil | `/fase-2` | `GET /accounting/vendors`, `GET /accounting/commitments`, `GET /accounting/payments`, `GET /accounting/reports/commitments?export=csv` | Admin passo 8 | **Implementado** | CSV em listagem-chave de empenhos |
| Transparência de empenhos/pagamentos | Público | `/public` | `GET /public/commitments`, `GET /public/payments` | Passo 9 | **Implementado** | Portal somente leitura |
| Cadastro de servidor | RH | `/rh` | `POST /hr/employees` | RH passo 2 | **Implementado** | Sem workflow de admissão completo |
| Eventos de folha | RH | `/rh` | `POST/GET /hr/payroll-events` | RH passo 3 | **Implementado** | Tipos de evento simplificados |
| Cálculo de folha | RH | `/rh` | `POST /hr/payroll/calculate` | RH passo 4 | **Implementado** | Fórmula simplificada (11% fixo) |
| Resultados de folha + PDF | RH | `/rh` | `GET /hr/payslips`, `GET /hr/payslips/{id}/pdf` | RH passo 5 | **Implementado** | PDF simples para demo |
| Portal do servidor | Servidor | `/portal-servidor` | `GET /employee-portal/me`, `GET /employee-portal/payslips`, `GET /employee-portal/income-statement` | Servidor passo 2 | **Implementado** | Sem histórico anual detalhado |
| Cadastro/transferência/baixa de bem | Patrimônio | `/patrimonio` | `POST /patrimony/assets`, `POST /patrimony/assets/{id}/transfer`, `POST /patrimony/assets/{id}/write-off` | Patrimônio passos 2–4 | **Implementado** | Sem depreciação patrimonial |
| Lista de bens + filtros/paginação + CSV | Patrimônio | `/patrimonio` | `GET /patrimony/assets`, `GET /patrimony/assets?export=csv` | Patrimônio passo 5 | **Implementado** | CSV em lista principal |
| Histórico de movimentações | Patrimônio | `/patrimonio` | `GET /patrimony/movements` | Patrimônio passo 6 | **Implementado** | Sem trilha de anexos/documentos |
| Relatório por departamento | Patrimônio | `/patrimonio` | `GET /patrimony/reports/by-department` | Patrimônio passo 7 | **Implementado** | Retorno agregado simples |
| Verificação de auditoria | Core | `/auditoria` | `GET /core/audit-logs`, `GET /core/users` | Passo final | **Implementado** | Tela simples com filtros/paginação para demonstração |
| Regras fiscais/folha/patrimônio avançadas | Domínio avançado | N/A | N/A | N/A | **Parcial** | Fora do objetivo do MVP de demonstração |
| Módulos não priorizados (compras avançadas, contratos avançados) | Escopo amplo | N/A | N/A | N/A | **Não implementado** | Não necessários para demo procurement do MVP |

## Script completo de demonstração (pt-BR, passo a passo)

### Preparação
1. Suba a stack: `docker compose up --build`.
2. Abra `http://localhost/login`.
3. Use a senha padrão `demo123` para todos os usuários demo.

### Bloco A — Login como admin + fluxo contábil
1. Login com **admin1 / demo123**.
2. No menu, abra **Contábil (Fase 2)** (`/fase-2`).
3. Em **Criar departamento**, informar:
   - Nome: `Secretaria de Compras Demo`
   - Resultado esperado: mensagem de sucesso e departamento disponível nas listas.
4. Em **Criar fornecedor**, informar:
   - Nome: `Fornecedor Apresentação`
   - Documento: `77.666.555/0001-44`
   - Resultado esperado: fornecedor aparece na lista interna.
5. Em **Criar dotação orçamentária**, informar:
   - Código: `BA-DEMO-LIVE-001`
   - Descrição: `Dotação demo ao vivo`
   - Valor: `50000`
   - Exercício: `2026`
   - Resultado esperado: mensagem de sucesso.
6. Em **Criar empenho**, informar:
   - Número: `EMP-DEMO-LIVE-001`
   - Descrição: `Empenho demo ao vivo`
   - Valor: `15000`
   - Departamento/Fornecedor: selecionar os recém-criados
   - Resultado esperado: empenho aparece na listagem.
7. Na tabela de empenhos, clicar **Liquidar** no novo empenho.
   - Resultado esperado: status muda para `liquidado`.
8. Em **Registrar pagamento**, selecionar o empenho e informar:
   - Valor: `15000`
   - Data: `2026-04-19`
   - Resultado esperado: pagamento criado e empenho com status `pago`.
9. Ainda em `/fase-2`, validar:
   - Busca de fornecedores
   - Filtro de status em empenhos
   - Paginação nas listas
   - Exportação CSV de empenhos

### Bloco B — Verificação de transparência pública
1. No menu, abrir **Transparência** (`/public`).
2. Buscar por `EMP-DEMO-LIVE-001` (ou `EMP-DEMO-001` seeded).
3. Resultado esperado:
   - Empenho visível no quadro público
   - Pagamento correspondente visível na tabela de pagamentos.

### Bloco C — Login como RH + fluxo de folha
1. Logout e login com **hr1 / demo123**.
2. No menu, abrir **RH** (`/rh`).
3. Em **Cadastrar servidor**, informar:
   - Nome: `Servidor Demo RH`
   - CPF: `123.456.789-10`
   - Cargo: `Analista de RH`
   - Tipo de vínculo: `Efetivo`
   - Salário base: `4200`
   - Departamento: `Secretaria Demo Integrada` (ou outro disponível)
   - Resultado esperado: servidor salvo com mensagem de sucesso.
4. Em **Criar evento de folha**, informar:
   - Servidor: `Servidor Demo RH`
   - Mês: `2026-04`
   - Tipo: `Provento`
   - Descrição: `Evento demo folha`
   - Valor: `500`
   - Resultado esperado: evento aparece na listagem.
5. Clicar em **Calcular folha mensal**.
   - Resultado esperado: holerites gerados e listados.
6. Na tabela de resultados, clicar **Baixar PDF** em um holerite.
   - Resultado esperado: arquivo PDF baixado.

### Bloco D — Login como servidor + portal do servidor
1. Logout e login com **employee1 / demo123**.
2. No menu, abrir **Portal Servidor** (`/portal-servidor`).
3. Validar:
   - Dados do servidor carregados
   - Demonstrativo de rendimentos exibido
   - Holerites próprios listados
   - Download de holerite PDF funcional.

### Bloco E — Login como patrimônio + fluxo patrimonial
1. Logout e login com **patrimony1 / demo123**.
2. No menu, abrir **Patrimônio** (`/patrimonio`).
3. Em **Cadastrar bem**, informar:
   - Tombamento: `PAT-DEMO-LIVE-001`
   - Descrição: `Notebook demo ao vivo`
   - Classificação: `Informática`
   - Localização: `Sala 12`
   - Departamento e responsável: selecionar opções válidas
   - Valor: `3900`
   - Resultado esperado: bem criado e listado.
4. Em **Transferir bem**, selecionar `PAT-DEMO-LIVE-001` e informar:
   - Novo departamento
   - Nova localização: `Sala 18`
   - Novo responsável (opcional)
   - Resultado esperado: transferência registrada.
5. Na lista de bens, clicar **Baixar bem** para o item recém-criado.
   - Resultado esperado: status do bem passa para `baixado`.
6. Validar:
   - Filtros e paginação da lista de bens
   - Exportação CSV da lista
   - Histórico de movimentações com o bem transferido
   - Relatório por departamento.

### Bloco F — Verificação de auditoria
1. Login com **admin1 / demo123** (ou `read_only1 / demo123`).
2. Abrir **Auditoria** (`/auditoria`).
3. Filtrar por ação, entidade e usuário conforme necessário.
4. Resultado esperado:
   - Registros de create/update para departamentos, fornecedores, empenhos, pagamentos, folha e patrimônio.

## Modo demonstração (ajuda rápida)

- **Usuários recomendados**: `admin1`, `hr1`, `employee1`, `patrimony1` (senha `demo123`).
- **Ordem recomendada de apresentação**:
  1) Contábil (`/fase-2`)
  2) Transparência (`/public`)
  3) RH (`/rh`)
  4) Portal do servidor (`/portal-servidor`)
  5) Patrimônio (`/patrimonio`)
  6) Auditoria (`/api/docs` -> `/core/audit-logs`)
- **Rotas mais rápidas**:
  - Painel: `/`
  - Contábil: `/fase-2`
  - RH: `/rh`
  - Servidor: `/portal-servidor`
  - Patrimônio: `/patrimonio`
  - Auditoria: `/auditoria`
  - Transparência: `/public`
- **Limitações conhecidas**:
  - Regras fiscais/folha/patrimônio avançadas estão simplificadas para demo.
  - Auditoria é uma visualização operacional simples (sem trilha avançada de investigação).

## Checklist final go/no-go para apresentação

- [ ] Stack iniciada com `docker compose up --build` sem erros
- [ ] Login válido para `admin1`, `hr1`, `employee1`, `patrimony1`
- [ ] Painel mostra corretamente usuário e perfil (sem “desconhecido”)
- [ ] Cenário seeded visível: `Secretaria Demo Integrada`, `Fornecedor Demo Integrado`, `BA-DEMO-001`, `EMP-DEMO-001`, `PAT-DEMO-001`, `Evento Demo Integrado`
- [ ] Contábil: criação + liquidação + pagamento + listas + CSV
- [ ] Transparência: empenho/pagamento seeded e novo registro interno visíveis
- [ ] RH/Servidor: holerite listado e download PDF funcional
- [ ] Patrimônio: movimentação e relatório visíveis
- [ ] Auditoria (`/auditoria`): eventos recentes visíveis após ações-chave

## Entidades seeded e usuários para demo rápida

- **Entidades-chave**
  - Departamento: `Secretaria Demo Integrada`
  - Fornecedor: `Fornecedor Demo Integrado`
  - Dotação: `BA-DEMO-001`
  - Empenho: `EMP-DEMO-001` (liquidado e pago)
  - Bem: `PAT-DEMO-001` (com movimentação)
  - Evento folha: `Evento Demo Integrado` (mês `2026-04`)
- **Usuários**
  - `admin1 / demo123`
  - `accountant1 / demo123`
  - `hr1 / demo123`
  - `employee1 / demo123`
  - `patrimony1 / demo123`
  - `read_only1 / demo123`

## Screenshot

- Auditoria com filtros/paginação e perfil logado (final hardening): https://github.com/user-attachments/assets/ea333c84-5bc6-407f-b672-fcf5bc148012

## Implementado vs parcial

- **Fully demo-ready**
  - Login por perfil, fluxo contábil completo, transparência pública, RH/folha, portal do servidor, patrimônio (cadastro/transferência/baixa/listas/CSV/histórico/relatório), auditoria por endpoint.
- **Partially demo-ready**
  - Regras de negócio avançadas (fiscal, folha detalhada, patrimônio com depreciação e governança documental) simplificadas para MVP.
  - Painel de auditoria sem recursos avançados de investigação (foco em demonstrabilidade).
- **Not demo-ready**
  - Módulos/rotinas avançadas fora do escopo do MVP procurement-demo (ex.: contratos e compras avançadas ponta a ponta no frontend).
