# Checklist de Validação e Aceite

**Versão:** 1.0 | **Data:** 2026-04 | **Produto:** Sistema ERP Municipal

---

## Instruções de uso

Este documento deve ser preenchido pelo coordenador de implantação e pelos usuários-chave durante a fase de homologação. Cada item deve ser marcado como **✅ Aprovado**, **❌ Reprovado** ou **⚠️ Pendente de ajuste**.

---

## 1. Infraestrutura e Acesso

| # | Item | Status | Observações |
|---|---|---|---|
| 1.1 | Sistema acessível via HTTPS no domínio configurado | | |
| 1.2 | Certificado SSL válido (sem aviso de segurança no browser) | | |
| 1.3 | Tempo de resposta da API < 2s para listagens paginadas | | |
| 1.4 | Login funciona com credenciais de admin | | |
| 1.5 | Refresh de token funciona (sessão persiste > 15 min) | | |
| 1.6 | Portal de transparência acessível sem login | | |

---

## 2. Autenticação e Controle de Acesso

| # | Item | Status | Observações |
|---|---|---|---|
| 2.1 | Usuário `admin` tem acesso a todos os módulos | | |
| 2.2 | Usuário `accountant` acessa contabilidade e orçamento; NÃO acessa RH | | |
| 2.3 | Usuário `hr` acessa folha; NÃO acessa contabilidade | | |
| 2.4 | Usuário `read_only` visualiza; NÃO consegue criar ou editar | | |
| 2.5 | Usuário `employee` acessa apenas portal do servidor | | |
| 2.6 | Logout limpa token e redireciona ao login | | |
| 2.7 | Troca de senha funciona | | |

---

## 3. Orçamento — PPA / LDO / LOA

| # | Item | Status | Observações |
|---|---|---|---|
| 3.1 | Criar PPA com programas vinculados | | |
| 3.2 | Criar LDO com metas fiscais | | |
| 3.3 | Criar LOA com itens de despesa | | |
| 3.4 | Saldo disponível na LOA reflete empenhos realizados | | |
| 3.5 | Exportação CSV da LOA funciona | | |

---

## 4. Contabilidade — Empenho / Liquidação / Pagamento

| # | Item | Status | Observações |
|---|---|---|---|
| 4.1 | Criar empenho com número, valor, fornecedor e dotação | | |
| 4.2 | Liquidar empenho (parcial e total) | | |
| 4.3 | Registrar pagamento de empenho liquidado | | |
| 4.4 | Empenho sem saldo de dotação gera erro claro | | |
| 4.5 | Relatório de empenhos por status disponível | | |

---

## 5. Compras e Licitações

| # | Item | Status | Observações |
|---|---|---|---|
| 5.1 | Criar processo licitatório com número e objeto | | |
| 5.2 | Vincular contrato ao processo licitatório | | |
| 5.3 | Registrar aditivo de contrato | | |
| 5.4 | Listar contratos com filtro por status | | |

---

## 6. Protocolo e Processos Administrativos

| # | Item | Status | Observações |
|---|---|---|---|
| 6.1 | Abrir protocolo com assunto e interessado | | |
| 6.2 | Registrar tramitação (despacho) com data | | |
| 6.3 | Encerrar protocolo | | |
| 6.4 | Listar protocolos por assunto e status | | |

---

## 7. Convênios

| # | Item | Status | Observações |
|---|---|---|---|
| 7.1 | Cadastrar convênio com tipo (recebimento/repasse) | | |
| 7.2 | Registrar desembolso/parcela | | |
| 7.3 | Listar convênios com filtro por status | | |
| 7.4 | Convênio em rascunho NÃO aparece no portal público | | |

---

## 8. Tributário / Arrecadação

| # | Item | Status | Observações |
|---|---|---|---|
| 8.1 | Cadastrar contribuinte (PF e PJ) | | |
| 8.2 | Cadastrar imóvel vinculado ao contribuinte | | |
| 8.3 | Lançar IPTU com competência, exercício e valor | | |
| 8.4 | Emitir guia de arrecadação com código de barras | | |
| 8.5 | Registrar pagamento de guia (baixa) | | |
| 8.6 | Lançamento fica com status "pago" após baixa | | |
| 8.7 | Inscrever lançamento vencido em dívida ativa | | |
| 8.8 | Dashboard tributário exibe KPIs corretos | | |
| 8.9 | Lançamento pago NÃO pode ser inscrito em dívida ativa | | |

---

## 9. RH e Folha de Pagamento

| # | Item | Status | Observações |
|---|---|---|---|
| 9.1 | Cadastrar funcionário com cargo e salário base | | |
| 9.2 | Gerar evento de folha (salário, INSS, IR) | | |
| 9.3 | Emitir contracheque | | |
| 9.4 | Funcionário acessa próprio contracheque no portal | | |

---

## 10. Patrimônio

| # | Item | Status | Observações |
|---|---|---|---|
| 10.1 | Cadastrar bem patrimonial com número e valor | | |
| 10.2 | Registrar movimentação (transferência de responsável) | | |
| 10.3 | Listar bens por tipo e localização | | |

---

## 11. Portal de Transparência

| # | Item | Status | Observações |
|---|---|---|---|
| 11.1 | Painel geral exibe KPIs atualizados | | |
| 11.2 | Empenhos listados com busca e exportação CSV | | |
| 11.3 | Contratos listados com filtro por status e CSV | | |
| 11.4 | Processos licitatórios listados com filtro e CSV | | |
| 11.5 | Convênios listados (sem rascunhos) com filtro e CSV | | |
| 11.6 | Arrecadação tributária paga listada com filtro e CSV | | |
| 11.7 | Dívida ativa listada SEM expor dados pessoais | | |
| 11.8 | Todos os endpoints do portal respondem sem autenticação | | |

---

## 12. Auditoria

| # | Item | Status | Observações |
|---|---|---|---|
| 12.1 | Log de auditoria registra criação/edição/exclusão | | |
| 12.2 | Admin visualiza trilha de auditoria com filtro | | |
| 12.3 | Outros perfis NÃO acessam auditoria | | |

---

## 13. Migração de Dados

| # | Item | Status | Observações |
|---|---|---|---|
| 13.1 | Total de contribuintes migrados confere com o legado | | |
| 13.2 | Total de imóveis migrados confere com CADIMO | | |
| 13.3 | Soma de lançamentos em aberto confere com relatório legado | | |
| 13.4 | Total de dívida ativa confere com CDA vigente | | |
| 13.5 | Total de contratos vigentes confere | | |
| 13.6 | Amostragem de 30 contribuintes confirmada pelos fiscais | | |

---

## Assinaturas de Aceite

| Papel | Nome | Assinatura | Data |
|---|---|---|---|
| Gestor municipal | | | |
| Coordenador de TI | | | |
| Contador chefe | | | |
| Fiscal tributário | | | |
| Responsável RH | | | |
| Técnico de implantação | | | |

---

*Todos os itens devem estar com status ✅ Aprovado para emissão do Termo de Aceite e início do período de garantia.*
