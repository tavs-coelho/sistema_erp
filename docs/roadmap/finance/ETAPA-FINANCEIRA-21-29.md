# Gestão Financeira e Contábil — execução dos PRs #21–#29

**Data-base:** 04/11/2026. **Situação:** nove PRs de planejamento em draft; nenhuma dessas nove entregas financeiras novas está concluída apenas por sua abertura.

## Ordem técnica de integração

```text
#21 Segregação financeira e plano de contas
 ├── #22 PPA e programas
 │     └── #23 LDO/LOA e dotações
 │            └── #24 Empenho → liquidação → pagamento
 │                   ├── #25 Tesouraria e conciliação
 │                   │     └── #26 Receitas e fontes
 │                   └── #27 RREO/RGF (com #25 e #26)
 │                          └── #28 SICONFI, FINBRA e XML
 └─────────────────────────────────── #29 Fechamento integrado (requer #21–#28)
```

#21 é prioritário porque os routers de orçamento, contabilidade e conciliação existentes **não utilizam `get_tenant_id` diretamente**. Antes de ampliar funções financeiras, deve haver modelo transacional de propriedade e testes negativos de IDOR. Não abrir sistema financeiro para clientes reais sem essa segregação.

| PR | Foco | Resultado mínimo esperado | Gate para aceitação |
| --- | --- | --- | --- |
| [#21](https://github.com/tavs-coelho/sistema_erp/pull/21) | Fundação e isolamento | Dados e plano de contas segregados, transações auditáveis | Tenant, RBAC, banco migrado e E2E com dois municípios |
| [#22](https://github.com/tavs-coelho/sistema_erp/pull/22) | PPA | Programas, metas, valores, revisão/aprovação | Ciclo completo com regras de vigência |
| [#23](https://github.com/tavs-coelho/sistema_erp/pull/23) | LDO/LOA | Metas e dotações vinculadas a programas e exercício | Fluxo PPA→LDO→LOA e saldos |
| [#24](https://github.com/tavs-coelho/sistema_erp/pull/24) | Despesa | Empenho, liquidação, pagamento/estorno | Integridade transacional e concorrência real |
| [#25](https://github.com/tavs-coelho/sistema_erp/pull/25) | Tesouraria | Extratos, conciliação, fechamento de contas | Importação idempotente e diferenças auditáveis |
| [#26](https://github.com/tavs-coelho/sistema_erp/pull/26) | Receita | Classificação, arrecadação, dedução e conciliação | Receita→banco→relatório sem duplicidade |
| [#27](https://github.com/tavs-coelho/sistema_erp/pull/27) | RREO/RGF | Demonstrativos com memória de cálculo | Revisão contábil/fiscal e E2E |
| [#28](https://github.com/tavs-coelho/sistema_erp/pull/28) | SICONFI | Arquivos, XSD, histórico e aprovação | Layout oficial revisado e logs, sem envio fictício |
| [#29](https://github.com/tavs-coelho/sistema_erp/pull/29) | Fechamento | Bloqueio de período, reconciliação, evidências | Jornada integrada e matriz por requisito |

## Definição de pronto por PR

É necessário: modelo SQLAlchemy/migração Alembic e atualização em PostgreSQL; isolamento multi-entidade e autorização por ação; API e interface funcional; histórico/auditoria; validação e erros; teste pytest + navegação E2E com dados fictícios; FAQ/manual; CI aprovada no head; limitações documentadas e revisão especializada para regras fiscais. Não considerar estes PRs prontos enquanto tiverem somente documentos de planejamento.

## Medição de aderência

A prova de conceito de Dois Córregos exige pelo menos 85% **de cada módulo** e 100% dos itens tecnológicos; os 2.420 requisitos funcionais e 52 tecnológicos ainda precisam ser confrontados com a matriz oficial item a item. Nenhuma taxa de cobertura pode ser inferida pela contagem de PRs, endpoints ou testes isolados.

## Controle de mudança

Todas as branches partem da `main`, para que o planejamento possa ser visto separadamente. Antes de implementar/integrar um PR dependente, atualizar a branch com a dependência já mesclada, resolver conflitos, executar CI no SHA final e validar o fluxo inteiro. **Sem merge nem deploy automático.**
