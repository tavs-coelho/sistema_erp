# Conciliação Bancária

## Visão Geral

O módulo de **Conciliação Bancária** fecha o ciclo financeiro do ERP municipal, cruzando os
lançamentos do extrato bancário com os pagamentos e receitas registrados no sistema.

| Entidade | Tabela | Descrição |
|---|---|---|
| `ContaBancaria` | `contas_bancarias` | Conta corrente/poupança/aplicação da entidade |
| `LancamentoBancario` | `lancamentos_bancarios` | Linha do extrato bancário (crédito ou débito) |

---

## Endpoints

Todas as rotas exigem autenticação JWT. CRUD de contas e lançamentos requer role
`admin` ou `accountant`. Leitura (GET) está disponível para todos os perfis autenticados.

### Contas Bancárias

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/banco/contas` | Lista contas (filtro: `ativa`) |
| `POST` | `/banco/contas` | Cria conta |
| `GET` | `/banco/contas/{id}` | Detalhes de uma conta |
| `PATCH` | `/banco/contas/{id}` | Atualiza descrição ou situação |

### Lançamentos Bancários

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/banco/lancamentos` | Lista lançamentos (filtros: `conta_id`, `status`, `tipo`, `data_inicio`, `data_fim`) |
| `POST` | `/banco/lancamentos` | Cadastra lançamento manual |
| `DELETE` | `/banco/lancamentos/{id}` | Remove lançamento |
| `PATCH` | `/banco/lancamentos/{id}/ignorar` | Marca como ignorado |
| `PATCH` | `/banco/lancamentos/{id}/conciliar-manual` | Conciliação manual via `payment_id` ou `revenue_entry_id` |

### Conciliação e Relatório

| Método | Path | Descrição |
|---|---|---|
| `POST` | `/banco/conciliacao/auto` | Conciliação automática por valor exato ± tolerância de data |
| `GET` | `/banco/dashboard` | KPIs de conciliação + saldo projetado |
| `GET` | `/banco/conciliacao/relatorio` | Relatório detalhado (JSON ou `?export=csv`) |

---

## Status dos Lançamentos

| Status | Descrição |
|---|---|
| `pendente` | Ainda não processado pela conciliação |
| `conciliado` | Cruzado com exatidão de valor e data (dentro da tolerância) |
| `divergente` | Valor encontrado no ERP mas datas diferem além da tolerância |
| `ignorado` | Descartado manualmente (ex.: tarifa bancária, IOF) |

---

## Lógica de Conciliação Automática (`POST /banco/conciliacao/auto`)

```
Para cada LancamentoBancario com status = pendente:

  Se tipo = débito:
    → Busca Payment onde amount = lancamento.valor
                               AND payment_date ∈ [data − tol, data + tol]
                               AND payment não conciliado ainda
      → Encontrou: status = conciliado, vincula payment_id
      → Não encontrou (data ok) mas valor existe fora da janela:
           → status = divergente, registra observação com diferença em dias
      → Sem match de valor: permanece pendente

  Se tipo = crédito:
    → Busca RevenueEntry onde amount = lancamento.valor
                                   AND entry_date ∈ [data − tol, data + tol]
    → Mesma lógica acima
```

**Tolerância de data padrão:** `TOLERANCIA_DIAS = 3` dias (configurável no código).

---

## Dashboard (`GET /banco/dashboard`)

```json
{
  "total_lancamentos": 15,
  "conciliados": 10,
  "divergentes": 2,
  "pendentes": 3,
  "ignorados": 0,
  "pct_conciliado": 66.7,
  "total_creditos": 215000.0,
  "total_debitos": 80000.0,
  "saldo_inicial_contas": 70000.0,
  "saldo_projetado": 205000.0
}
```

**Saldo projetado** = Soma dos saldos iniciais das contas ativas + total_creditos − total_debitos
no período filtrado.

> ⚠️ Este saldo é uma **estimativa contábil** baseada nos lançamentos importados. Não substitui
> o saldo bancário real. Para saldo exato, todos os lançamentos do extrato devem ser importados.

---

## Exportação CSV (`GET /banco/conciliacao/relatorio?export=csv`)

Campos exportados:

```
id, conta_id, data, tipo, valor, descricao, documento_ref, status,
payment_id, revenue_entry_id, divergencia_obs
```

Arquivo nomeado automaticamente: `conciliacao_{data_inicio}_{data_fim}.csv`

---

## Frontend

Interface disponível em `/conciliacao` com três abas:

1. **Dashboard** — KPIs, barra de progresso de conciliação, botão "Conciliar Automaticamente".
2. **Lançamentos / Extrato** — tabela filtrada por status/tipo/conta, cadastro manual, botão Ignorar, exportação CSV.
3. **Contas Bancárias** — listagem, cadastro, ativar/desativar.

Alertas visuais por status: verde (conciliado), laranja (divergente), cinza (pendente/ignorado).

---

## Premissas e Limitações

| Premissa | Detalhe |
|---|---|
| Cruzamento por valor exato | A conciliação automática exige valor byte-identical (float == float). Diferenças de centavos por arredondamento não são detectadas. |
| Um-para-um | Cada lançamento do extrato é cruzado com no máximo um Payment ou RevenueEntry. Lançamentos consolidados (ex.: DETRAN com múltiplos pagamentos num só depósito) ficam divergentes. |
| Importação manual | Não há importação de arquivo OFX/CNAB nesta versão. Os lançamentos são cadastrados manualmente ou via API. |
| Saldo projetado | Estimativa com base nos lançamentos importados. Lançamentos não cadastrados (tarifas, rendimentos) distorcem o saldo. |
| Tolerância de data | Configurável via `TOLERANCIA_DIAS` em `routers/conciliacao.py`. Padrão: 3 dias. |

---

## Próximas Evoluções

1. **Importação OFX / CNAB 240** — parsear extrato bancário automaticamente.
2. **Conciliação N:1** — suporte a lançamentos consolidados (um único depósito cobrindo N pagamentos).
3. **Alertas de saldo negativo** — notificação quando `saldo_projetado < 0`.
4. **Histórico de conciliação** — log de quem conciliou cada lançamento e quando.
5. **Integração com RGF** — usar saldo conciliado como base para a disponibilidade financeira do RGF.
