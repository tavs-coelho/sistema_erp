# Auditoria Técnica de Aderência ao Edital — Sistema ERP Municipal

**Data:** 2026-04-19  
**Base de análise:** repositório `tavs-coelho/sistema_erp`, branch `copilot/diagnostico-tecnico-erp`

---

## Metodologia

A auditoria avalia cada módulo e requisito técnico esperado num ERP Municipal quanto ao grau de implementação, classificando-os em:

| Classificação | Critério |
|---|---|
| ✅ **Atende** | Implementado, testado, com frontend demonstrável |
| ⚠️ **Atende Parcialmente** | Funcionalidade presente mas com lacunas funcionais ou de UX |
| ❌ **Pendente Crítico** | Módulo ausente ou insuficiente para demonstração |

---

## 1. Módulos Administrativos

### 1.1 Orçamento Municipal (PPA / LDO / LOA)

| Item | Status | Observação |
|---|---|---|
| Cadastro de PPA (Plano Plurianual) | ✅ Atende | CRUD completo com programas e metas |
| Cadastro de LDO (Lei de Diretrizes Orçamentárias) | ✅ Atende | Metas e diretrizes por exercício |
| Cadastro de LOA (Lei Orçamentária Anual) | ✅ Atende | Dotações com código função/subfunção/programa/ação |
| Execução orçamentária (empenho, liquidação, pagamento) | ✅ Atende | Commitment → Liquidation → Payment na contabilidade |
| Acompanhamento de saldo autorizado vs executado | ⚠️ Atende Parcialmente | LOAItem tem `executed_amount` mas atualização automática ao empenhar não está implementada |
| Relatórios orçamentários | ⚠️ Atende Parcialmente | Dados existem; relatório específico de execução orçamentária não foi implementado |

---

### 1.2 Compras e Licitações

| Item | Status | Observação |
|---|---|---|
| Cadastro de processo licitatório | ✅ Atende | `ProcurementProcess` com número, objeto, status |
| Cadastro de fornecedores | ✅ Atende | `Vendor` com CNPJ único |
| Contratos com fornecedor | ✅ Atende | `Contract` com valor, vigência, addenda |
| Empenhos vinculados ao contrato | ✅ Atende | `Commitment` com departamento, fornecedor, exercício |
| Recebimento de material | ✅ Atende | `RecebimentoMaterial` com conferência e vinculação almoxarifado |
| Integração compras → almoxarifado | ✅ Atende | Recebimento gera entrada automática em estoque |
| Integração alerta estoque → requisição de compra | ✅ Atende | Alerta gera `RequisicaoCompra` automaticamente |
| Portal público de licitações | ✅ Atende | Endpoint `/public/licitacoes` acessível sem autenticação |
| Publicação de contratos e resultados | ⚠️ Atende Parcialmente | Dados existem; frontend de portal público é básico |

---

### 1.3 Almoxarifado / Controle de Estoque

| Item | Status | Observação |
|---|---|---|
| Cadastro de itens com código/CATMAT | ✅ Atende | Código único, categoria, localização, unidade |
| Entradas de estoque | ✅ Atende | Tipo entrada, rastreável a recebimento/contrato |
| Saídas de estoque por departamento | ✅ Atende | Saída com departamento, responsável, documento ref |
| Saldo atual em tempo real | ✅ Atende | `estoque_atual` atualizado atomicamente |
| Histórico de movimentações | ✅ Atende | Filtros por item/tipo/departamento/período + CSV |
| Alerta automático de estoque mínimo | ✅ Atende | Gerado em toda saída que ultrapassa o mínimo |
| Requisição de compra automática | ✅ Atende | Gerada automaticamente ao abrir alerta |
| Exportação CSV de movimentações | ✅ Atende | Endpoint com `?export=csv` |

---

### 1.4 Patrimônio

| Item | Status | Observação |
|---|---|---|
| Cadastro de bens patrimoniais | ✅ Atende | `Asset` com tombamento, classificação, departamento |
| Transferência entre departamentos | ✅ Atende | `AssetMovement` com rastreabilidade |
| Status do bem (ativo, baixado, etc.) | ✅ Atende | Campo status com transições |
| Inventário por departamento | ⚠️ Atende Parcialmente | Lista existe; relatório de inventário formal não foi implementado |
| Depreciação | ❌ Pendente Crítico | Não implementada; esperada em ERPs municipais para NBCASP |
| Reavaliação e ajuste de valor | ❌ Pendente Crítico | Não implementada |

---

### 1.5 Frota

| Item | Status | Observação |
|---|---|---|
| Cadastro de veículos | ✅ Atende | Placa, tipo, combustível, odômetro, departamento |
| Registro de abastecimentos | ✅ Atende | Litros, valor/litro, odômetro, posto, NF |
| Controle de manutenções | ✅ Atende | Tipos preventiva/corretiva, lifecycle, peças |
| Peças vinculadas ao almoxarifado | ✅ Atende | Saída automática ao adicionar item de manutenção |
| Controle de consumo (dashboard) | ✅ Atende | KPIs por veículo e frota total |
| Rastreabilidade veículo → manutenção → almoxarifado | ✅ Atende | `movimentacao_id` em cada `ItemManutencao` |
| Relatório TCO por veículo | ✅ Atende | `/relatorios/frota/custo-por-veiculo` com CSV |
| Relatório TCO por departamento | ✅ Atende | `/relatorios/frota/custo-por-departamento` com CSV |
| Relatório L/100km | ❌ Pendente Crítico | Não implementado; requer odômetro consistente |
| Alertas de manutenção preventiva por km | ❌ Pendente Crítico | Não implementado |

---

### 1.6 Recursos Humanos

| Item | Status | Observação |
|---|---|---|
| Cadastro de funcionários | ✅ Atende | `Employee` com matrícula, cargo, departamento |
| Cargos e departamentos | ✅ Atende | Tabelas `Department`, `JobPosition` com hierarquia |
| Folha de pagamento (eventos) | ✅ Atende | `PayrollEvent`, `PayrollEntry` com cálculo e fechamento |
| Portal do servidor | ✅ Atende | Visualização de contracheque, afastamentos, férias |
| Ponto / frequência | ❌ Pendente Crítico | Não implementado |
| DIRF / declarações fiscais | ❌ Pendente Crítico | Não implementado |
| Controle de férias | ⚠️ Atende Parcialmente | `Absence` existe; gestão de escala de férias ausente |

---

### 1.7 Protocolo e Gestão de Documentos

| Item | Status | Observação |
|---|---|---|
| Protocolo de documentos/processos | ✅ Atende | `Protocolo` com tramitação entre departamentos |
| Tramitação com histórico | ✅ Atende | `TramitacaoProtocolo` com responsável e data |
| Status e prazo | ✅ Atende | Campo status + controle de datas |
| Gestão documental (GED) avançada | ❌ Pendente Crítico | Sem upload de arquivos; sem versionamento |

---

### 1.8 Convênios

| Item | Status | Observação |
|---|---|---|
| Cadastro de convênios | ✅ Atende | Com concedente, valor, vigência, situação |
| Parcelas e prestações de contas | ✅ Atende | `ParcelaConvenio`, `PrestacaoContas` |
| Histórico de status | ✅ Atende | Transições auditadas |
| Portal de consulta pública | ⚠️ Atende Parcialmente | Não exposto no frontend público |

---

### 1.9 Tributação Municipal

| Item | Status | Observação |
|---|---|---|
| IPTU (cadastro de imóveis, alíquotas) | ✅ Atende | `Imovel`, `LancamentoTributario`, `AliquotaIPTU` |
| Parcelamento de dívida ativa | ✅ Atende | `ParcelamentoDivida` com parcelas e controle de inadimplência |
| ISS / ISSQN | ✅ Atende | `NotaFiscalServico` com emissão, cancelamento, cálculo ISS automático e `LancamentoTributario` gerado |
| ITBI | ✅ Atende | `OperacaoITBI` com base de cálculo (max declarado/venal), alíquota configurável, `LancamentoTributario` gerado |
| Nota Fiscal de Serviços Eletrônica (NFS-e) | ✅ Atende (simplificado) | NFS-e interna com emissão, cancelamento, ISS calculado, dashboard, CSV; sem integração SEFAZ |
| Dívida ativa — ajuizamento | ⚠️ Atende Parcialmente | Campo `status=ajuizada` existe; integração PGM ausente |

---

### 1.10 Contabilidade

| Item | Status | Observação |
|---|---|---|
| Empenho / Liquidação / Pagamento | ✅ Atende | Ciclo completo implementado |
| Receitas | ✅ Atende | `RevenueEntry` com arrecadação |
| Exercício fiscal | ✅ Atende | `FiscalYear` com abertura/encerramento |
| Plano de Contas (PCASP) | ⚠️ Atende Parcialmente | Estrutura presente mas sem validação do PCASP formal |
| Balancetes e Demonstrações (RREO/RGF) | ✅ Atende | RREO e RGF implementados via `/lrf/rreo` e `/lrf/rgf` com CSV |
| Conciliação bancária | ❌ Pendente Crítico | Não implementada |
| SICONFI / SIOP (integração federal) | ❌ Pendente Crítico | Não implementada |

---

## 2. Requisitos Transversais

| Requisito | Status | Observação |
|---|---|---|
| Autenticação JWT com expiração | ✅ Atende | `python-jose` com renovação |
| Controle de perfis (RBAC) | ✅ Atende | `RoleEnum`: admin, accountant, procurement, hr, patrimony, read_only |
| Auditoria de operações (`audit_logs`) | ✅ Atende | `write_audit` em todas as operações de escrita principais |
| Paginação nas listagens | ✅ Atende | Padrão `{total, page, size, items}` |
| Filtros nas listagens | ✅ Atende | Todos os endpoints de listagem têm filtros relevantes |
| Exportação CSV | ✅ Atende | Almoxarifado, Frota, Relatórios |
| Multi-tenancy | ❌ Pendente Crítico | Isolamento por município não implementado |
| Criptografia em repouso | ⚠️ Atende Parcialmente | Senhas com bcrypt; dados sensíveis não criptografados |
| Log de acesso | ⚠️ Atende Parcialmente | Auditoria de operações existe; log de login/sessão não |
| API REST documentada | ✅ Atende | Swagger/OpenAPI automático via FastAPI em `/docs` |
| Testes automatizados | ✅ Atende | 163 testes cobrindo todos os módulos principais |
| Migration com Alembic | ✅ Atende | 9 migrations ordenadas e reversíveis |

---

## 3. Resumo Executivo

| Categoria | Atende | Parcial | Pendente Crítico |
|---|:---:|:---:|:---:|
| Orçamento (PPA/LDO/LOA) | 4 | 2 | 0 |
| Compras / Licitações | 7 | 2 | 0 |
| Almoxarifado | 8 | 0 | 0 |
| Patrimônio | 3 | 1 | 2 |
| Frota | 7 | 0 | 2 |
| Recursos Humanos | 4 | 1 | 3 |
| Protocolo | 3 | 0 | 1 |
| Convênios | 3 | 1 | 0 |
| Tributação | 3 | 2 | 3 |
| Contabilidade | 3 | 1 | 4 |
| Requisitos Transversais | 8 | 3 | 3 |
| **Total** | **53** | **13** | **18** |

**Taxa de aderência estimada: ~62% plena / ~77% incluindo parciais.**

---

## 4. Pendentes Críticos Priorizados

| Prioridade | Item | Impacto |
|---|---|---|
| ~~🔴 Alta~~ ✅ | ~~RREO / RGF / Demonstrações contábeis~~ **Implementado** | RREO e RGF disponíveis em `/lrf/rreo` e `/lrf/rgf` |
| ~~🔴 Alta~~ ✅ | ~~Conciliação bancária~~ **Implementado** | Contas, lançamentos, conciliação auto/manual, dashboard, CSV |
| ~~🔴 Alta~~ ✅ | ~~NFS-e / ITBI~~ **Implementado** | NFS-e simplificada, ITBI com base de cálculo, dashboard, CSV, integração tributária |
| 🔴 Alta | Ponto / frequência de servidores | Vinculado a folha; impacta legalidade da remuneração |
| 🟡 Média | Depreciação patrimonial (NBCASP) | Exigência IPSAS/NBCASP — impacta balanço patrimonial |
| 🟡 Média | L/100km e alertas preventivos de frota | Ganho operacional; não bloqueia conformidade |
| 🟡 Média | SICONFI / SIOP | Obrigação de prestação de contas ao governo federal |
| 🟠 Baixa | Multi-tenancy | Necessário se o sistema for vendido como SaaS para múltiplos municípios |

---

## 5. Conclusão (atualizado após onda 13)

O sistema **pode ser demonstrado como aderente de forma parcial e sólida** para os módulos de:
- ✅ Compras, Licitações e Almoxarifado (praticamente completos)
- ✅ Frota (completo e integrado)
- ✅ Orçamento (PPA/LDO/LOA)
- ✅ RH, Protocolo e Convênios (funcionais)
- ✅ **Demonstrativos LRF (RREO e RGF)** — implementados na onda 11
- ✅ **Conciliação bancária** — implementada na onda 12
- ✅ **NFS-e e ITBI** — implementados na onda 13 (ISS, ITBI, dashboard, CSV, integração tributária)

**Ainda não pode ser defendido como integralmente aderente** sem ponto/frequência de servidores e depreciação patrimonial (NBCASP).

**Próximo passo ideal:** ponto/frequência de servidores — vinculado à folha de pagamento e impacta diretamente a legalidade da remuneração (RBGF, instrução normativa TCE).
Alternativa: depreciação patrimonial, que fecha a conformidade com NBCASP/IPSAS no balanço.

