# Plano Operacional — Sistema ERP Municipal

**Versão:** 1.0 | **Data:** 2026-04 | **Produto:** Sistema ERP Municipal

---

## 1. Objetivo

Descrever os procedimentos operacionais contínuos para garantir o funcionamento seguro, disponível e auditável do Sistema ERP Municipal após o go-live.

---

## 2. Rotinas Diárias

| Horário | Atividade | Responsável |
|---|---|---|
| 08h00 | Verificar painel de monitoramento (uptime, erros 5xx) | TI |
| 08h30 | Conferir backup automático do banco de dados (log de sucesso) | TI |
| Qualquer horário | Atender chamados de usuário com SLA contratual | Suporte |

### 2.1 Verificação de saúde da API

```bash
curl -sf https://erp.prefeitura.gov.br/api/health | jq .
# Resposta esperada: {"status": "ok"}
```

---

## 3. Rotinas Semanais

| Atividade | Responsável | Quando |
|---|---|---|
| Revisar trilha de auditoria em busca de acessos suspeitos | Administrador | Segunda-feira |
| Verificar lançamentos tributários vencidos em aberto (dashboard) | Fiscal tributário | Segunda-feira |
| Conferir empenhos sem liquidação há > 30 dias | Contador | Terça-feira |
| Revisar contratos com vencimento nos próximos 30 dias | Secretaria | Quarta-feira |
| Verificar integridade dos backups (restore de amostra) | TI | Sexta-feira |

---

## 4. Rotinas Mensais

### 4.1 Fechamento contábil

1. Verificar que todos os empenhos do mês estão liquidados ou justificados
2. Conferir saldo de dotações (não pode ser negativo)
3. Gerar relatório mensal de pagamentos (exportação CSV)
4. Arquivar relatório em pasta de competência

### 4.2 Fechamento da folha de pagamento

1. Lançar todos os eventos do mês (vencimentos, descontos)
2. Revisar totais por departamento
3. Fechar folha e liberar acesso ao contracheque para os servidores
4. Exportar arquivo para SIAPE/SIAFI se necessário

### 4.3 Arrecadação tributária

1. Verificar lançamentos vencidos sem pagamento
2. Emitir relatório de inadimplência (filtrar aberto + vencido)
3. Encaminhar lista de inadimplentes para análise de inscrição em dívida ativa

### 4.4 Portal de transparência

1. Verificar que novos convênios vigentes estão aparecendo no portal
2. Confirmar que convênios rescindidos/encerrados aparecem com status correto
3. Testar exportação CSV de cada categoria

---

## 5. Rotinas Anuais

### 5.1 Encerramento do exercício fiscal

1. Encerrar Ano Fiscal corrente (alterar `active = False`)
2. Criar novo Ano Fiscal para o exercício seguinte
3. Importar LOA aprovada pelo legislativo para o novo exercício
4. Migrar lançamentos tributários em aberto para o exercício corrente (se aplicável por lei municipal)

### 5.2 Lançamento em massa de IPTU

1. Conferir valor venal de todos os imóveis (atualização conforme Planta Genérica de Valores)
2. Executar lançamento em lote via API ou script `POST /tributario/lancamentos` por contribuinte
3. Emitir guias para envio postal (futura integração DETRAN/Correios)

### 5.3 Revisão de dívida ativa

1. Revisar CDA: inscrições com mais de 5 anos → avaliação de prescrição
2. Inscrições ajuizadas: acompanhar andamento judicial
3. Gerar relatório consolidado para a Procuradoria Municipal

---

## 6. Gerenciamento de Usuários

### 6.1 Onboarding de novo usuário

1. Criar usuário no sistema (`POST /users/`) com perfil adequado
2. Comunicar login e senha temporária ao usuário
3. Orientar troca de senha no primeiro acesso
4. Registrar criação na ata de implantação

### 6.2 Offboarding (desligamento)

1. Desativar usuário imediatamente (`PATCH /users/{id}` → `ativo: false`)
2. Revogar token de sessão ativo (se o sistema tiver endpoint de revogação)
3. Registrar desativação na trilha de auditoria

### 6.3 Redefinição de senha

1. Admin acessa `/users/{id}/reset-password`
2. Gerar senha temporária e informar ao usuário
3. Usuário deve trocar a senha temporária no primeiro login

---

## 7. Gestão de Incidentes

### 7.1 Classificação

| Severidade | Descrição | Exemplo | SLA |
|---|---|---|---|
| P1 — Crítico | Sistema indisponível | Banco de dados offline; API retorna 500 em todos endpoints | 4 horas |
| P2 — Alto | Funcionalidade crítica com erro | Não consegue emitir empenho ou guia tributária | 8 horas |
| P3 — Médio | Funcionalidade secundária com erro | Filtro de exportação não retorna CSV correto | 2 dias úteis |
| P4 — Baixo | Melhoria ou cosmético | Texto de label errado; layout quebrado em mobile | Próxima versão |

### 7.2 Procedimento de escalonamento

1. Usuário abre chamado com descrição, prints e passos para reproduzir
2. Suporte N1 classifica a severidade e tenta resolução em 15 min
3. Se não resolvido → escalar para Suporte N2 (desenvolvedor)
4. Se P1 → acionar gerente de projeto imediatamente

### 7.3 Coleta de logs para diagnóstico

```bash
# Logs da API (últimas 500 linhas)
journalctl -u erp-backend -n 500 --no-pager

# Logs do banco de dados PostgreSQL
tail -200 /var/log/postgresql/postgresql-15-main.log
```

---

## 8. Segurança Operacional

| Controle | Frequência | Responsável |
|---|---|---|
| Rotação da `SECRET_KEY` do JWT | Semestral | TI |
| Atualização de dependências Python/Node | Mensal | Desenvolvedor |
| Revisão de usuários ativos vs. lista de servidores | Mensal | RH + TI |
| Teste de restore do backup | Semanal | TI |
| Análise da trilha de auditoria | Semanal | Admin |
| Pentest / varredura de vulnerabilidades | Anual | Equipe de segurança |

---

## 9. Contatos de Suporte

| Papel | Nome | E-mail | Telefone |
|---|---|---|---|
| Suporte N1 | A definir | suporte@sistema-erp.gov.br | — |
| Técnico de implantação | A definir | tecnico@sistema-erp.gov.br | — |
| Gerente de projeto | A definir | gestor@sistema-erp.gov.br | — |
| DBA da prefeitura | A definir | dba@prefeitura.gov.br | — |

---

## 10. Indicadores Operacionais (KPIs de TI)

| KPI | Meta | Forma de medição |
|---|---|---|
| Disponibilidade do sistema | ≥ 99,5% / mês | Uptime monitor externo |
| Tempo médio de resposta da API | < 1 s | Log de requisições |
| Tempo de restore de backup | < 2 horas | Teste semanal |
| Incidentes P1/P2 por mês | ≤ 1 | Registro de chamados |
| Usuários com senha não trocada | 0 | Auditoria mensal |
