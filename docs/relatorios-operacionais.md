# Relatórios Operacionais de Custo de Frota

## Visão geral

O módulo de Relatórios Operacionais cruza dados dos módulos **Frota**, **Almoxarifado** e **Compras** para fornecer visibilidade analítica sobre o custo total de operação (TCO) da frota municipal.

---

## Endpoints disponíveis

### `GET /relatorios/frota/custo-por-veiculo`

Custo operacional detalhado por veículo para um período selecionado.

**Parâmetros de query:**

| Parâmetro       | Tipo   | Obrigatório | Descrição                              |
|-----------------|--------|-------------|----------------------------------------|
| `data_inicio`   | date   | não         | Início do período (`YYYY-MM-DD`)       |
| `data_fim`      | date   | não         | Fim do período (`YYYY-MM-DD`)          |
| `veiculo_id`    | int    | não         | Filtra por veículo específico          |
| `departamento_id` | int  | não         | Filtra por departamento                |
| `export`        | string | não         | `csv` para download em CSV            |

**Composição do custo por linha:**

| Campo | Fonte |
|---|---|
| `custo_abastecimento` | `SUM(abastecimentos.valor_total)` no período |
| `custo_manutencao_servico` | `SUM(manutencoes_veiculo.valor_servico)` no período |
| `custo_pecas_almoxarifado` | `SUM(itens_manutencao.valor_total)` via manutenções no período |
| `custo_total` | soma das três colunas acima |

**Resposta JSON:**
```json
{
  "filtros": { "data_inicio": "2026-01-01", "data_fim": "2026-12-31", "veiculo_id": null, "departamento_id": null },
  "totais": {
    "total_veiculos": 5,
    "total_abastecimento": 12500.00,
    "total_manutencao_servico": 4300.00,
    "total_pecas_almoxarifado": 1800.00,
    "total_geral": 18600.00
  },
  "itens": [
    {
      "veiculo_id": 1, "placa": "ABC-1234", "descricao": "Caminhonete Ford Ranger",
      "tipo": "leve", "combustivel": "diesel", "departamento_id": 2,
      "n_abastecimentos": 12, "total_litros": 480.0, "custo_abastecimento": 3120.00,
      "n_manutencoes": 2, "custo_manutencao_servico": 850.00,
      "n_pecas_almoxarifado": 3, "custo_pecas_almoxarifado": 360.00,
      "custo_total": 4330.00
    }
  ]
}
```

---

### `GET /relatorios/frota/custo-por-departamento`

Custo operacional consolidado por secretaria/departamento.

**Parâmetros de query:**

| Parâmetro       | Tipo   | Obrigatório | Descrição                              |
|-----------------|--------|-------------|----------------------------------------|
| `data_inicio`   | date   | não         | Início do período (`YYYY-MM-DD`)       |
| `data_fim`      | date   | não         | Fim do período (`YYYY-MM-DD`)          |
| `departamento_id` | int  | não         | Filtra por departamento específico     |
| `export`        | string | não         | `csv` para download em CSV            |

> Departamentos que não tiveram custo no período não aparecem. Movimentações sem departamento são agrupadas em "Sem departamento".

---

## Exportação CSV

Ambos os endpoints aceitam `?export=csv`. O arquivo é nomeado automaticamente com o período:

```
custo_por_veiculo_2026-01-01_2026-12-31.csv
custo_por_departamento_2026-01-01_2026-12-31.csv
```

---

## Frontend

A interface está disponível em `/relatorios` e oferece:

- **Aba "Custo por Veículo"**: filtros de período, veículo e departamento; tabela com totalizadores; botão de exportação CSV.
- **Aba "Custo por Departamento"**: filtros de período e departamento; tabela com totalizadores; botão de exportação CSV.
- Ambas exibem KPIs resumidos (total geral, por categoria de custo).

---

## Autorização

Os endpoints requerem autenticação JWT. Todos os perfis com acesso ao sistema (`admin`, `accountant`, `procurement`, `read_only`) podem visualizar os relatórios.

---

## Rastreabilidade dos dados

| Custo | Tabela origem | Chave de período | Chave de veículo | Chave de departamento |
|---|---|---|---|---|
| Abastecimento | `abastecimentos` | `data_abastecimento` | `veiculo_id` | `departamento_id` |
| Serviço manutenção | `manutencoes_veiculo` | `data_abertura` | `veiculo_id` | `departamento_id` |
| Peças/insumos | `itens_manutencao` JOIN `manutencoes_veiculo` | `data_abertura` (manutenção) | via manutenção | via manutenção |

Cada `ItemManutencao` com `item_almoxarifado_id` possui `movimentacao_id` apontando para a saída correspondente em `movimentacoes_estoque`, garantindo rastreabilidade completa até o item de almoxarifado e ao processo de compra original (quando disponível).

---

## Próximas evoluções sugeridas

1. **Relatório por período comparativo** (mês a mês, ano a ano).
2. **Custo/km** — cruzar `custo_total` com variação de odômetro por período.
3. **Alertas de custo alto** — veículos com custo acima de limiar configurável.
4. **Integração empenho** — vincular abastecimentos e manutenções a empenhos/contratos da contabilidade.
