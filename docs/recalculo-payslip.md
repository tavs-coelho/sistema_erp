# Recálculo Automático do Payslip — Documentação Técnica (Onda 17)

## Objetivo

Fechar o ciclo completo **frequência → eventos → folha → holerite**, garantindo que ao integrar
ponto/frequência com a folha, o holerite (Payslip) do servidor seja imediatamente recalculado e
reflita descontos por faltas/atrasos e créditos por horas extras.

---

## Modelo adicionado

### `RecalcularPayslipLog` (tabela `recalcular_payslip_logs`)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int PK | |
| `employee_id` | FK employees | |
| `periodo` | str(7) | `YYYY-MM` |
| `gross_amount_anterior` | float \| null | Valor bruto antes do recálculo (null = holerite criado) |
| `gross_amount_novo` | float | Novo valor bruto |
| `deductions_anterior` | float \| null | Deduções anteriores |
| `deductions_novo` | float | Novas deduções |
| `net_amount_anterior` | float \| null | Líquido anterior |
| `net_amount_novo` | float | Novo líquido |
| `origem` | str(40) | `manual` \| `integracao_ponto` |
| `executado_por_id` | FK users (nullable) | Usuário que acionou |
| `created_at` | datetime | |

---

## Fórmula de cálculo

```
proventos = sum(PayrollEvent.value WHERE kind='provento' AND employee_id=X AND month=Y)
descontos = sum(PayrollEvent.value WHERE kind='desconto' AND employee_id=X AND month=Y)
gross     = employee.base_salary + proventos - descontos
deductions = round(gross * taxa_deducao / 100, 2)
net        = gross - deductions
```

> **`taxa_deducao`** (padrão 11%) é uma simplificação do INSS/IRRF. Em produção, substituir por
> tabelas progressivas reais do RGPS e IRRF.

### Diferença em relação ao `POST /hr/payroll/calculate` antigo

O endpoint antigo somava **todos** os eventos sem diferenciar `provento` de `desconto`,
o que causava adição incorreta dos descontos ao gross. A nova implementação trata corretamente:
- `provento` → soma ao gross
- `desconto` → subtrai do gross

O endpoint `/payroll/calculate` foi atualizado para usar a mesma lógica interna.

---

## Endpoints

### Endpoint principal

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| POST | `/hr/payslips/recalcular` | Recalcula holerites por período/servidor | admin, hr |
| GET | `/hr/payslips/recalcular/logs` | Lista logs de recálculo (filtro: periodo, employee_id) | admin, hr, read_only |

#### `POST /hr/payslips/recalcular` — body

```json
{
  "periodo": "2025-05",
  "employee_id": 3,          // opcional — omitir para processar todos
  "taxa_deducao": 11.0       // opcional — padrão 11%
}
```

#### Resposta

```json
{
  "periodo": "2025-05",
  "total_criados": 1,
  "total_atualizados": 0,
  "total_erros": 0,
  "resultados": [
    {
      "employee_id": 3,
      "employee_name": "João Silva",
      "periodo": "2025-05",
      "gross_amount": 2870.00,
      "deductions": 315.70,
      "net_amount": 2554.30,
      "status": "criado",
      "variacao_net": 2554.30
    }
  ]
}
```

> `variacao_net` = `net_novo − net_anterior` (0 para criados no primeiro recálculo)

---

### Integração automática com Ponto → Folha

O `POST /integracao-ponto-folha/integrar` agora aceita dois novos campos opcionais:

```json
{
  "periodo": "2025-05",
  "recalcular_payslip": true,   // padrão false
  "taxa_deducao": 11.0          // padrão 11%
}
```

Quando `recalcular_payslip=true`, após persistir os `PayrollEvents` de ponto, chama
`recalcular_payslip_servidor()` para cada servidor com status `ok` e inclui os resultados
na resposta:

```json
{
  "periodo": "2025-05",
  "total_ok": 1,
  ...
  "payslips_recalculados": [
    { "employee_id": 3, "gross_amount": 2870.00, "net_amount": 2554.30, ... }
  ]
}
```

---

## Idempotência

O recálculo é sempre seguro de reexecutar:
- Se o Payslip existe: atualiza `gross`, `deductions`, `net_amount`
- Se não existe: cria novo Payslip
- Cada execução gera um `RecalcularPayslipLog` (auditoria completa)
- Não há unicidade forçada em `(employee_id, periodo)` no log — múltiplas execuções ficam registradas com o histórico antes/depois

---

## Premissas e limitações

| # | Premissa / Limitação |
|---|---|
| 1 | **Taxa de dedução simplificada**: 11% fixo representa INSS simplificado. IRRF e contribuições adicionais não são calculados. |
| 2 | **Não gera PDF automaticamente**: o holerite em PDF é gerado via `GET /hr/payslips/{id}/pdf` separadamente. |
| 3 | **Sem detalhe de rubricas**: o Payslip armazena apenas `gross`, `deductions`, `net`. Rubricas individuais ficam nos `PayrollEvents`. |
| 4 | **Sem validação de competência futura**: é possível calcular holerites para períodos futuros; a validação de competência é responsabilidade do operador. |
| 5 | **Sem cálculo de 13º/férias**: eventos de 13º salário e férias devem ser adicionados manualmente como `PayrollEvents` antes do recálculo. |

---

## Próximas evoluções sugeridas

1. **Tabelas progressivas INSS/IRRF** — substituir taxa_deducao fixa por cálculo conforme faixas salariais
2. **Geração automática de PDF** — flag `gerar_pdf=True` no recalcular para retornar URL do holerite em PDF
3. **Rubricas detalhadas no Payslip** — breakdown por tipo de evento (salário base, HE, faltas, INSS, IRRF)
4. **Aprovação de folha** — workflow de aprovação antes do fechamento do período
5. **Exportação em lote** — `GET /hr/payslips/pdf/batch?period=YYYY-MM` para gerar ZIP com todos os PDFs
