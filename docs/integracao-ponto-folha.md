# Integração Ponto/Frequência → Folha de Pagamento — Documentação Técnica (Onda 16)

## Objetivo

Fechar o ciclo de legalidade operacional entre a apuração de frequência (módulo ponto) e a remuneração processada (módulo folha), convertendo automaticamente faltas injustificadas em descontos e horas extras em créditos nos `PayrollEvents` do servidor.

---

## Modelos de dados

### `ConfiguracaoIntegracaoPonto` (tabela `configuracoes_integracao_ponto`)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int PK | |
| `employee_id` | FK employees (unique) | Vincula ao servidor |
| `desconto_falta_diaria` | float \| null | Valor fixo por falta (se null = proporcional ao salário) |
| `percentual_hora_extra` | float | Adicional sobre o valor da hora normal (ex.: 50 = 50%) |
| `desconto_atraso` | bool | Se True: desconto proporcional por minuto de atraso |
| `ativo` | bool | False = servidor não é processado na integração |

### `IntegracaoPontoFolhaLog` (tabela `integracao_ponto_folha_logs`)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int PK | |
| `employee_id` | FK employees | |
| `periodo` | str(7) | `YYYY-MM` |
| `faltas_descontadas` | int | Faltas injustificadas no mês (excluindo abonadas) |
| `horas_extras_creditadas` | float | Total de horas extras no mês |
| `valor_desconto_faltas` | float | Valor total descontado por faltas |
| `valor_desconto_atrasos` | float | Valor total descontado por atrasos |
| `valor_credito_horas_extras` | float | Valor total creditado por horas extras |
| `status` | str | `ok` \| `erro` |
| `executado_por_id` | FK users (nullable) | Usuário que acionou a integração |

---

## Lógica de conversão

### 1. Desconto por faltas injustificadas

```
se desconto_falta_diaria IS NOT NULL:
    desconto_faltas = faltas_injustificadas × desconto_falta_diaria
senão (proporcional ao salário):
    valor_dia       = employee.base_salary / total_dias_uteis
    desconto_faltas = faltas_injustificadas × valor_dia
```

> `faltas_injustificadas` = total de dias úteis sem registro de ponto **e sem abono aprovado**.

### 2. Desconto por atrasos (se `desconto_atraso=True`)

```
valor_hora   = (employee.base_salary / total_dias_uteis) / horas_dia_escala
valor_minuto = valor_hora / 60
desconto_atrasos = total_minutos_atraso × valor_minuto
```

### 3. Crédito por horas extras

```
valor_hora  = (employee.base_salary / total_dias_uteis) / horas_dia_escala
fator       = 1 + (percentual_hora_extra / 100)
credito_he  = total_horas_extras × valor_hora × fator
```

### Integração com `PayrollEvent`

Cada tipo gera um `PayrollEvent` no período com:
- `kind = 'desconto'` para faltas e atrasos
- `kind = 'provento'` para horas extras
- `description` com prefixo `PONTO:` (usado para idempotência no reprocessamento)

---

## Idempotência

O endpoint `POST /integrar` é idempotente por `(employee_id, periodo)`:
- Se já existe `IntegracaoPontoFolhaLog` com `status='ok'` para o par: retorna `status='pulado'`
- Com `force=True`: deleta os `PayrollEvents` do período (apenas os com `description LIKE 'PONTO:%'`) e o log, depois recria
- Isso permite re-execução segura após correção de parâmetros ou dados de ponto

---

## Endpoints

### Configuração (`/integracao-ponto-folha/config`)

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| POST | `/config` | Cria configuração para um servidor | admin, hr |
| GET | `/config/{employee_id}` | Retorna configuração do servidor | autenticado |
| GET | `/config` | Lista todas (paginado) | autenticado |
| PATCH | `/config/{employee_id}` | Atualiza parâmetros | admin, hr |

### Operações

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| POST | `/preview` | Simula o que seria gerado (dry-run, sem persistir) | admin, hr |
| POST | `/integrar` | Persiste PayrollEvents e log. Idempotente; aceita `force=True` | admin, hr |

### Logs

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| GET | `/logs` | Lista logs com filtros `employee_id` e `periodo` (paginado) | autenticado |
| GET | `/logs/csv?periodo=YYYY-MM` | Exporta CSV do período | admin, hr, read_only |
| GET | `/dashboard?periodo=YYYY-MM` | KPIs consolidados | admin, hr, read_only |

### Dashboard KPIs

- `total_configurados` — servidores com configuração ativa
- `total_integrados` — servidores com log OK no período
- `total_faltas_descontadas`
- `total_horas_extras_creditadas`
- `total_desconto_faltas`
- `total_desconto_atrasos`
- `total_credito_horas_extras`
- `saldo_liquido` = `total_credito_horas_extras − total_desconto_faltas − total_desconto_atrasos`
- `servidores` — lista detalhada por servidor

---

## Exportação CSV

Campos: `employee_id, employee_name, periodo, faltas_descontadas, horas_extras_creditadas, valor_desconto_faltas, valor_desconto_atrasos, valor_credito_horas_extras, status`

---

## Seed de demonstração

Configura integração para os 4 primeiros servidores ativos, alternando `percentual_hora_extra` entre 50% e 100%.

---

## Premissas e limitações

| # | Premissa / Limitação |
|---|---|
| 1 | **Não gera Payslip automaticamente**: apenas cria/atualiza `PayrollEvents`. A consolidação do Payslip (gross, deductions, net) deve ser acionada manualmente no módulo RH. |
| 2 | **Percentual único de HE**: não diferencia 50% (dias úteis) de 100% (domingos/feriados). Refinamento futuro: adicionar `percentual_hora_extra_dominical` na configuração. |
| 3 | **Sem INSS/IRRF sobre créditos HE**: impostos incidem sobre o valor do PayrollEvent de provento, mas o cálculo de INSS/IRRF é responsabilidade do módulo de folha. |
| 4 | **Sem pro-rata no primeiro mês**: não realiza cálculo proporcional para servidores admitidos no meio do mês. |
| 5 | **Dia útil = escala do servidor**: se não houver `EscalaServidor` cadastrada, usa-se padrão 8h/seg–sex. Basta criar a escala correta para o servidor. |
| 6 | **Desconto de atraso**: calculado sobre os minutos acumulados reportados pelo módulo ponto. Não trata tolerância de atraso (ex.: 10 min de tolerância); isso precisaria de configuração adicional. |
| 7 | **Baixa de servidor**: ao inativar um servidor (`ConfiguracaoIntegracaoPonto.ativo=False`), ele não é mais processado em execuções futuras. Não cancela retroativamente os eventos já gerados. |

---

## Próximas evoluções sugeridas

1. **Percentual diferenciado HE** — 50% dias úteis, 100% domingos/feriados
2. **Tolerância de atraso** — janela de minutos configurável antes de iniciar desconto
3. **Geração automática de Payslip** — option flag `gerar_payslip=True` que já recalcula a folha
4. **Pro-rata no primeiro mês** — desconto e crédito proporcional para admissões no meio do período
5. **Calendário de feriados** — integração com tabela de feriados municipais/nacionais para cálculo correto de dias úteis e percentual de HE dominical
