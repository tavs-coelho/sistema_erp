# Plano de Implantação — Sistema ERP Municipal

**Versão:** 1.0 | **Data:** 2026-04 | **Produto:** Sistema ERP Municipal

---

## 1. Objetivo

Detalhar as etapas, responsabilidades, pré-requisitos e cronograma necessários para colocar o Sistema ERP Municipal em produção no ambiente do cliente (prefeitura).

---

## 2. Escopo da Implantação

| Módulo | Incluído nesta entrega |
|---|---|
| Autenticação e controle de acesso (RBAC) | ✅ |
| Contabilidade — Empenho / Liquidação / Pagamento | ✅ |
| Orçamento — PPA / LDO / LOA | ✅ |
| Compras e Licitações | ✅ |
| Contratos | ✅ |
| Protocolo e Processos Administrativos | ✅ |
| Convênios | ✅ |
| RH e Folha de Pagamento | ✅ |
| Portal do Servidor | ✅ |
| Patrimônio | ✅ |
| **Tributário / Arrecadação Municipal** | ✅ |
| **Portal de Transparência** | ✅ |
| Trilha de Auditoria | ✅ |
| Almoxarifado / Frota | ⬜ (fase 2) |

---

## 3. Pré-requisitos Técnicos

### 3.1 Infraestrutura mínima (produção)

| Componente | Requisito mínimo |
|---|---|
| Servidor de aplicação | 4 vCPU, 8 GB RAM, SSD 100 GB |
| Sistema operacional | Ubuntu 22.04 LTS |
| Runtime Python | 3.12+ |
| Runtime Node.js | 20 LTS |
| Banco de dados | PostgreSQL 15+ (recomendado) ou SQLite para testes |
| Proxy reverso | Nginx 1.24+ |
| Certificado SSL | Let's Encrypt (domínio público) ou certificado interno |
| Backup | Snapshot diário + retenção 30 dias |

### 3.2 Acessos necessários

- Credenciais do servidor (SSH)
- Domínio ou IP público do servidor
- Acesso ao banco de dados legado (para migração)
- Usuário de banco de dados com permissões de criação de schema

### 3.3 Dependências de rede

- Acesso HTTPS de saída (pip, npm, Let's Encrypt)
- Porta 443 (HTTPS) aberta ao público para o portal de transparência
- Portas 8000 (API) e 3000 (frontend) internas entre serviços

---

## 4. Fases de Implantação

### Fase 0 — Preparação (Semana 1)

| # | Atividade | Responsável | Duração |
|---|---|---|---|
| 0.1 | Levantamento do ambiente atual da prefeitura | Técnico de implantação | 1 dia |
| 0.2 | Provisionamento do servidor (VM ou bare-metal) | TI da prefeitura | 1 dia |
| 0.3 | Instalação do SO, Docker, dependências base | Técnico | 1 dia |
| 0.4 | Clone do repositório e configuração de variáveis de ambiente | Técnico | 2 h |
| 0.5 | Configuração do banco de dados PostgreSQL | DBA / Técnico | 2 h |
| 0.6 | Validação da conectividade interna (API ↔ BD ↔ Frontend) | Técnico | 1 h |

### Fase 1 — Instalação e Migração (Semana 1–2)

| # | Atividade | Responsável | Duração |
|---|---|---|---|
| 1.1 | Execução do `pip install` e `npm install` | Técnico | 30 min |
| 1.2 | Execução das migrations (`alembic upgrade head`) | Técnico | 15 min |
| 1.3 | Carga de dados iniciais (seed) | Técnico | 30 min |
| 1.4 | Migração de dados legados (ver Plano de Migração) | DBA + Técnico | 2–5 dias |
| 1.5 | Validação pós-migração (conferência de totais) | Coordenador + TI | 1 dia |

### Fase 2 — Configuração e Parametrização (Semana 2)

| # | Atividade | Responsável | Duração |
|---|---|---|---|
| 2.1 | Cadastro de usuários e perfis (admin, contador, RH, etc.) | Coordenador | 2 h |
| 2.2 | Cadastro de departamentos e unidades orçamentárias | Coordenador | 2 h |
| 2.3 | Importação do Plano de Contas (LOA vigente) | Contador | 4 h |
| 2.4 | Configuração do exercício fiscal corrente | Contador | 1 h |
| 2.5 | Cadastro de contribuintes e imóveis (carga inicial) | Fiscal tributário | 1–2 dias |
| 2.6 | Validação de acessos por perfil | Coordenador + Técnico | 2 h |

### Fase 3 — Homologação (Semana 3)

| # | Atividade | Responsável | Duração |
|---|---|---|---|
| 3.1 | Execução do Checklist de Aceite (ver doc específico) | Coordenador + usuários-chave | 1 dia |
| 3.2 | Testes de aceitação por perfil (fluxo ponta a ponta) | Usuários-chave | 2 dias |
| 3.3 | Ajustes de parametrização identificados na homologação | Técnico | 1 dia |
| 3.4 | Treinamento por perfil (ver Roteiro de Treinamento) | Técnico / Coordenador | 2 dias |
| 3.5 | Assinatura do Termo de Homologação | Gestor municipal | — |

### Fase 4 — Go-Live (Semana 4)

| # | Atividade | Responsável | Duração |
|---|---|---|---|
| 4.1 | Corte do sistema legado (data definida com gestor) | Gestor municipal | — |
| 4.2 | Início da operação em produção | Todos os usuários | — |
| 4.3 | Acompanhamento intensivo (suporte on-site ou remoto) | Técnico | 5 dias |
| 4.4 | Relatório de implantação final | Técnico | 1 dia |

---

## 5. Variáveis de Ambiente

```env
# backend/.env
DATABASE_URL=postgresql://erp:senha@localhost:5432/erp_municipal
SECRET_KEY=<gerar com: openssl rand -hex 32>
REFRESH_SECRET_KEY=<gerar com: openssl rand -hex 32>
CORS_ORIGINS=["https://erp.prefeitura.gov.br"]

# frontend/.env.local
NEXT_PUBLIC_API_URL=https://erp.prefeitura.gov.br/api
```

---

## 6. Procedimento de Deploy

```bash
# 1. Clonar repositório
git clone https://github.com/tavs-coelho/sistema_erp /opt/erp
cd /opt/erp

# 2. Backend
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 3. Frontend
cd ../frontend
npm ci && npm run build
# Servir via nginx ou: npm start -- -p 3000
```

---

## 7. Rollback

Em caso de falha crítica na fase de go-live:

1. Restaurar snapshot do BD anterior à migração
2. Reverter migration: `alembic downgrade -1`
3. Retornar ao sistema legado até resolução
4. Abrir chamado com equipe técnica com logs coletados

---

## 8. Suporte pós-implantação

- **Período intensivo:** 30 dias após go-live (suporte com SLA de 4 horas)
- **Período normal:** a partir do 31º dia (SLA conforme contrato)
- **Canal de acionamento:** e-mail suporte@sistema-erp.gov.br / telefone definido em contrato
