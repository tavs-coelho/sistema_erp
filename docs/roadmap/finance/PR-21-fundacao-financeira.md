# Planejamento do PR de execução financeira 21

**Título:** Segregação contábil e modelo de contas

**Estado inicial:** escopo técnico registrado, implementação funcional e testes ainda pendentes. A criação deste documento **não** demonstra atendimento a requisito do edital.

## Objetivo
Isolamento de entidades e ownership de fornecedor, orçamento, fonte, empenho, liquidação, pagamento, receita, contas e lançamentos.

## Implementação contratada para este PR
Migrations de tenant_id com backfill auditado; plano de contas parametrizado; filtros/IDOR em APIs, exportações e dashboards; RBAC contábil.

## Critérios mínimos de aceite
Dois municípios com dados homônimos sem vazamento; violação de FK cruzada bloqueada; PostgreSQL upgrade e testes E2E; auditoria de movimentação.

Além disso, antes de considerar pronto: código com migração Alembic reversível/ensaiada, segregação por tenant, RBAC, trilha de auditoria, interface Next.js funcional, testes pytest e E2E executados em PostgreSQL, documentação e FAQ. Proibir acesso aos recursos de outros municípios; validar integridade e concorrência de transações financeiras.

## Base técnica existente
O repositório já contém routers FastAPI de budget, accounting, conciliacao, rreo_rgf, siconfi_siop e siconfi_xml, e modelos financeiros. **Não recriar módulos do zero**; auditar lacunas e completar fluxos, migrando dados existentes sem apagá-los. Números e formatos oficiais devem ser validados contra especificações vigentes; não assumir conformidade legal por haver um endpoint.

## Dependências e integração
Primeiro PR da etapa; prioridade de segurança e fundação.

## Evidências e status exigidos
- Requisitos do TR com identificador, módulo, tela, API, teste e execução: **a mapear**.
- Testes E2E do fluxo completo: **não executados neste scaffold**.
- Migração PostgreSQL e testes de concorrência: **não executados neste scaffold**.
- Revisão de regras contábeis por especialista: **pendente**.
- O PR só deve sair de draft após implementação integral, CI verde e revisão.

## Riscos
Segregação multi-entidade não está completa nos routers de budget/accounting/conciliacao; não inserir dados reais, não expor volumes ou senhas, não anunciar aderência POC de Dois Córregos sem prova item a item. Evitar alterações genéricas de schema sem testar migração de bases existentes. Nenhum deploy ou merge automático.
