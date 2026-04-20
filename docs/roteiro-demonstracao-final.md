# Roteiro de Demonstração Final — Sistema ERP Municipal

**Versão:** 1.0 — Congelamento de produto 2026-04-19  
**Duração estimada:** 90 minutos  
**Audiência-alvo:** Comissão técnica / avaliadores do edital  
**Ambiente:** Demo local (`http://localhost:3000`) + backend (`http://localhost:8000/docs`)

---

## Preparação (antes da apresentação)

### Checklist técnico
- [ ] Backend rodando: `uvicorn app.main:app --reload` na porta 8000
- [ ] Seed executado: `python seed.py` (cria usuários demo + dados iniciais)
- [ ] Frontend rodando: `npm run dev` na porta 3000
- [ ] Testar login admin: usuário `admin1`, senha `demo123`
- [ ] Abrir em paralelo: `/docs` (Swagger) para demonstração da API

### Dados de demonstração prontos
| Item | Valor demo |
|---|---|
| Município | Município Demo — IBGE 9999999 |
| Exercício LOA | 2026 |
| CNPJ Fornecedor | 12.345.678/0001-99 |
| CPF Contribuinte (com débito) | 111.222.333-44 |
| Servidor RH | José da Silva — Matrícula EMP-001 |
| Processo licitatório | PP-001/2026 — Aquisição de combustíveis |

---

## Roteiro por Bloco (90 min)

### Bloco 1 — Acesso e Segurança (10 min)

**Objetivo:** Demonstrar autenticação, RBAC e rastreabilidade.

1. **Login** em `http://localhost:3000`
   - Entrar com `admin1 / demo123` → mostrar JWT e token de acesso
   - Mostrar bloqueio de senha expirada (login com `admin1` na primeira vez pede troca)

2. **Rate limiting** (abrir Swagger `/docs`)
   - Executar 11+ POSTs em `/auth/login` com credenciais inválidas
   - Mostrar resposta `429 Too Many Requests` na 11ª tentativa
   - *Ponto de destaque:* proteção automática contra força bruta

3. **RBAC**
   - Fazer login com `read_only1 / demo123`
   - Tentar `POST /hr/ferias` → receber `403 Forbidden`
   - Fazer login novamente com `admin1`

4. **Audit log**
   - No Swagger: `GET /audit/logs` → filtrar por `action=login`
   - Mostrar registro de IP, timestamp, usuário em cada autenticação

---

### Bloco 2 — Orçamento e Execução Financeira (15 min)

**Objetivo:** Demonstrar ciclo PPA → LDO → LOA → Execução orçamentária.

1. **PPA / LDO** em `/orcamento`
   - Mostrar programas cadastrados no PPA 2022–2025
   - Mostrar diretrizes e metas da LDO 2026

2. **LOA 2026**
   - Criar dotação: Função 04 (Saúde), Subfunção 122, Programa 0001
   - Valor total: R$ 500.000,00

3. **Empenho com atualização de saldo** (ponto ORC-05)
   - `POST /accounting/commitments` com `loa_item_id` da dotação criada
   - Após criar: consultar `GET /accounting/loa-items/{id}` → mostrar `executed_amount` atualizado
   - *Ponto de destaque:* saldo executado atualizado atomicamente, sem divergência orçamentária

4. **Ciclo completo**
   - Criar Liquidação vinculada ao empenho
   - Criar Pagamento
   - Mostrar status em cada etapa

5. **Relatório de execução** em `/relatorios`
   - Exportar CSV de comprometimento por dotação

---

### Bloco 3 — Compras e Almoxarifado (10 min)

**Objetivo:** Demonstrar rastreabilidade da compra até o estoque.

1. **Licitação** em `/compras`
   - Mostrar PP-001/2026 já cadastrado
   - Clicar em "Fornecedores" → mostrar CNPJ único validado

2. **Contrato + Empenho**
   - Mostrar contrato vinculado ao processo
   - Mostrar empenho vinculado ao contrato

3. **Recebimento → Almoxarifado** (integração automática)
   - Criar Recebimento de Material para o contrato
   - Navegar para `/almoxarifado` → mostrar entrada automática no estoque

4. **Alerta de estoque mínimo**
   - Registrar saída que ultrapasse o estoque mínimo
   - Mostrar `AlertaEstoque` gerado e `RequisicaoCompra` criada automaticamente
   - *Ponto de destaque:* zero intervenção manual para reposição

5. **Portal público** (`/public`)
   - Mostrar licitações sem autenticação
   - Mostrar filtros por modalidade, status, período

---

### Bloco 4 — Tributação e Portal do Contribuinte (10 min)

**Objetivo:** Demonstrar ciclo de arrecadação e transparência fiscal.

1. **IPTU** em `/tributario`
   - Mostrar imóvel cadastrado com área, alíquota, valor venal
   - Gerar lançamento IPTU 2026

2. **Dívida ativa e parcelamento**
   - Mostrar lançamento em cobrança
   - Criar parcelamento: 12x + juros

3. **Portal do contribuinte** (sem autenticação)
   - Acessar `GET /public/contribuinte/111.222.333-44/debitos`
   - Mostrar lista de débitos com valores, vencimentos e status
   - Acessar `GET /public/contribuinte/111.222.333-44/certidao`
   - Mostrar certidão positiva (contribuinte com débito)
   - *Ponto de destaque:* transparência fiscal sem necessidade de login

4. **ISS e NFS-e**
   - Emitir Nota Fiscal de Serviço
   - Mostrar cálculo automático do ISS
   - Mostrar lançamento tributário gerado

---

### Bloco 5 — Recursos Humanos e Folha (15 min)

**Objetivo:** Demonstrar ciclo completo de RH municipal.

1. **Cadastro de servidores** em `/rh`
   - Mostrar servidor José da Silva com matrícula, cargo, departamento, salário
   - Mostrar vínculos: efetivo, comissionado, temporário

2. **Ponto e Frequência**
   - Mostrar registros de ponto do mês corrente
   - Mostrar escala de trabalho configurada
   - Lançar falta justificada → abono automático

3. **Integração ponto → folha**
   - Executar `POST /hr/integracao-ponto-folha` com `dry_run=true`
   - Mostrar preview de descontos e créditos
   - Confirmar integração → eventos gerados automaticamente

4. **Folha de pagamento**
   - Mostrar eventos do mês (salário + horas extras + descontos)
   - Processar holerite
   - Baixar PDF do contracheque

5. **Escala de férias** (ponto RH-07)
   - Programar férias: servidor, período, fração (1/3)
   - Mostrar validação de sobreposição (tentar período já programado → erro)
   - Aprovar escala
   - Consultar saldo: `GET /hr/ferias/servidor/1/saldo`
   - *Ponto de destaque:* controle de gozo com rastreabilidade

6. **Portal do servidor**
   - Login com `employee1 / demo123`
   - Mostrar contracheque, férias programadas, registros de ponto

---

### Bloco 6 — Patrimônio e Frota (10 min)

**Objetivo:** Demonstrar controle de ativos e frota.

1. **Patrimônio** em `/patrimonio`
   - Cadastrar bem: computador, tombamento 00001, valor R$ 5.000
   - Transferir para departamento de Tecnologia
   - Registrar manutenção: baixa preventiva
   - Calcular depreciação: mostrar `LancamentoDepreciacao` gerado pelo método linear (NBCASP)

2. **Frota** em `/frota`
   - Mostrar veículo F-100 — Placa XYZ-1234
   - Registrar abastecimento: 50L, R$ 300
   - Registrar manutenção corretiva com peças
   - Mostrar peça baixada automaticamente do almoxarifado
   - Abrir dashboard: consumo mensal, custo por departamento, TCO por veículo

---

### Bloco 7 — Contabilidade, LRF e SICONFI (15 min)

**Objetivo:** Demonstrar conformidade legal e SICONFI Fase 1.

1. **Contabilidade** em `/contabilidade`
   - Mostrar receitas lançadas por categoria
   - Mostrar ciclo empenho → liquidação → pagamento já concluído
   - Conciliação bancária: importar extrato OFX → reconciliar automaticamente

2. **LRF — RREO e RGF**
   - Gerar RREO Bimestral: `POST /rreo-rgf/rreo`
   - Mostrar Quadro de Receitas, Despesas por Função
   - Gerar RGF Quadrimestral: mostrar Disponibilidade Financeira, Pessoal
   - Exportar CSV de ambos

3. **SICONFI XML (Fase 1)**
   - `POST /siconfi/gerar-xml` para FINBRA exercício 2025
   - Mostrar XML gerado: estrutura `<FINBRA>` com contas, valores, IBGE
   - `POST /siconfi/validar-xml` → mostrar validação XSD bem-sucedida
   - Mostrar estrutura idêntica para RREO e RGF
   - *Ponto de destaque:* Fase 2 (envio real) aguarda certificado ICP-Brasil do gestor

4. **Convênios**
   - Mostrar convênio com concedente Estado, parcelas e prestação de contas

---

### Bloco 8 — Protocolo / GED e Encerramento (5 min)

**Objetivo:** Demonstrar gestão documental e fechar.

1. **Protocolo** em `/protocolo`
   - Criar protocolo de requerimento
   - Tramitar para departamento Jurídico
   - Anexar PDF (upload GED): `POST /protocolo/protocolos/1/anexos`
   - Baixar o arquivo: `GET /protocolo/anexos/1/download`
   - *Ponto de destaque:* evidência documental rastreável ao protocolo

2. **API REST e testes**
   - Abrir `/docs` (Swagger): mostrar 100+ endpoints documentados
   - Mostrar `pytest` rodando: 592 testes, 21 suítes

3. **Fechamento**
   - Resumir: 79% de aderência plena, 90% incluindo parciais
   - Ressalvas documentadas: DIRF, Demonstrações Contábeis, Multi-tenancy — fora do escopo do TR atual
   - Próximos passos: SICONFI Fase 2 após entrega de certificado ICP-Brasil

---

## Perguntas Frequentes (FAQ Técnico)

| Pergunta | Resposta |
|---|---|
| Funciona sem internet? | Sim. Toda a lógica é local. SICONFI Fase 2 requer conectividade gov.br. |
| Banco de dados? | PostgreSQL em produção; SQLite em testes automatizados. |
| Escalável para múltiplos municípios? | Arquitetura preparada; multi-tenancy como fase de evolução contratual. |
| DIRF está implementada? | Não nesta versão — reconhecida como obrigação acessória para Onda 21 (proposta posterior). |
| NFS-e tem validade fiscal? | NFS-e interna implementada. Integração com SEFAZ municipal como fase futura. |
| Como é feito o deploy? | Docker + docker-compose. Proxy reverso Nginx para HTTPS. |
| Migrations são reversíveis? | Sim — todas as 17 migrations têm `upgrade()` e `downgrade()` Alembic. |
| Qual o SLA de resposta da API? | p95 < 100ms em queries indexadas; relatórios complexos < 2s. |

---

## Script de Comandos para Demo Rápida

```bash
# Iniciar backend (dev)
cd apps/backend
uvicorn app.main:app --reload --port 8000

# Popular com dados demo
python seed.py

# Rodar todos os testes
python -m pytest -q

# Iniciar frontend
cd apps/frontend
npm run dev
```

Endpoints-chave para demonstração direta no Swagger:
- `POST /auth/login` — obter token
- `GET /public/contribuinte/{cpf_cnpj}/debitos` — sem auth
- `POST /accounting/commitments` — empenho com atualização LOA
- `POST /siconfi/gerar-xml` — SICONFI Fase 1
- `POST /protocolo/protocolos/{id}/anexos` — upload GED
