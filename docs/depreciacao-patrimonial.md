# Depreciação Patrimonial — Documentação Técnica (NBCASP / IPSAS 17)

## Objetivo

Implementar o cálculo de depreciação patrimonial conforme a NBC T 16.9 (NBCASP) e IPSAS 17, aproveitando o módulo de patrimônio existente (`Asset`, `AssetMovement`). O módulo mantém o valor contábil líquido de cada bem, gera lançamentos mensais históricos e fornece visão consolidada por período.

---

## Modelos de dados

### `ConfiguracaoDepreciacao` (tabela `configuracoes_depreciacao`)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int PK | |
| `asset_id` | FK assets (unique) | Vincula ao bem patrimonial existente |
| `data_aquisicao` | date | Data de incorporação ao patrimônio |
| `valor_aquisicao` | float | Custo histórico (imutável após configurado) |
| `vida_util_meses` | int | Prazo total de depreciação em meses |
| `valor_residual` | float | Valor mínimo (bem não deprecia abaixo deste) |
| `metodo` | str | `linear` \| `saldo_decrescente` |
| `ativo` | bool | `False` = bem baixado ou isento de depreciação |

> **Nota**: O campo `Asset.value` **não** é alterado pelo módulo de depreciação, para manter compatibilidade com os módulos de patrimônio existentes. O valor contábil líquido está em `LancamentoDepreciacao.valor_contabil_liquido`.

### `LancamentoDepreciacao` (tabela `lancamentos_depreciacao`)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int PK | |
| `asset_id` | FK assets | |
| `periodo` | str(7) | `YYYY-MM` |
| `valor_depreciado` | float | Quota de depreciação do mês |
| `depreciacao_acumulada` | float | Soma de todas as quotas até este período |
| `valor_contabil_liquido` | float | `valor_aquisicao − depreciacao_acumulada` |
| `criado_por_id` | FK users (nullable) | Usuário que acionou o cálculo |
| `created_at` | datetime | |

---

## Prazos de referência NBCASP (NBC T 16.9 / art. 3º)

| Classe de bem | Vida útil padrão | Residual sugerido |
|---|---|---|
| Imóveis | 300 meses (25 anos) | 20% |
| Máquinas e equipamentos | 120 meses (10 anos) | 10% |
| Móveis e utensílios | 120 meses (10 anos) | 10% |
| Veículos | 60 meses (5 anos) | 10% |
| Equipamentos de TI | 60 meses (5 anos) | 5% |
| Obras de arte / bens culturais | Não depreciam | — |

---

## Lógica de cálculo

### Método Linear (padrão NBCASP)

```
quota_mensal  = (valor_aquisicao − valor_residual) / vida_util_meses
(constante para todos os meses)
```

A quota é aplicada até que `valor_contabil_liquido ≤ valor_residual`.

### Método Saldo Decrescente (acelerado)

```
taxa_mensal   = 2 / vida_util_meses
quota_mes_n   = valor_contabil_liquido_anterior × taxa_mensal
```

A quota decresce mês a mês. Para quando `valor_contabil_liquido ≤ valor_residual`.

### Invariante verificado nos testes

```
valor_contabil_liquido = valor_aquisicao − depreciacao_acumulada
depreciacao_acumulada  = Σ valor_depreciado (todos os períodos até agora)
valor_contabil_liquido ≥ valor_residual (nunca ultrapassa o piso)
```

---

## Endpoints

### Configuração (`/depreciacao/config`)

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| POST | `/depreciacao/config` | Cria configuração de depreciação para um bem | admin, patrimony |
| GET | `/depreciacao/config/{asset_id}` | Retorna configuração do bem | autenticado |
| GET | `/depreciacao/config` | Lista todas as configurações (paginado) | autenticado |
| PATCH | `/depreciacao/config/{asset_id}` | Atualiza parâmetros | admin, patrimony |

### Cálculo e Lançamentos (`/depreciacao`)

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| POST | `/depreciacao/calcular` | Calcula e persiste lançamentos para `periodo` (YYYY-MM). Idempotente. Suporta bem específico ou todos | admin, patrimony |
| GET | `/depreciacao/lancamentos` | Lista lançamentos com filtros: `asset_id`, `periodo` | autenticado |

### Relatório por bem

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| GET | `/depreciacao/relatorio/{asset_id}` | Histórico completo de depreciação do bem (JSON) | autenticado |
| GET | `/depreciacao/relatorio/{asset_id}/csv` | Export CSV do histórico | admin, patrimony, read_only |

### Dashboard

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| GET | `/depreciacao/dashboard?periodo=YYYY-MM` | KPIs consolidados | admin, patrimony, read_only |

KPIs retornados:
- `total_bens_configurados`
- `total_bens_com_lancamento`
- `total_depreciado_periodo`
- `total_depreciacao_acumulada`
- `total_valor_contabil_liquido`
- `total_valor_aquisicao`
- `top_bens` (top 10 por valor depreciado no período)

---

## Exportação CSV do relatório

Campos: `tombamento, descricao, valor_aquisicao, metodo, periodo, valor_depreciado, depreciacao_acumulada, valor_contabil_liquido`

---

## Idempotência

`POST /depreciacao/calcular` é idempotente por `(asset_id, periodo)`:
- Se já existe lançamento para o par: recalcula e atualiza (`atualizados++`)
- Se não existe: cria novo lançamento (`criados++`)
- Isso permite re-execução segura após correção de parâmetros

---

## Seed de demonstração

| Item | Descrição |
|---|---|
| 6 configurações | Uma por bem ativo (até 6), alternando método linear/saldo decrescente, classe e vida útil variada |
| 12 meses de lançamentos | Gerados retroativamente para cada bem configurado |
| Variação de prazos | Veículos (60m), Máquinas (120m), Imóveis (300m), etc. |

---

## Premissas e limitações

| # | Premissa / Limitação |
|---|---|
| 1 | **`Asset.value` inalterado**: o módulo não atualiza `Asset.value` para o VCL. Para exibir o valor contábil líquido atualizado no inventário, precisa-se de consulta ao último `LancamentoDepreciacao` do bem. |
| 2 | **Sem reavaliação (revalorização)**: o módulo não suporta reavaliação patrimonial (aumento do valor por avaliação técnica), prevista na IPSAS 17. |
| 3 | **Sem redução ao valor recuperável (impairment)**: NBC T 16.10 exige teste de impairment; não implementado. |
| 4 | **Feriados / Pro-rata**: a quota é calculada mensalmente sem pro-rata por aquisição no meio do mês. Para conformidade estrita, o primeiro mês deveria ser proporcional aos dias de uso. |
| 5 | **Sem contabilização em partidas dobradas**: o módulo gera o lançamento de controle patrimonial, mas não cria automaticamente débito em "Depreciação Acumulada" e crédito em "Resultado do Exercício" no módulo de contabilidade. Essa integração precisaria ser desenvolvida separadamente. |
| 6 | **Sem reversão automática**: baixar um bem (`Asset.status = "baixado"`) não cancela retroativamente os lançamentos anteriores nem impede futuros cálculos. O campo `ConfiguracaoDepreciacao.ativo` deve ser setado como `False` manualmente via PATCH. |
| 7 | **Escopo de classes**: não há tabela de "classes de bens" com parâmetros NBCASP pré-definidos. Os prazos do NBC T 16.9 são documentados como referência, mas precisam ser inseridos manualmente em cada configuração. |

---

## Próximas evoluções sugeridas

1. **Tabela de classes patrimoniais NBCASP** — parâmetros pré-definidos por categoria para facilitar cadastro em massa
2. **Pro-rata na aquisição** — quota proporcional no primeiro mês
3. **Integração contábil** — geração automática de lançamentos em partidas dobradas ao registrar depreciação
4. **Impairment (NBC T 16.10)** — teste de redução ao valor recuperável
5. **Reavaliação patrimonial** — suporte a aumento de valor por avaliação técnica pericial
6. **Relatório NBCASP de patrimônio** — quadro de variação do ativo imobilizado no balanço patrimonial
