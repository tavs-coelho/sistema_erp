# Planejamento do PR de execução financeira 24

**Título:** Empenho, liquidação, pagamento e estorno

**Estado inicial:** escopo técnico registrado, implementação funcional e testes ainda pendentes. A criação deste documento **não** demonstra atendimento a requisito do edital.

## Objetivo
Execução orçamentária utilizável de dotação a pagamento, com saldos e trilha.

## Implementação contratada para este PR
Controle transacional de saldo; empenho/estorno; liquidação parcial, pagamento e documentação; UI com fornecedor e contrato.

## Critérios mínimos de aceite
E2E empenho→liquidação→pagamento; concorrência PostgreSQL; saldo não negativo, IDOR e RBAC.

Além disso, antes de considerar pronto: código com migração Alembic reversível/ensaiada, segregação por tenant, RBAC, trilha de auditoria, interface Next.js funcional, testes pytest e E2E executados em PostgreSQL, documentação e FAQ. Proibir acesso aos recursos de outros municípios; validar integridade e concorrência de transações financeiras.

## Base técnica existente
O repositório já contém routers FastAPI de budget, accounting, conciliacao, rreo_rgf, siconfi_siop e siconfi_xml, e modelos financeiros. **Não recriar módulos do zero**; auditar lacunas e completar fluxos, migrando dados existentes sem apagá-los. Números e formatos oficiais devem ser validados contra especificações vigentes; não assumir conformidade legal por haver um endpoint.

## Dependências e integração
Requer implementação e merge validado de #21, #23. Branch parte de main apenas para planejamento independente; deve ser atualizada/rebaseada depois das dependências.

## Evidências e status exigidos
- Requisitos do TR com identificador, módulo, tela, API, teste e execução: **a mapear**.
- Testes E2E do fluxo completo: **não executados neste scaffold**.
- Migração PostgreSQL e testes de concorrência: **não executados neste scaffold**.
- Revisão de regras contábeis por especialista: **pendente**.
- O PR só deve sair de draft após implementação integral, CI verde e revisão.

## Riscos
Segregação multi-entidade não está completa nos routers de budget/accounting/conciliacao; não inserir dados reais, não expor volumes ou senhas, não anunciar aderência POC de Dois Córregos sem prova item a item. Evitar alterações genéricas de schema sem testar migração de bases existentes. Nenhum deploy ou merge automático.
