# Demonstrativos RREO e RGF — LRF

## Visão Geral

O módulo **LRF** implementa os dois demonstrativos obrigatórios da Lei de Responsabilidade Fiscal calculados a partir dos dados já existentes no sistema ERP:

| Demonstrativo | Base legal | Periodicidade |
|---|---|---|
| **RREO** — Relatório Resumido da Execução Orçamentária | LRF art. 52-53 | Bimestral |
| **RGF** — Relatório de Gestão Fiscal | LRF art. 55 | Quadrimestral |

---

## RREO — Relatório Resumido da Execução Orçamentária

### Endpoint

```
GET /lrf/rreo
```

### Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `ano` | int | ano corrente | Exercício fiscal |
| `bimestre` | int (1-6) | bimestre corrente | Bimestre de referência |
| `export` | string | — | `csv` para download |

### Cálculo das linhas

| Linha | Fonte de dados | Lógica |
|---|---|---|
| Receita Prevista (LOA) | `loa_items` (category=receita) | `SUM(authorized_amount)` do exercício |
| Receita Arrecadada | `revenue_entries` | `SUM(amount)` filtrado pelo bimestre / acumulado no ano |
| Dotação Autorizada (LOA) | `loa_items` (category≠receita) | `SUM(authorized_amount)` do exercício |
| Despesa Empenhada | `commitments` | `SUM(amount)` do exercício |
| Despesa Liquidada | `liquidations` | `SUM(amount)` filtrado por `created_at` |
| Despesa Paga | `payments` | `SUM(amount)` filtrado por `payment_date` |

### Indicadores calculados

| Indicador | Fórmula |
|---|---|
| Saldo execução acumulado | Receita arrecadada acumulada − Despesa paga acumulada |
| % Receita realizada | Receita acumulada / Receita prevista × 100 |
| % Despesa executada | Despesa paga acumulada / Despesa empenhada × 100 |
| Resultado | superavit se saldo ≥ 0, déficit caso contrário |

### Exemplo de resposta JSON

```json
{
  "cabecalho": {
    "exercicio": 2026,
    "bimestre": 2,
    "periodo_bimestre": { "inicio": "2026-03-01", "fim": "2026-04-30" },
    "referencia": "2º Bimestre de 2026",
    "base_legal": "LRF art. 52-53"
  },
  "linhas": [
    { "descricao": "Receita Prevista (LOA)", "bimestre": null, "acumulado": 500000.0 },
    { "descricao": "Receita Arrecadada", "bimestre": 75000.0, "acumulado": 215000.0 },
    { "descricao": "Despesa Paga", "bimestre": 30000.0, "acumulado": 80000.0 }
  ],
  "indicadores": {
    "saldo_execucao_acumulado": 135000.0,
    "pct_receita_realizada": 43.0,
    "pct_despesa_executada": 53.33,
    "resultado": "superavit"
  }
}
```

---

## RGF — Relatório de Gestão Fiscal

### Endpoint

```
GET /lrf/rgf
```

### Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `ano` | int | ano corrente | Exercício fiscal |
| `quadrimestre` | int (1-3) | quadrimestre corrente | Quadrimestre de referência |
| `export` | string | — | `csv` para download |

### Cálculo das linhas

| Linha | Fonte de dados | Lógica |
|---|---|---|
| RCL 12 meses | `revenue_entries` | `SUM(amount)` dos 12 meses anteriores ao fim do quadrimestre |
| Despesa com Pessoal | `payslips` | `SUM(gross_amount)` no período (filtra por `month` YYYY-MM) |
| Limite legal 60 % RCL | — | RCL × 0,60 — LRF art. 19, III (municípios) |
| Limite alerta 54 % RCL | — | RCL × 0,54 — limite prudencial LRF art. 22 |
| Dívida Consolidada | `commitments` | `SUM(amount)` com status in {empenhado, liquidado} do exercício |
| Disponibilidade Financeira | Derivada | Receita arrecadada − Despesa paga |

### Indicadores calculados

| Indicador | Descrição |
|---|---|
| `pct_despesa_pessoal_rcl` | % da despesa pessoal sobre a RCL |
| `situacao_despesa_pessoal` | `REGULAR` / `ALERTA` (>54%) / `EXCEDIDO` (>60%) |
| `excesso_despesa_pessoal` | Valor que excede o limite de 60 % (0 se REGULAR/ALERTA) |

### Alertas gerados no frontend

- **EXCEDIDO**: exibe banner vermelho — medidas de contenção obrigatórias (LRF art. 23).
- **ALERTA**: exibe banner amarelo — vedada a criação de novas despesas de pessoal (LRF art. 22).

---

## Exportação CSV

Ambos os endpoints aceitam `?export=csv`. O arquivo é nomeado automaticamente:

```
rreo_2026_bim2.csv
rgf_2026_quad1.csv
```

A estrutura do CSV replica as linhas do relatório, seguida de um bloco separado com todos os indicadores calculados.

---

## Frontend

A interface está disponível em `/lrf` e oferece:

- **Aba RREO**: seletor de exercício e bimestre, KPI cards (saldo, % receita, % despesa, resultado), tabela bimestre/acumulado, botão CSV.
- **Aba RGF**: seletor de exercício e quadrimestre, KPI cards (RCL, pessoal, % pessoal/RCL, situação, dívida, disponibilidade), tabela quadrimestre/acumulado, alertas visuais automáticos, botão CSV.

---

## Premissas e Limitações

| Premissa | Detalhe |
|---|---|
| Receita prevista | Extraída de `LOAItem.authorized_amount` (category=`receita`). Se não houver LOA cadastrada para o exercício, o valor é 0. |
| Despesa pessoal | Usa `Payslip.gross_amount` (bruto). Não inclui encargos patronais (INSS, FGTS) que não são modelados separadamente. |
| RCL | Aproximação: soma das `RevenueEntry` dos 12 meses precedentes. Deduções de transferências constitucionais não são aplicadas (modelo simplificado). |
| Dívida consolidada | Empenhos do exercício com status `empenhado` ou `liquidado` (ainda não pagos). Não inclui dívidas de exercícios anteriores. |
| Conciliação bancária | Não implementada — a disponibilidade financeira é uma estimativa contábil, não bancária. |

---

## Próximas Evoluções

1. **Deduções da RCL** — para cálculo preciso, subtrair transferências constitucionais (FUNDEB, etc.).
2. **Dívida de exercícios anteriores** — incluir restos a pagar de exercícios anteriores no cálculo da dívida consolidada.
3. **Encargos patronais** — modelar separadamente para cálculo correto da despesa com pessoal.
4. **Exportação PDF** — geração de PDF via biblioteca (`weasyprint` ou similar) para publicação oficial.
5. **Histórico de publicações** — registrar cada geração do relatório com timestamp e usuário responsável.
