# NFS-e e ITBI — Documentação Técnica

## Objetivo

Implementar a vertical de receitas municipais de serviços (ISS/NFS-e) e transmissão imobiliária (ITBI), integrando-os ao módulo tributário existente com geração automática de lançamentos.

---

## Modelos de dados

### `NotaFiscalServico` (tabela `notas_fiscais_servico`)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int PK | |
| `numero` | str unique | Ex: `NFS/2026-0001` |
| `prestador_id` | FK Contribuinte | Emissor da nota |
| `tomador_id` | FK Contribuinte (nullable) | Tomador do serviço |
| `descricao_servico` | text | |
| `codigo_servico` | str | Item da LC 116/2003 (ex: `1.07`) |
| `competencia` | str | `YYYY-MM` |
| `data_emissao` | date | |
| `valor_servico` | float | Valor bruto |
| `valor_deducoes` | float | Deduções da base ISS |
| `aliquota_iss` | float | % (ex: 2.5) |
| `valor_iss` | float | Calculado: `(servico - deducoes) * aliquota / 100` |
| `retencao_fonte` | bool | ISS retido pelo tomador |
| `status` | str | `emitida` \| `cancelada` \| `substituida` |
| `nota_substituta_id` | FK self (nullable) | Para substituição de nota |
| `lancamento_id` | FK LancamentoTributario | Gerado automaticamente na emissão |
| `observacoes` | text | |
| `created_at` | datetime | |

### `OperacaoITBI` (tabela `operacoes_itbi`)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int PK | |
| `numero` | str unique | Ex: `ITBI/2026-0001` |
| `transmitente_id` | FK Contribuinte | Vendedor/transmitente |
| `adquirente_id` | FK Contribuinte | Comprador/adquirente |
| `imovel_id` | FK ImovelCadastral | |
| `natureza_operacao` | str | `compra_venda` \| `doacao` \| `permuta` \| `heranca` \| `adjudicacao` \| `integralizacao_capital` |
| `data_operacao` | date | |
| `valor_declarado` | float | Informado pelo contribuinte |
| `valor_venal_referencia` | float | Valor venal municipal de referência |
| `base_calculo` | float | `max(declarado, venal_referencia)` |
| `aliquota_itbi` | float | % (ex: 2.0) |
| `valor_devido` | float | `base_calculo * aliquota / 100` |
| `status` | str | `aberto` \| `pago` \| `cancelado` |
| `lancamento_id` | FK LancamentoTributario | Gerado automaticamente no registro |
| `observacoes` | text | |
| `created_at` | datetime | |

---

## Lógica de cálculo

### ISS (NFS-e)

```
base_iss = max(valor_servico - valor_deducoes, 0)
valor_iss = round(base_iss * aliquota_iss / 100, 2)
```

O vencimento do `LancamentoTributario` gerado é sempre o **dia 20 do mês de competência**.

### ITBI

```
valor_venal_referencia_efetivo = valor_venal_referencia if > 0 else imovel.valor_venal
base_calculo = max(valor_declarado, valor_venal_referencia_efetivo)
valor_devido = round(base_calculo * aliquota_itbi / 100, 2)
```

O vencimento do `LancamentoTributario` gerado é a **data da operação**.

---

## Endpoints

### NFS-e (`/nfse`)

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| POST | `/nfse/emitir` | Emite NFS-e + cria LancamentoTributario ISS | autenticado |
| GET | `/nfse` | Lista com filtros: `prestador_id`, `tomador_id`, `status`, `competencia`, `data_inicio`, `data_fim` | autenticado |
| GET | `/nfse/{id}` | Detalhe | autenticado |
| PATCH | `/nfse/{id}/cancelar?motivo=` | Cancela nota e lançamento associado | admin, accountant |
| GET | `/nfse/relatorio?export=csv` | Relatório JSON paginado ou CSV | autenticado |

### ITBI (`/itbi`)

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| POST | `/itbi/registrar` | Registra operação + cria LancamentoTributario ITBI | autenticado |
| GET | `/itbi` | Lista com filtros: `adquirente_id`, `transmitente_id`, `imovel_id`, `status`, `natureza_operacao`, `data_inicio`, `data_fim` | autenticado |
| GET | `/itbi/{id}` | Detalhe | autenticado |
| PATCH | `/itbi/{id}/cancelar?motivo=` | Cancela operação e lançamento | admin, accountant |
| GET | `/itbi/relatorio?export=csv` | Relatório JSON paginado ou CSV | autenticado |

### Dashboard (`/nfse-itbi`)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/nfse-itbi/dashboard` | KPIs: NFS-e emitidas/canceladas, ISS emitido/arrecadado, ITBI aberto/pago, totais |

---

## Integração com módulo tributário

Toda emissão de NFS-e e todo registro de ITBI **gera automaticamente** um `LancamentoTributario` com:
- `tributo = "ISS"` ou `"ITBI"`
- `status = "aberto"` (segue o fluxo normal: guia → baixa → pago)
- `contribuinte_id = prestador_id` (ISS) ou `adquirente_id` (ITBI)
- `imovel_id` preenchido apenas para ITBI

O cancelamento da NFS-e / operação ITBI **também cancela o lançamento** se ainda estiver `aberto`.

---

## Seed de demonstração

Incluídos no seed de startup:

| Item | Descrição |
|---|---|
| NFS-e `NFS/YYYY-0001` | Consultoria em TI, R$ 5.000, ISS 2%, lançamento gerado |
| NFS-e `NFS/YYYY-0002` | Manutenção de equipamentos, R$ 3.200, ISS 3%, retenção na fonte |
| ITBI `ITBI/YYYY-0001` | Compra e venda, declarado R$ 250k, venal R$ 280k, base = R$ 280k, ITBI 2% = R$ 5.600 |

---

## Exportação CSV

### NFS-e
Campos: `numero, prestador_id, tomador_id, competencia, data_emissao, valor_servico, valor_deducoes, aliquota_iss, valor_iss, retencao_fonte, status, lancamento_id`

### ITBI
Campos: `numero, transmitente_id, adquirente_id, imovel_id, natureza_operacao, data_operacao, valor_declarado, valor_venal_referencia, base_calculo, aliquota_itbi, valor_devido, status, lancamento_id`

---

## Premissas e limitações

| # | Premissa/Limitação |
|---|---|
| 1 | **NFS-e simplificada**: não integra com SEFAZ/Provedor municipal. A "emissão" é interna ao sistema. Para uso real, precisaria de integração com webservice municipal (ABRASF ou ISS.net). |
| 2 | **Número sequencial simples**: contagem total de registros +1. Em ambiente distribuído, usar sequence do banco. |
| 3 | **Alíquota ISS por nota**: cada nota define sua própria alíquota. Para ambiente real, a alíquota deveria vir de tabela por código de serviço. |
| 4 | **ITBI sem escritura eletrônica**: não integra com cartório ou SINTER/Serpro. O registro é apenas fiscal/municipal. |
| 5 | **Valor venal de referência**: o sistema aceita o informado ou usa o `valor_venal` do cadastro imobiliário. Para produção, deveria ser auditado por laudo técnico. |
| 6 | **ISS retido na fonte**: o campo `retencao_fonte` é informacional — a responsabilidade de recolhimento pelo tomador não altera o status do lançamento automaticamente. |
| 7 | **Substituição de nota**: o campo `nota_substituta_id` está modelado mas o fluxo de substituição (emitir nova nota e vincular à cancelada) não foi implementado nesta onda. |
| 8 | **Baixa manual ITBI**: o status `pago` não é alterado automaticamente pela baixa da guia. Precisaria de integração com o fluxo `GuiaPagamento.baixar`. |

---

## Próximas evoluções sugeridas

1. **Tabela de alíquotas ISS por código de serviço** — parametrização municipal
2. **Substituição de NFS-e** — fluxo emite nova nota vinculada à cancelada
3. **Baixa automática ITBI** via integração com `GuiaPagamento`
4. **Integração com RGF/RREO** — ISS e ITBI como receitas tributárias nos demonstrativos
5. **Relatório de arrecadação ISS/ITBI por competência** — comparativo mês a mês
