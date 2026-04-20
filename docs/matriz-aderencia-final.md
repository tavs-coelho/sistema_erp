# Matriz de Aderência Final — Sistema ERP Municipal

**Versão:** pós-Sprint Aderência  
**Data de congelamento:** 2026-04-19  
**Aderência plena:** 69/87 = **79%**  
**Aderência plena + parcial:** 78/87 = **90%**

---

## 1. Visão Geral por Módulo

| Módulo | Itens | ✅ Atende | ⚠️ Parcial | ❌ Pendente | % Plena |
|---|:---:|:---:|:---:|:---:|:---:|
| Orçamento (PPA/LDO/LOA) | 7 | 5 | 2 | 0 | 71% |
| Compras / Licitações | 9 | 8 | 1 | 0 | 89% |
| Almoxarifado | 8 | 8 | 0 | 0 | **100%** |
| Patrimônio | 6 | 4 | 1 | 1 | 67% |
| Frota | 9 | 7 | 0 | 2 | 78% |
| Recursos Humanos | 9 | 7 | 0 | 2 | 78% |
| Protocolo / GED | 4 | 4 | 0 | 0 | **100%** |
| Convênios | 4 | 3 | 1 | 0 | 75% |
| Tributação Municipal | 7 | 5 | 1 | 1 | 71% |
| Contabilidade / LRF | 10 | 7 | 2 | 1 | 70% |
| Requisitos Transversais | 14 | 11 | 1 | 2 | 79% |
| **TOTAL** | **87** | **69** | **9** | **9** | **79%** |

---

## 2. Itens com Status ✅ Atende (69)

### Módulo Orçamentário
| ID | Requisito |
|---|---|
| ORC-01 | Cadastro de PPA com programas e metas |
| ORC-02 | Cadastro de LDO com diretrizes e metas |
| ORC-03 | Cadastro de LOA com dotações por função/subfunção/programa/ação |
| ORC-04 | Execução orçamentária — empenho, liquidação, pagamento |
| ORC-05 | Atualização automática de saldo executado ao empenhar *(Sprint Aderência)* |

### Compras e Licitações
| ID | Requisito |
|---|---|
| COM-01 | Cadastro de processo licitatório |
| COM-02 | Cadastro e gestão de fornecedores (CNPJ único) |
| COM-03 | Contratos vinculados a processo licitatório |
| COM-04 | Empenhos vinculados a contrato/fornecedor |
| COM-05 | Recebimento de material com conferência |
| COM-06 | Integração compras → almoxarifado automática |
| COM-07 | Alerta de estoque mínimo → requisição automática |
| COM-08 | Portal público de licitações (sem autenticação) |

### Almoxarifado / Controle de Estoque
| ID | Requisito |
|---|---|
| ALM-01 | Cadastro de itens com código e categoria |
| ALM-02 | Entradas de estoque |
| ALM-03 | Saídas por departamento com responsável |
| ALM-04 | Saldo atual em tempo real |
| ALM-05 | Histórico de movimentações com filtros |
| ALM-06 | Alerta de estoque mínimo |
| ALM-07 | Requisição de compra automática |
| ALM-08 | Exportação CSV |

### Patrimônio
| ID | Requisito |
|---|---|
| PAT-01 | Cadastro de bens com tombamento |
| PAT-02 | Transferência entre departamentos |
| PAT-03 | Status do bem |
| PAT-04 | Depreciação patrimonial (NBCASP) |

### Frota
| ID | Requisito |
|---|---|
| FRO-01 | Cadastro de veículos |
| FRO-02 | Registro de abastecimentos |
| FRO-03 | Controle de manutenções preventivas e corretivas |
| FRO-04 | Peças vinculadas ao almoxarifado |
| FRO-05 | Dashboard de consumo por veículo e frota |
| FRO-06 | Rastreabilidade veículo → manutenção → almoxarifado |
| FRO-07 | Relatório TCO por veículo e por departamento |

### Recursos Humanos
| ID | Requisito |
|---|---|
| RH-01 | Cadastro de funcionários |
| RH-02 | Cargos, funções e departamentos |
| RH-03 | Folha de pagamento |
| RH-04 | Ponto e frequência |
| RH-05 | Integração ponto → folha |
| RH-06 | Portal do servidor |
| RH-07 | Controle de férias (escala anual) *(Sprint Aderência)* |

### Protocolo / GED
| ID | Requisito |
|---|---|
| PROT-01 | Protocolo de documentos com número único |
| PROT-02 | Tramitação entre departamentos |
| PROT-03 | Status e prazo de resposta |
| PROT-04 | Upload e gestão de documentos (GED) *(Sprint Aderência)* |

### Convênios
| ID | Requisito |
|---|---|
| CONV-01 | Cadastro de convênios |
| CONV-02 | Parcelas e prestações de contas |
| CONV-03 | Histórico de status auditado |

### Tributação Municipal
| ID | Requisito |
|---|---|
| TRIB-01 | IPTU |
| TRIB-02 | Parcelamento de dívida ativa |
| TRIB-03 | ISS / ISSQN |
| TRIB-04 | ITBI |
| TRIB-07 | Portal do contribuinte *(Sprint Aderência)* |

### Contabilidade / LRF
| ID | Requisito |
|---|---|
| CONT-01 | Ciclo empenho → liquidação → pagamento |
| CONT-02 | Receitas por categoria |
| CONT-03 | Exercício fiscal |
| CONT-04 | Conciliação bancária |
| CONT-05 | RREO bimestral |
| CONT-06 | RGF quadrimestral |
| CONT-07 | SICONFI — FINBRA / RREO / RGF XML |

### Requisitos Transversais
| ID | Requisito |
|---|---|
| TRV-01 | Autenticação JWT |
| TRV-02 | RBAC por módulo |
| TRV-03 | Auditoria de operações |
| TRV-04 | Paginação padronizada |
| TRV-05 | Filtros nas listagens |
| TRV-06 | Exportação CSV |
| TRV-07 | API REST documentada (OpenAPI) |
| TRV-08 | Testes automatizados (592 testes) |
| TRV-09 | Migrations versionadas |
| TRV-12 | Log de autenticação *(Sprint Aderência)* |
| TRV-13 | Rate limiting / brute force *(Sprint Aderência)* |

---

## 3. Itens com Status ⚠️ Atende Parcialmente (9)

| ID | Módulo | Lacuna | Impacto no Edital | Esforço |
|---|---|---|:---:|:---:|
| ORC-06 | Orçamento | Relatório LOA vs executado formatado por dotação | Médio | Baixo |
| ORC-07 | Orçamento | LOA não exposta publicamente em `/public` | Baixo | Baixo |
| COM-09 | Compras | Publicação formal de extrato de resultado | Baixo | Baixo |
| PAT-05 | Patrimônio | Inventário formal com assinatura/rodapé PDF | Médio | Baixo |
| CONV-04 | Convênios | Portal público `/public/convenios` | Baixo | Baixo |
| TRIB-05 | Tributação | NFS-e interna sem integração SEFAZ | Médio | Alto |
| TRIB-06 | Tributação | Dívida ativa sem integração PGM/CDA | Médio | Alto |
| CONT-09 | Contabilidade | Plano de Contas PCASP sem validação formal | Médio | Alto |
| TRV-11 | Transversal | CPF/CNPJ em texto; sem criptografia em repouso (LGPD) | Médio | Médio |

---

## 4. Itens com Status ❌ Pendente (9)

| ID | Módulo | Descrição | Impacto no Edital | Esforço | Risco Impl. |
|---|---|---|:---:|:---:|:---:|
| FRO-08 | Frota | Índice L/100km por veículo | Baixo | Baixo | Baixo |
| FRO-09 | Frota | Alertas manutenção preventiva por km/tempo | Médio | Baixo | Baixo |
| PAT-06 | Patrimônio | Reavaliação de ativo (NBCASP 16.9) | Alto | Médio | Médio |
| RH-08 | RH | DIRF (cálculo IRRF + arquivo RFB) | Alto | Alto | Alto |
| RH-09 | RH | RAIS / eSocial | Alto | Alto | Alto |
| CONT-10 | Contabilidade | Demonstrações Contábeis (BP, DRE, DFC) | Alto | Alto | Alto |
| TRV-10 | Transversal | Multi-tenancy (isolamento por município) | Alto | Alto | Alto |
| CONT-08* | Contabilidade | SIOP API REST real (integração gov.br) | Médio | Alto | Alto |
| TRIB-05* | Tributação | Integração NFS-e SEFAZ XML ABRASF | Médio | Alto | Alto |

*CONT-08 e TRIB-05 estão formalmente como ⚠️ mas exigem integração externa fora do controle do produto.

---

## 5. Não Aplicáveis (〰️)

| ID | Requisito | Motivo |
|---|---|---|
| TRV-14 | HTTPS / TLS | Responsabilidade de infra/deploy; proxy reverso documentado |

---

## 6. Análise de Congelamento

### Ponto de Congelamento Recomendado
O produto está pronto para proposta comercial ao nível atual. Os 9 pendentes restantes dividem-se em dois grupos:

**Grupo A — Ressalvas técnicas documentadas (não implementar antes da proposta):**
- RH-08 (DIRF), RH-09 (RAIS/eSocial), CONT-10 (BP/DRE/DFC), TRV-10 (Multi-tenancy): alta complexidade, longa duração, risco de introduzir bugs em código estável. Devem constar como "fase de evolução" no contrato.
- TRIB-05 (SEFAZ), CONT-08 (SIOP REST): dependem de credenciais/certificados externos ao produto.

**Grupo B — Candidatos à última sprint (implementar antes da proposta):**
- FRO-08 (L/100km): ~2h, zero risco — campo calculado sobre dados existentes
- FRO-09 (alertas preventivos): ~4h, zero risco — campo + endpoint de listagem
- PAT-06 (reavaliação ativo): ~8h, risco médio — novo endpoint com lançamento contábil

Implementar FRO-08 + FRO-09 + PAT-06 leva a aderência plena de **79% → 82% (72/87)**.
