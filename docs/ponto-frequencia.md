# Ponto e Frequência de Servidores — Documentação Técnica

## Objetivo

Implementar a vertical de controle de ponto e frequência de servidores públicos municipais, integrada ao módulo RH existente (`Employee`). O módulo cobre registro de ponto, cálculo automático de frequência mensal (presenças, faltas, horas extras, atrasos) e fluxo de abonos de falta/atraso com aprovação.

---

## Modelos de dados

### `EscalaServidor` (tabela `escalas_servidores`)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int PK | |
| `employee_id` | FK Employee (unique) | Um servidor tem uma escala |
| `horas_dia` | float | Carga horária contratual diária (ex: 8.0, 6.0) |
| `dias_semana` | str(7) | Dias de trabalho: `"12345"` = seg–sex; `"1"=Seg`, `"7"=Dom` |
| `hora_entrada` | str(5) | `HH:MM` |
| `hora_saida` | str(5) | `HH:MM` |
| `hora_inicio_intervalo` | str(5) | `HH:MM` |
| `hora_fim_intervalo` | str(5) | `HH:MM` |

Se não houver escala cadastrada, o sistema aplica o padrão: **8h/dia, seg–sex, 08:00–17:00, intervalo 12:00–13:00**.

### `RegistroPonto` (tabela `registros_ponto`)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int PK | |
| `employee_id` | FK Employee | |
| `data` | date | Dia do registro |
| `tipo_registro` | str | `entrada` \| `saida` \| `inicio_intervalo` \| `fim_intervalo` |
| `hora_registro` | str(5) | `HH:MM` |
| `origem` | str | `manual` \| `biometrico` \| `portal` |
| `observacoes` | text | |
| `created_at` | datetime | |

**Unicidade implícita**: um servidor não pode ter dois registros do mesmo `tipo_registro` no mesmo dia (retorna 409).

### `AbonoFalta` (tabela `abonos_falta`)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int PK | |
| `employee_id` | FK Employee | |
| `data` | date | Dia da falta/atraso |
| `tipo` | str | `falta` \| `atraso` \| `folga_compensacao` |
| `motivo` | text | Justificativa |
| `status` | str | `pendente` \| `aprovado` \| `rejeitado` |
| `aprovado_por_id` | FK User (nullable) | Quem aprovou/rejeitou |
| `created_at` | datetime | |

---

## Lógica de cálculo da folha de frequência

Para cada dia do mês solicitado:

### Dia útil com marcação completa (entrada + saída)

```
intervalo_min = fim_intervalo - inicio_intervalo   (se informado)
             ou escala.hora_fim_intervalo - escala.hora_inicio_intervalo   (default)

horas_trabalhadas = (saida - entrada - intervalo_min) / 60
horas_extras = max(0, horas_trabalhadas - escala.horas_dia)
minutos_atraso = max(0, entrada_real - escala.hora_entrada)   (em minutos)
status_dia = "presente"
```

### Dia útil sem marcação de entrada/saída

```
falta = True
status_dia = "falta"           se não há abono aprovado
status_dia = "falta_abonada"   se há abono aprovado para esse dia
```

### Dia não útil (final de semana / fora da `dias_semana`)

```
falta = False
status_dia = "fim_semana" (se weekday >= 5) ou "folga"
```

### Totalizadores da folha

```
total_dias_uteis = dias com dia_util = True
total_presencas = dias com dia_util + entrada + saida registrados
total_faltas = dias úteis com falta = True e sem abono aprovado
total_faltas_abonadas = dias úteis com falta = True e com abono aprovado
total_horas_trabalhadas = soma de horas_trabalhadas
total_horas_extras = soma de horas_extras
total_minutos_atraso = soma de minutos_atraso
```

**Verificação**: `total_presencas + total_faltas + total_faltas_abonadas = total_dias_uteis`

---

## Endpoints

### Escala (`/ponto/escalas`)

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| POST | `/ponto/escalas` | Cria escala de um servidor | admin, hr |
| GET | `/ponto/escalas/{employee_id}` | Retorna escala do servidor | autenticado |
| PATCH | `/ponto/escalas/{employee_id}` | Atualiza escala | admin, hr |

### Registros (`/ponto/registros`)

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| POST | `/ponto/registros` | Registra ponto (entrada/saída/intervalo) | autenticado¹ |
| GET | `/ponto/registros` | Lista com filtros: `employee_id`, `data_inicio`, `data_fim`, `tipo_registro` | autenticado |
| DELETE | `/ponto/registros/{id}` | Remove registro (retificação) | admin, hr |

¹ Servidor (`employee` role) só pode registrar o próprio ponto.

### Folha de Frequência (`/ponto/folha`)

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| GET | `/ponto/folha/{employee_id}/{periodo}` | Folha mensal (período = YYYY-MM) | autenticado¹ |
| GET | `/ponto/folha/{employee_id}/{periodo}/csv` | Export CSV | admin, hr, read_only |

¹ Servidor só pode ver a própria folha.

### Abonos (`/ponto/abonos`)

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| POST | `/ponto/abonos` | Solicita abono de falta/atraso | autenticado¹ |
| GET | `/ponto/abonos` | Lista com filtros: `employee_id`, `status`, `data_inicio`, `data_fim` | autenticado |
| PATCH | `/ponto/abonos/{id}` | Aprova ou rejeita abono | admin, hr |

¹ Servidor só pode solicitar abono para si mesmo.

### Dashboard (`/ponto/dashboard`)

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| GET | `/ponto/dashboard?periodo=YYYY-MM` | KPIs de frequência de todos os servidores | admin, hr, read_only |

KPIs retornados:
- `total_servidores`
- `total_presencas`, `total_faltas`, `total_faltas_abonadas`
- `total_horas_extras`
- `total_minutos_atraso`
- `abonos_pendentes`
- `servidores_com_falta` (top 10 por faltas)

---

## Exportação CSV da folha

Campos: `data, dia_semana, dia_util, entrada, saida, inicio_intervalo, fim_intervalo, horas_trabalhadas, horas_extras, minutos_atraso, falta, abonado, abono_tipo, status_dia`

---

## Seed de demonstração

| Item | Descrição |
|---|---|
| `EscalaServidor` emp1 | 8h/dia, seg–sex, 08:00–17:00 (intervalo 12:00–13:00) |
| `EscalaServidor` emp2 | 6h/dia, seg–sex, 07:00–13:00 (intervalo 10:00–10:15) |
| Registros emp1 | Todos os dias úteis do mês anterior com ponto completo, exceto: dia 5 (falta), dia 10 (atraso de 25min), dia 15 (saída às 19h = 2h extras) |
| `AbonoFalta` emp1 | Abono aprovado para o dia 5 do mês anterior (consulta médica) |

---

## Premissas e limitações

| # | Premissa/Limitação |
|---|---|
| 1 | **Ponto manual**: não há integração com relógio biométrico/REP-C. O campo `origem` aceita `biometrico` mas não há integração real. Para uso real, precisaria de webservice de integração com o REP ou importação de arquivo AFD. |
| 2 | **Sem feriados**: o sistema não tem calendário de feriados. Dias oficialmente feriados são tratados como dias úteis se estiverem na escala do servidor. Para produção, implementar tabela `feriados_municipais`. |
| 3 | **Unicidade de tipo por dia**: um servidor não pode ter dois "entrada" no mesmo dia. Para sistemas com múltiplos REPs ou retificações, seria necessário modelo mais flexível com pareamento de marcações. |
| 4 | **Horas extras simples**: o cálculo não considera diferenciação de percentual (50% vs 100% nos finais de semana, feriados etc.). Serve para controle operacional; para cálculo de pagamento, precisaria de regras complementares. |
| 5 | **Integração folha de pagamento**: o módulo não alimenta automaticamente `PayrollEvent` com desconto de faltas ou adicional de horas extras. Esse vínculo precisaria ser implementado no fluxo de cálculo da folha. |
| 6 | **Escala única por servidor**: um servidor tem uma escala estática. Não suporta escalas rotativas (plantão 12×36) ou alterações no meio do mês. |
| 7 | **Banco de horas não implementado**: horas extras são calculadas e exibidas, mas não há saldo acumulado de banco de horas para compensação futura. |

---

## Próximas evoluções sugeridas

1. **Importação AFD/AFDT** — arquivo padrão de relógio de ponto eletrônico (REP-C, Portaria MTE 1.510)
2. **Calendário de feriados municipais** — integrar ao cálculo de dias úteis
3. **Banco de horas** — acumulação e compensação de horas extras
4. **Integração PayrollEvent** — desconto automático por falta e adicional por hora extra ao calcular folha
5. **Escala rotativa** — suporte a plantões (12×36, sobreaviso, turnos)
6. **Relatório gerencial** — frequência por departamento, comparativo mensal, mapa de ponto
