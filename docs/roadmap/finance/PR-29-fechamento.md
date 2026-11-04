# PR financeiro 29 — Fechamento contábil e evidências integradas

**Status inicial: escopo de execução planejado; NÃO desenvolvido nem testado.**

## Objetivo
Fechamento mensal/anual completo: conciliação de saldos entre orçamento, receita, despesa, tesouraria e demonstrações fiscais, com evidências de homologação.

## Entrega abrangente prevista
Checklist por competência/entidade, reconciliação de totais, bloqueio de períodos fechados, reabertura auditada, relatório de inconsistências, exportações, manual/FAQ e matriz de requisitos do edital.

## Critérios verificáveis de aceite
Ciclo E2E PPA→LDO→LOA→empenho→liquidação→pagamento→tesouraria→RREO/RGF→prestação; testes PostgreSQL, IDOR, RBAC, backup/restauração e números de referência.

Além disso, o PR deve incluir interface Next.js funcional, API FastAPI, migrações Alembic para novas estruturas, segregação por tenant, RBAC, trilha de auditoria sem segredos, manual/FAQ e CI verde na SHA revisada. É necessário cadastrar cada requisito da matriz do edital com ID, tela, API, teste e evidência.

## Dependências
#21–#28. A branch é independente para planejar, mas o trabalho de implementação deverá incorporar as dependências antes da integração.

## Riscos
Os routers contábeis existentes não provam conformidade fiscal, transmissão oficial nem segurança multi-entidade integral. Não usar dados reais na CI. Exigir revisão de especialista, homologação em PostgreSQL e evidências antes de chamar de pronto. Não mesclar/deploy automaticamente.
