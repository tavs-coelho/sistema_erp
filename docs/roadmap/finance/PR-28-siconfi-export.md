# PR financeiro 28 — SICONFI, FINBRA, XML e prestação de contas

**Status inicial: escopo de execução planejado; NÃO desenvolvido nem testado.**

## Objetivo
Prestação de contas auditável: geração de FINBRA/RREO/RGF, XML validado contra especificação oficial versionada, relatórios de erros, histórico e aprovação.

## Entrega abrangente prevista
Evoluir routers `siconfi_siop.py` e `siconfi_xml.py`, validação XSD conforme leiaute homologado, armazenamento de artefatos com hash, versionamento, assinatura/revisão e download seguro. Transmissão externa só se autorizada e homologada; nunca simular envio.

## Critérios verificáveis de aceite
Cenários XML válido/inválido, validação por período/entidade, prevenção de IDOR em downloads, logs e E2E gerar → revisar → exportar.

Além disso, o PR deve incluir interface Next.js funcional, API FastAPI, migrações Alembic para novas estruturas, segregação por tenant, RBAC, trilha de auditoria sem segredos, manual/FAQ e CI verde na SHA revisada. É necessário cadastrar cada requisito da matriz do edital com ID, tela, API, teste e evidência.

## Dependências
#27. A branch é independente para planejar, mas o trabalho de implementação deverá incorporar as dependências antes da integração.

## Riscos
Os routers contábeis existentes não provam conformidade fiscal, transmissão oficial nem segurança multi-entidade integral. Não usar dados reais na CI. Exigir revisão de especialista, homologação em PostgreSQL e evidências antes de chamar de pronto. Não mesclar/deploy automaticamente.
