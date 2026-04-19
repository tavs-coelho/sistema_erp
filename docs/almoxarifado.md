# Módulo Almoxarifado — Documentação Operacional

## Visão Geral

O módulo **Almoxarifado** controla o estoque de materiais e suprimentos da prefeitura, registrando entradas de compras/doações e saídas/requisições por departamento, com rastreabilidade completa e auditoria.

---

## Funcionalidades implementadas

| Funcionalidade | Rota backend | Descrição |
|---|---|---|
| Listar itens | `GET /almoxarifado/itens` | Filtros: busca, categoria, ativo, abaixo_minimo; exportação CSV |
| Obter item | `GET /almoxarifado/itens/{id}` | Detalhe completo |
| Cadastrar item | `POST /almoxarifado/itens` | Código único, unidade, categoria, estoque mínimo, valor unitário |
| Atualizar item | `PUT /almoxarifado/itens/{id}` | Atualiza campos; inativação |
| Excluir item | `DELETE /almoxarifado/itens/{id}` | Só permite se sem movimentações |
| Registrar movimentação | `POST /almoxarifado/movimentacoes` | Entrada ou saída; valida saldo; atualiza custo médio ponderado |
| Listar movimentações | `GET /almoxarifado/movimentacoes` | Filtros: item, tipo, departamento, período; exportação CSV |
| Obter movimentação | `GET /almoxarifado/movimentacoes/{id}` | Detalhe |
| Consultar saldo | `GET /almoxarifado/saldo/{item_id}` | Saldo atual, valor de estoque, alerta de mínimo |
| Dashboard | `GET /almoxarifado/dashboard` | Totais, itens abaixo do mínimo, valor total em estoque, entradas/saídas do mês |

---

## Modelos de Dados

### `ItemAlmoxarifado`

| Campo | Tipo | Descrição |
|---|---|---|
| `codigo` | String(30) | Código interno ou CATMAT (único) |
| `descricao` | String(200) | Descrição do material |
| `unidade` | String(10) | Unidade de medida (UN, KG, CX, L…) |
| `categoria` | String(60) | material_consumo, permanente, medicamento, limpeza, etc. |
| `localizacao` | String(80) | Prateleira ou corredor no almoxarifado |
| `estoque_minimo` | Float | Quantidade mínima desejável (alerta) |
| `estoque_atual` | Float | Saldo atual (atualizado automaticamente) |
| `valor_unitario` | Float | Custo médio ponderado (atualizado em entradas) |
| `ativo` | Boolean | Se inativo, não permite movimentações |

### `MovimentacaoEstoque`

| Campo | Tipo | Descrição |
|---|---|---|
| `item_id` | FK | Item movimentado |
| `tipo` | String(10) | `entrada` ou `saida` |
| `quantidade` | Float | Quantidade movimentada |
| `valor_unitario` | Float | Valor unitário na data da movimentação |
| `valor_total` | Float | `quantidade × valor_unitario` |
| `data_movimentacao` | Date | Data efetiva da movimentação |
| `departamento_id` | FK | Departamento requisitante (opcional, saídas) |
| `responsavel_id` | FK | Usuário que registrou |
| `documento_ref` | String(80) | Nota fiscal, número de requisição, etc. |
| `saldo_pos` | Float | Saldo do item após a movimentação (rastreabilidade) |

---

## Regras de Negócio

1. **Entrada**: Aumenta `estoque_atual`. Atualiza `valor_unitario` pelo custo médio ponderado quando `valor_unitario > 0`.
2. **Saída**: Reduz `estoque_atual`. Rejeitada com HTTP 422 se `quantidade > estoque_atual`.
3. **Quantidade zero ou negativa**: Rejeitada com HTTP 422.
4. **Item inativo**: Qualquer movimentação é rejeitada até reativação.
5. **Exclusão**: Não é permitida se o item possuir movimentações — deve-se inativar.
6. **Auditoria**: Todas as operações de criação, atualização e movimentação geram registro em `audit_logs`.

---

## Alertas

- Itens com `estoque_atual < estoque_minimo` são sinalizados em amarelo no frontend e contabilizados no dashboard.
- O filtro `?abaixo_minimo=true` retorna somente estes itens para facilitar geração de solicitações de compra.

---

## Procedimento de Entrada de Estoque

1. Receber o material e conferir com a nota fiscal / requisição de compra.
2. Acessar `Almoxarifado → Entrada / Saída → 📥 Entrada`.
3. Informar: ID do item, quantidade, valor unitário, data, número da nota fiscal em "Documento referência".
4. Confirmar — o saldo é atualizado imediatamente e o custo médio é recalculado.

## Procedimento de Saída / Requisição

1. Departamento solicita o material com formulário de requisição.
2. Responsável acessa `Almoxarifado → Entrada / Saída → 📤 Saída / Requisição`.
3. Informar: ID do item, quantidade, data, departamento, número da requisição.
4. Confirmar — o saldo é abatido. Saída é bloqueada se saldo insuficiente.

---

## API — Exemplos

```bash
# Cadastrar item
curl -X POST /almoxarifado/itens \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"codigo":"MAT-001","descricao":"Papel A4","unidade":"RM","estoque_minimo":10,"valor_unitario":25.50}'

# Entrada de 50 resmas
curl -X POST /almoxarifado/movimentacoes \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"item_id":1,"tipo":"entrada","quantidade":50,"valor_unitario":25.50,"data_movimentacao":"2026-04-01","documento_ref":"NF-12345"}'

# Saída de 5 resmas para Saúde
curl -X POST /almoxarifado/movimentacoes \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"item_id":1,"tipo":"saida","quantidade":5,"valor_unitario":0,"data_movimentacao":"2026-04-10","departamento_id":1,"documento_ref":"REQ-001"}'

# Consultar saldo
curl /almoxarifado/saldo/1 -H "Authorization: Bearer $TOKEN"

# Exportar histórico CSV
curl "/almoxarifado/movimentacoes?item_id=1&export=csv" -H "Authorization: Bearer $TOKEN"
```

---

## Pendências e Próximos Passos

| Item | Prioridade | Observação |
|---|---|---|
| Solicitação de compra automática ao atingir mínimo | Alta | Criar requisição de compra vinculada ao módulo de compras |
| Inventário periódico / conferência física | Média | Ajuste de estoque manual justificado |
| Relatório de consumo por departamento | Média | Agrupamento de saídas por departamento/período |
| Lote e validade (para medicamentos) | Média | Campo de lote e data de validade nas entradas |
| Integração com Compras (ProcurementProcess) | Alta | Entrada automática ao empenhar/pagar fornecedor |
| Transferência entre almoxarifados | Baixa | Para municípios com múltiplos depósitos |

---

## Integração Almoxarifado ↔ Compras

### Modelos Adicionais

**`RecebimentoMaterial`** — representa o ato físico de recepção de materiais:

| Campo | Tipo | Descrição |
|---|---|---|
| `processo_id` | FK | Processo licitatório de origem |
| `contrato_id` | FK | Contrato vinculado (opcional) |
| `vendor_id` | FK | Fornecedor (opcional, pode estar no contrato) |
| `commitment_id` | FK | Empenho vinculado (opcional) |
| `nota_fiscal` | String(60) | Número da nota fiscal do fornecedor |
| `data_recebimento` | Date | Data da entrega física |
| `status` | String(20) | `pendente`, `conferido`, `recusado` |
| `responsavel_id` | FK | Usuário que registrou o recebimento |

**`ItemRecebimento`** — linha de item no recebimento:

| Campo | Tipo | Descrição |
|---|---|---|
| `recebimento_id` | FK | Recebimento pai |
| `item_almoxarifado_id` | FK | Item do almoxarifado correspondente |
| `quantidade_recebida` | Float | Quantidade entregue fisicamente |
| `valor_unitario` | Float | Preço unitário da nota fiscal |
| `movimentacao_id` | FK | `MovimentacaoEstoque` gerada ao confirmar |

**Campos adicionados a `MovimentacaoEstoque`:**

| Campo | Tipo | Descrição |
|---|---|---|
| `processo_id` | FK | Rastreabilidade: processo de origem |
| `contrato_id` | FK | Rastreabilidade: contrato de origem |
| `recebimento_id` | FK | Rastreabilidade: recebimento que gerou a entrada |

### Fluxo Ponta a Ponta

```
Processo Licitatório  →  Contrato  →  Empenho
          ↓
   Recebimento de Material (status=pendente)
          ↓
   Conferência física / CONFIRMAR
          ↓
   MovimentacaoEstoque (entrada) gerada automaticamente
   ↗ processo_id, contrato_id, recebimento_id preenchidos
          ↓
   ItemAlmoxarifado.estoque_atual atualizado
   ItemAlmoxarifado.valor_unitario (custo médio) atualizado
```

### Novos Endpoints

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/almoxarifado/recebimentos` | Cria recebimento (status=pendente) |
| POST | `/almoxarifado/recebimentos/{id}/confirmar` | Confirma → gera entradas de estoque |
| POST | `/almoxarifado/recebimentos/{id}/recusar` | Recusa (material devolvido) |
| GET | `/almoxarifado/recebimentos` | Lista com filtros |
| GET | `/almoxarifado/recebimentos/{id}` | Detalhe + itens |
| GET | `/procurement/processes/{id}/recebimentos` | Recebimentos de um processo |
| GET | `/procurement/contracts/{id}/recebimentos` | Recebimentos de um contrato |

### Regras de Negócio da Integração

1. **Recebimento pendente**: registra a intenção de entrada sem modificar o estoque.
2. **Confirmação**: cria um `MovimentacaoEstoque` por item, atualiza `estoque_atual` e recalcula custo médio ponderado.
3. **Recusa**: não altera estoque; registra motivo em `observacoes`; fluxo de devolução ao fornecedor fica fora do sistema por ora.
4. **Idempotência**: confirmar um recebimento já `conferido` retorna HTTP 422.
5. **Rastreabilidade**: toda entrada via recebimento carrega `processo_id`, `contrato_id` e `recebimento_id` na movimentação — permite auditoria e consulta bidirecional.

### Exemplo de uso via API

```bash
# 1. Criar recebimento (após entrega física)
curl -X POST /almoxarifado/recebimentos \
  -d '{
    "processo_id": 3, "contrato_id": 2, "vendor_id": 1,
    "nota_fiscal": "NF-45678", "data_recebimento": "2026-04-19",
    "itens": [
      {"item_almoxarifado_id": 5, "quantidade_recebida": 100, "valor_unitario": 25.90},
      {"item_almoxarifado_id": 8, "quantidade_recebida": 20,  "valor_unitario": 12.50}
    ]
  }'

# 2. Conferir e confirmar (altera estoque)
curl -X POST /almoxarifado/recebimentos/7/confirmar

# 3. Verificar saldo e rastreabilidade
curl /almoxarifado/saldo/5
curl "/almoxarifado/movimentacoes?item_id=5"
# → movimentação retorna processo_id=3, contrato_id=2, recebimento_id=7

# 4. Consultar todos recebimentos de um processo
curl /procurement/processes/3/recebimentos
```
