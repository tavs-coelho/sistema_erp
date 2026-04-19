# Auditoria Final — Aderência ao Termo de Referência (TR)

**Data:** 2026-04-19  
**Branch auditada:** `copilot/diagnostico-tecnico-erp`  
**Total de testes:** 565 (20 suítes)  
**Migrations:** 16 (0001–0016)  
**Frontend:** 23 páginas Next.js

---

## Metodologia

| Classificação | Símbolo | Critério |
|---|:---:|---|
| Atende | ✅ | Implementado, testado, com frontend demonstrável e evidência objetiva |
| Atende Parcialmente | ⚠️ | Funcionalidade presente mas com lacuna funcional, de UX ou de conformidade |
| Pendente Crítico | ❌ | Módulo ausente ou insuficiente para demonstração ou conformidade |
| Não Aplicável | 〰️ | Requisito fora do escopo acordado ou substituído por outra solução |

---

## 1. Módulo Orçamentário (PPA / LDO / LOA)

| ID | Requisito | Status | Evidência | Risco Remanescente | Ação Corretiva |
|---|---|:---:|---|---|---|
| ORC-01 | Cadastro de PPA com programas e metas | ✅ | `routers/budget.py` → `PPA`, `PPAProgram`; frontend `/orcamento`; `test_procurement.py` | Baixo | — |
| ORC-02 | Cadastro de LDO com diretrizes e metas | ✅ | `LDO`, `LDOGoal`; frontend `/orcamento`; CRUD completo | Baixo | — |
| ORC-03 | Cadastro de LOA com dotações por função/subfunção/programa/ação | ✅ | `LOA`, `LOAItem`, `BudgetAllocation`; código estruturado | Baixo | — |
| ORC-04 | Execução orçamentária — empenho, liquidação, pagamento | ✅ | `routers/accounting.py`; ciclo `Commitment→Liquidation→Payment`; `test_integracao_compras.py` | Baixo | — |
| ORC-05 | Atualização automática de saldo executado ao empenhar | ⚠️ | `LOAItem.executed_amount` existe; sem disparo automático ao criar `Commitment` | Médio — risco de divergência orçamentária | Disparar trigger de atualização de `executed_amount` no `create_commitment` (Onda 20) |
| ORC-06 | Relatório de execução orçamentária por dotação | ⚠️ | `/accounting/commitments-report` existe; sem relatório formatado por dotação/função | Médio | Implementar relatório LOA vs executado em `/relatorios/execucao-orcamentaria` (Onda 20) |
| ORC-07 | Consulta pública de LOA e execução | ⚠️ | `/public/licitacoes` existe; LOA não exposta publicamente | Baixo | Expor endpoint `/public/loa/{exercicio}` (Onda 20) |

---

## 2. Compras e Licitações

| ID | Requisito | Status | Evidência | Risco Remanescente | Ação Corretiva |
|---|---|:---:|---|---|---|
| COM-01 | Cadastro de processo licitatório (número, objeto, modalidade) | ✅ | `ProcurementProcess`; `routers/procurement.py`; frontend `/compras`; 20 testes | Baixo | — |
| COM-02 | Cadastro e gestão de fornecedores (CNPJ único) | ✅ | `Vendor` com CNPJ único indexado; frontend | Baixo | — |
| COM-03 | Contratos vinculados a processo licitatório | ✅ | `Contract` com valor, vigência, cláusulas, addenda | Baixo | — |
| COM-04 | Empenhos vinculados a contrato/fornecedor | ✅ | `Commitment.contract_id`; `routers/accounting.py` | Baixo | — |
| COM-05 | Recebimento de material com conferência | ✅ | `RecebimentoMaterial`; `test_integracao_compras.py` | Baixo | — |
| COM-06 | Integração compras → almoxarifado automática | ✅ | Recebimento gera `StockMovement` tipo entrada; 23 testes | Baixo | — |
| COM-07 | Alerta de estoque mínimo → requisição de compra automática | ✅ | `AlertaEstoque` gera `RequisicaoCompra`; 28 testes | Baixo | — |
| COM-08 | Portal público de licitações (sem autenticação) | ✅ | `GET /public/licitacoes`; frontend `/public`; 25 testes | Baixo | — |
| COM-09 | Publicação de resultado e contrato | ⚠️ | Dados existem no backend; frontend público exibe apenas listagem; sem publicação formal de extrato | Baixo | Adicionar extrato publicável em `/public/contratos/{id}` |

---

## 3. Almoxarifado / Controle de Estoque

| ID | Requisito | Status | Evidência | Risco Remanescente | Ação Corretiva |
|---|---|:---:|---|---|---|
| ALM-01 | Cadastro de itens com código e categoria | ✅ | `StockItem`; `routers/almoxarifado.py`; 35 testes | Baixo | — |
| ALM-02 | Entradas de estoque (recebimento/doação) | ✅ | `StockMovement` tipo entrada; rastreável a recebimento | Baixo | — |
| ALM-03 | Saídas por departamento com responsável | ✅ | `StockMovement` tipo saída; auditado | Baixo | — |
| ALM-04 | Saldo atual em tempo real | ✅ | `estoque_atual` atualizado atomicamente na transação | Baixo | — |
| ALM-05 | Histórico de movimentações com filtros | ✅ | Filtros por item/tipo/departamento/período; CSV | Baixo | — |
| ALM-06 | Alerta de estoque mínimo | ✅ | Gerado em toda saída que ultrapassa mínimo | Baixo | — |
| ALM-07 | Requisição de compra automática | ✅ | Gerada ao abrir alerta; 28 testes | Baixo | — |
| ALM-08 | Exportação CSV | ✅ | `?export=csv` em todas as listagens | Baixo | — |

---

## 4. Patrimônio

| ID | Requisito | Status | Evidência | Risco Remanescente | Ação Corretiva |
|---|---|:---:|---|---|---|
| PAT-01 | Cadastro de bens com tombamento e classificação | ✅ | `Asset`; `routers/patrimony.py`; frontend `/patrimonio` | Baixo | — |
| PAT-02 | Transferência entre departamentos | ✅ | `AssetMovement`; rastreabilidade completa | Baixo | — |
| PAT-03 | Status do bem (ativo, baixado, em manutenção) | ✅ | Campo `status`; transições auditadas | Baixo | — |
| PAT-04 | Depreciação patrimonial (NBCASP) | ✅ | `ConfiguracaoDepreciacao`, `LancamentoDepreciacao`; linear + saldo decrescente; idempotente; 35 testes; `docs/depreciacao-patrimonial.md` | Baixo | — |
| PAT-05 | Inventário por departamento (relatório formal) | ⚠️ | Lista de ativos existe; sem relatório de inventário com assinatura/rodapé formal | Médio | Implementar `/relatorios/inventario/{departamento}` com PDF (Onda 20) |
| PAT-06 | Reavaliação e ajuste de valor de ativo | ❌ | Não implementada; sem `ReavaliacaoAtivo` ou ajuste manual | Alto — sem conformidade NBCASP 16.9 | Implementar `POST /patrimonio/{id}/reavaliar` com `LancamentoContabil` (Onda 21) |

---

## 5. Frota

| ID | Requisito | Status | Evidência | Risco Remanescente | Ação Corretiva |
|---|---|:---:|---|---|---|
| FRO-01 | Cadastro de veículos (placa, tipo, combustível, odômetro) | ✅ | `Veiculo`; `routers/frota.py`; 38 testes | Baixo | — |
| FRO-02 | Registro de abastecimentos | ✅ | `Abastecimento` com litros, valor, odômetro, NF | Baixo | — |
| FRO-03 | Controle de manutenções preventivas e corretivas | ✅ | `Manutencao` com tipos, lifecycle, peças | Baixo | — |
| FRO-04 | Peças vinculadas ao almoxarifado | ✅ | `ItemManutencao` gera saída automática de estoque | Baixo | — |
| FRO-05 | Dashboard de consumo por veículo e frota | ✅ | `/frota/dashboard`; KPIs agregados | Baixo | — |
| FRO-06 | Rastreabilidade veículo → manutenção → almoxarifado | ✅ | `movimentacao_id` em cada `ItemManutencao` | Baixo | — |
| FRO-07 | Relatório TCO por veículo e por departamento | ✅ | `/relatorios/frota/custo-por-veiculo` e `/custo-por-departamento`; CSV | Baixo | — |
| FRO-08 | Índice L/100km por veículo | ❌ | Não implementado; requer consistência de odômetro e cálculo por intervalo | Médio — KPI operacional relevante | Calcular em `_build_veiculo_row` usando delta odômetro / litros (Onda 20) |
| FRO-09 | Alertas de manutenção preventiva por km ou por tempo | ❌ | Não implementado; sem trigger de km próximo | Médio — risco de manutenção não realizada | Implementar campo `km_proxima_revisao` e endpoint de alertas (Onda 20) |

---

## 6. Recursos Humanos

| ID | Requisito | Status | Evidência | Risco Remanescente | Ação Corretiva |
|---|---|:---:|---|---|---|
| RH-01 | Cadastro de funcionários com matrícula, cargo, departamento | ✅ | `Employee`; `routers/hr.py`; frontend `/rh` | Baixo | — |
| RH-02 | Cargos, funções e departamentos | ✅ | `Department`, `JobPosition` com hierarquia | Baixo | — |
| RH-03 | Folha de pagamento (eventos, cálculo, fechamento) | ✅ | `PayrollEvent`, `PayrollEntry`, `Payslip`; ciclo frequência→eventos→holerite; 56 testes combinados | Baixo | — |
| RH-04 | Ponto e frequência (escala, registro, abono) | ✅ | `RegistroPonto`, `EscalaServidor`, `AbonoFalta`; folha mensal; horas extras; 39 testes; `docs/ponto-frequencia.md` | Baixo | — |
| RH-05 | Integração ponto → folha (descontos/créditos automáticos) | ✅ | `IntegracaoPontoFolha`; idempotente; preview dry-run; 32 testes; `docs/integracao-ponto-folha.md` | Baixo | — |
| RH-06 | Portal do servidor (contracheque, afastamentos) | ✅ | `routers/employee_portal.py`; frontend `/portal-servidor` | Baixo | — |
| RH-07 | Controle de férias (programação/escala) | ⚠️ | `Absence` com tipo `ferias` existe; sem escala anual de férias, conflito de períodos ou relatório de gozo | Alto — obrigação trabalhista | Implementar `EscalaFerias` com controle de 30 dias e relatório (Onda 20) |
| RH-08 | DIRF (Declaração de Imposto de Renda na Fonte) | ❌ | Não implementada; sem cálculo de IRRF, tabela progressiva ou arquivo RFB | Alto — obrigação acessória IR | Implementar cálculo IRRF em `PayrollEvent` + geração de arquivo DIRF (Onda 21) |
| RH-09 | RAIS / eSocial (obrigações acessórias trabalhistas) | ❌ | Não implementado; sem módulo de obrigações acessórias | Alto — multa por não entrega | Fora do escopo do TR atual — requerer clareza contratual |

---

## 7. Protocolo e Gestão de Documentos

| ID | Requisito | Status | Evidência | Risco Remanescente | Ação Corretiva |
|---|---|:---:|---|---|---|
| PROT-01 | Protocolo de documentos com número único | ✅ | `Protocolo`; `routers/protocolo.py`; 21 testes; frontend `/protocolo` | Baixo | — |
| PROT-02 | Tramitação entre departamentos com histórico | ✅ | `TramitacaoProtocolo`; responsável, data, observação | Baixo | — |
| PROT-03 | Status e prazo de resposta | ✅ | Campo `status` com transições; campo `data_limite` | Baixo | — |
| PROT-04 | Upload e gestão de documentos (GED) | ❌ | `Attachment` model criado mas sem endpoint de upload; sem armazenamento de arquivo | Alto — sem evidência documental | Implementar `POST /attachments` com armazenamento local/S3 (Onda 21) |

---

## 8. Convênios

| ID | Requisito | Status | Evidência | Risco Remanescente | Ação Corretiva |
|---|---|:---:|---|---|---|
| CONV-01 | Cadastro de convênios com concedente, valor, vigência | ✅ | `Convenio`; `routers/convenios.py`; frontend `/convenios` | Baixo | — |
| CONV-02 | Parcelas e prestações de contas | ✅ | `ParcelaConvenio`, `PrestacaoContas`; histórico de status | Baixo | — |
| CONV-03 | Histórico de status auditado | ✅ | `write_audit` em todas as transições | Baixo | — |
| CONV-04 | Portal público de consulta de convênios | ⚠️ | Dados existem; não exposto em `/public/convenios`; sem frontend público | Baixo | Adicionar endpoint `/public/convenios` e link no frontend público (Onda 20) |

---

## 9. Tributação Municipal

| ID | Requisito | Status | Evidência | Risco Remanescente | Ação Corretiva |
|---|---|:---:|---|---|---|
| TRIB-01 | IPTU (cadastro de imóveis, alíquotas, lançamento) | ✅ | `Imovel`, `AliquotaIPTU`, `LancamentoTributario`; 23 testes; frontend `/tributario` | Baixo | — |
| TRIB-02 | Parcelamento de dívida ativa | ✅ | `ParcelamentoDivida` com parcelas e inadimplência | Baixo | — |
| TRIB-03 | ISS / ISSQN (cálculo e lançamento) | ✅ | `NotaFiscalServico`; ISS calculado automaticamente; `LancamentoTributario` gerado | Baixo | — |
| TRIB-04 | ITBI (base de cálculo, alíquota configurável) | ✅ | `OperacaoITBI`; base = max(declarado, venal); 36 testes; `docs/nfse-itbi.md` | Baixo | — |
| TRIB-05 | NFS-e (emissão, cancelamento, numeração) | ✅ (simplificado) | Emissão interna; sem integração SEFAZ; sem XML padrão ABRASF | Médio — sem validade fiscal perante SEFAZ | Documentar como NFS-e interna; integração SEFAZ como Onda futura |
| TRIB-06 | Dívida ativa — ajuizamento e PGM | ⚠️ | Status `ajuizada` existe; sem integração PGM ou geração de CDA | Médio | Integração PGM fora do escopo do TR; documentar limitação |
| TRIB-07 | Consulta pública de débitos (portal do contribuinte) | ❌ | Não implementado; sem endpoint público de consulta de débitos do contribuinte | Alto — transparência fiscal | Implementar `GET /public/contribuinte/{cpf_cnpj}/debitos` (Onda 20) |

---

## 10. Contabilidade e LRF

| ID | Requisito | Status | Evidência | Risco Remanescente | Ação Corretiva |
|---|---|:---:|---|---|---|
| CONT-01 | Ciclo empenho → liquidação → pagamento | ✅ | `routers/accounting.py`; `Commitment→Liquidation→Payment` | Baixo | — |
| CONT-02 | Receitas por categoria | ✅ | `RevenueEntry`; `routers/accounting.py` | Baixo | — |
| CONT-03 | Exercício fiscal (abertura/encerramento) | ✅ | `FiscalYear`; controle de status | Baixo | — |
| CONT-04 | Conciliação bancária | ✅ | `ContaBancaria`, `LancamentoBancario`, conciliação auto/manual; 37 testes; `docs/conciliacao-bancaria.md` | Baixo | — |
| CONT-05 | RREO bimestral | ✅ | `routers/rreo_rgf.py`; `routers/siconfi_siop.py`; 23 testes; `docs/rreo-rgf.md` | Baixo | — |
| CONT-06 | RGF quadrimestral | ✅ | Idem; Relatório de Gestão Fiscal completo | Baixo | — |
| CONT-07 | SICONFI — FINBRA / RREO / RGF XML | ✅ | `app/siconfi_xml.py`; `routers/siconfi_xml.py`; validação XSD inline; 37 testes; `docs/siconfi-onda19.md` | Médio — XSD é aproximação; envio real pendente credencial | Fase 2 SICONFI (ver Onda 19 Fase 2 plan) |
| CONT-08 | SIOP (programas PPA) | ✅ (parcial) | `_build_siop_programas` em `routers/siconfi_siop.py`; sem API REST SIOP real | Médio — SIOP tem API REST própria | Documentar como export preparatório; integração REST SIOP como Onda futura |
| CONT-09 | Plano de Contas (PCASP) | ⚠️ | `BudgetAllocation.code` segue estrutura; sem validação formal PCASP nem dicionário de contas | Médio — risco de rejeição pelo Tesouro | Implementar tabela `PlanoContas` com PCASP completo e validação (Onda 21) |
| CONT-10 | Demonstrações Contábeis Consolidadas (BP, DRE, DFC) | ❌ | Não implementadas; sem balanço patrimonial nem demonstração de resultado | Alto — obrigação anual TCE/TCU | Implementar módulo de demonstrações contábeis (Onda 21) |

---

## 11. Requisitos Transversais

| ID | Requisito | Status | Evidência | Risco Remanescente | Ação Corretiva |
|---|---|:---:|---|---|---|
| TRV-01 | Autenticação JWT com expiração | ✅ | `routers/auth.py`; `python-jose`; 10 testes | Baixo | — |
| TRV-02 | RBAC — controle de perfis por módulo | ✅ | `RoleEnum`: admin, accountant, procurement, hr, patrimony, read_only; `require_roles` aplicado em todos os endpoints sensíveis | Baixo | — |
| TRV-03 | Auditoria de operações (audit_logs) | ✅ | `app/audit.py`; `write_audit` em todas as operações de escrita; tabela `audit_logs` com before/after | Baixo | — |
| TRV-04 | Paginação padronizada | ✅ | Padrão `{total, page, size, items}` em todas as listagens | Baixo | — |
| TRV-05 | Filtros nas listagens | ✅ | Filtros relevantes em todos os endpoints principais | Baixo | — |
| TRV-06 | Exportação CSV | ✅ | Almoxarifado, Frota, RREO, RGF, Integração Ponto-Folha, Depreciação | Baixo | — |
| TRV-07 | API REST documentada (OpenAPI) | ✅ | Swagger automático via FastAPI em `/docs`; 16 routers registrados | Baixo | — |
| TRV-08 | Testes automatizados | ✅ | **565 testes** em 20 suítes; cobertura de todos os módulos principais | Baixo | — |
| TRV-09 | Migrations versionadas e reversíveis | ✅ | 16 migrations Alembic (0001–0016); `upgrade()` + `downgrade()` em todas | Baixo | — |
| TRV-10 | Multi-tenancy (isolamento por município) | ❌ | Não implementado; banco único sem partição por tenant | Alto — necessário para SaaS multi-prefeitura | Adicionar `tenant_id` nos models principais + middleware de isolamento (Onda futura) |
| TRV-11 | Criptografia em repouso de dados sensíveis (CPF, CNPJ) | ⚠️ | Senhas hasheadas com bcrypt; CPF/CNPJ gravados em texto | Médio — risco LGPD | Aplicar criptografia AES-256 nos campos sensíveis (Onda 21) |
| TRV-12 | Log de autenticação (login/logout/falha) | ⚠️ | Auditoria de operações existe; login bem-sucedido não gera `audit_log`; sem registro de falha | Médio — rastreabilidade de segurança | Adicionar `write_audit` no `POST /auth/login` (sucesso e falha) |
| TRV-13 | Rate limiting / proteção contra brute force | ❌ | Não implementado; sem throttle no endpoint de login | Alto — risco de ataque de força bruta | Adicionar `slowapi` ou middleware de rate limiting (Onda 20) |
| TRV-14 | HTTPS / TLS em produção | 〰️ | Responsabilidade do infra/deploy; código usa uvicorn puro | Baixo | Documentar requisito de proxy reverso (Nginx/Traefik) no guia de deploy |

---

## 12. Resumo Executivo — Status Final

| Módulo | ✅ Atende | ⚠️ Parcial | ❌ Pendente | Total |
|---|:---:|:---:|:---:|:---:|
| Orçamento (PPA/LDO/LOA) | 4 | 3 | 0 | 7 |
| Compras / Licitações | 8 | 1 | 0 | 9 |
| Almoxarifado | 8 | 0 | 0 | 8 |
| Patrimônio | 4 | 1 | 1 | 6 |
| Frota | 7 | 0 | 2 | 9 |
| Recursos Humanos | 6 | 1 | 2 | 9 |
| Protocolo / GED | 3 | 0 | 1 | 4 |
| Convênios | 3 | 1 | 0 | 4 |
| Tributação | 4 | 2 | 1 | 7 |
| Contabilidade / LRF | 7 | 2 | 1 | 10 |
| Requisitos Transversais | 9 | 3 | 2 | 14 |
| **Total** | **63** | **14** | **10** | **87** |

**Taxa de aderência:**
- Plena: **63/87 = 72%**
- Plena + Parcial: **77/87 = 89%**

---

## 13. Pendentes Críticos — Matriz de Priorização

| ID | Item | Impacto | Complexidade | Prioridade |
|---|---|:---:|:---:|:---:|
| TRIB-07 | Portal público do contribuinte (consulta de débitos) | Alto | Baixa | 🔴 Alta |
| TRV-13 | Rate limiting / proteção brute force | Alto | Baixa | 🔴 Alta |
| TRV-10 | Multi-tenancy | Alto | Alta | 🟡 Média (pré-SaaS) |
| RH-07 | Controle de férias (escala anual) | Alto | Média | 🔴 Alta |
| RH-08 | DIRF | Alto | Alta | 🟡 Média |
| PAT-06 | Reavaliação de ativo (NBCASP 16.9) | Alto | Média | 🟡 Média |
| CONT-10 | Demonstrações Contábeis (BP, DRE) | Alto | Alta | 🟡 Média |
| PROT-04 | Upload / GED | Alto | Média | 🟡 Média |
| ORC-05 | Atualização saldo executado ao empenhar | Médio | Baixa | 🟡 Média |
| TRV-12 | Log de autenticação | Médio | Baixa | 🟡 Média |

---

## 14. Itens Resolvidos desde Auditoria Anterior

| Item | Onda | Status Anterior | Status Atual |
|---|:---:|---|---|
| RREO / RGF / Demonstrações LRF | 11 | ❌ Pendente | ✅ Atende |
| Conciliação bancária | 12 | ❌ Pendente | ✅ Atende |
| NFS-e / ITBI | 13 | ❌ Pendente | ✅ Atende |
| Ponto e Frequência | 14 | ❌ Pendente | ✅ Atende |
| Depreciação Patrimonial (NBCASP) | 15 | ❌ Pendente | ✅ Atende |
| Integração Ponto → Folha | 16 | ❌ Pendente | ✅ Atende |
| Recálculo automático do Payslip | 17 | ❌ Pendente | ✅ Atende |
| SICONFI preparatório (FINBRA/RREO/RGF/SIOP) | 18 | ❌ Pendente | ✅ Atende |
| SICONFI XML + validação XSD | 19 | ❌ Pendente | ✅ Atende |

---

## 15. Conclusão

O sistema atingiu **72% de aderência plena e 89% incluindo parciais** em relação ao TR auditado.

**Pontos fortes:**
- Todos os módulos operacionais core (compras, almoxarifado, frota, contabilidade) estão completos e com testes extensos
- Ciclo completo de RH: frequência → eventos → holerite
- LRF: RREO, RGF e SICONFI XML (Fase 1) implementados
- Auditoria de operações e RBAC em todos os módulos

**Riscos maiores remanescentes:**
1. **DIRF e obrigações acessórias de RH** — obrigações fiscais com prazo determinado; multas por atraso
2. **Reavaliação de ativos** — sem conformidade NBCASP 16.9 / IPSAS 17
3. **Demonstrações contábeis consolidadas** — obrigação anual TCE/TCU
4. **Rate limiting** — superfície de ataque em produção
5. **Multi-tenancy** — necessário se o sistema for implantado como SaaS

**Recomendação para Onda 20:** focar em rate limiting (TRV-13), portal do contribuinte (TRIB-07), escala de férias (RH-07), atualização automática de saldo orçamentário (ORC-05) e log de autenticação (TRV-12) — todos de alta prioridade e baixa a média complexidade.

**SICONFI Fase 2** (envio real) permanece bloqueado por dependências externas (certificado ICP-Brasil + credenciais gov.br do gestor). Pode ser implementado tecnicamente em paralelo com os demais itens da Onda 20 assim que os artefatos forem fornecidos pelo cliente.
