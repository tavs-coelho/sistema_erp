# ERP Público — Plano de entregas completas e verificáveis

**Produto da G. COELHO DE MELO LTDA.** Replanejamento de 03/11/2026.
Substitui a proposta anterior de pequenos PRs até o número 100.

## Nova dimensão de entregas

Estimativa inicial: **45 a 70 PRs de integração funcional a partir do PR #11**,
com referência de planejamento de **aproximadamente 55 PRs abrangentes**.
A quantidade será reestimada quando cada item da matriz de 2.420 requisitos
funcionais e 52 tecnológicos estiver vinculado a código e teste.

Cada PR de negócio deve oferecer um ou mais **fluxos operacionais completos**,
com migração/modelos SQL, APIs, RBAC/multi-entidade, UI, auditoria,
documentação de operação e execução de testes. Não criar PRs só para mover
arquivos, pintar dashboards ou adicionar endpoints sem experiência utilizável.
As correções de incidentes de segurança e de produção podem justificar
PRs menores excepcionais.

## Sequência de trabalho integrada (números são identificadores provisórios)

| Faixa | Qtde. planejada | Fluxos que precisam funcionar de ponta a ponta |
| --- | ---: | --- |
| 11–14 | 4 | Instalação e navegação reais, login/MFA/CSRF/HttpOnly, sessão renovável, tenant/usuários/permissões, dados e backup/restauração, smoke e2e em Docker |
| 15–20 | 6 | Núcleo municipal: entidades, unidades, pessoas/fornecedores, exercícios, documentos e assinaturas, processos/tarefas/notificações e central de suporte/FAQ |
| 21–29 | 9 | Contabilidade e planejamento PPA/LDO/LOA, empenho/liquidação/pagamento, tesouraria, conciliação e prestação de contas com normas verificadas |
| 30–37 | 8 | Requisição/compra/licitação/contrato, nota fiscal, recebimento, almoxarifado, patrimônio e integrações com execução financeira |
| 38–45 | 8 | RH e folha, ponto, servidor, eSocial, tributação, protestos, arrecadação e cobrança |
| 46–51 | 6 | Portal do cidadão/transparência, protocolo/tramitação, GED, obras, frotas e cemitérios |
| 52–57 | 6 | Educação, saúde, BI, assistente virtual, integrações intermodulares e painéis |
| 58–65 | 8 | Hardening, dados legados, teste de carga, acessibilidade, homologação, LGPD, requisitos do TR e POC por módulo |

**Total de referência dessa divisão: 55 PRs (#11–#65).**
Dependendo da profundidade da matriz e das integrações externas,
a faixa real pode ser maior ou menor. Não equiparar número de PRs
ao percentual de atendimento à licitação.

## PR #11 — novo escopo: migração de navegador + aplicação realmente utilizável

Exige, antes de aprovação:
1. Endpoints FastAPI de sessão por cookie HttpOnly + CSRF, MFA e refresh.
2. Substituição de armazenamento de JWT por chamadas de mesma origem no frontend.
3. Proxy correto via Nginx e Next.js direto (sem URL API inválida).
4. Teste de stack completa em containers com banco PostgreSQL inicializado;
   GET login, CSRF, autenticação, leitura do usuário e departamento, criação,
   consulta e tramitação de protocolo, renovação e logout.
5. Testes unitários/integrados de MFA, cookies, isolamento e compatibilidade.
6. FAQ de execução, segredos e protocolo. Evidência real da CI.
7. Nenhum merge na main e nenhum deploy automático.

## PRs amplos subsequentes (planejamento técnico)

- #12: eliminar dependências restantes de token JS, finalizar sessão browser
  e tratamento de erros/reconexão; homologar navegador real com Playwright,
  uploads/downloads, abas simultâneas e fluxos em todos os menus.
- #13: segregação multi-entidade transversal, RBAC por operação, testes
  negativos IDOR em endpoints de negócio e migrações sem perda de dados.
- #14: instalação/homologação/backup-restauração em PostgreSQL, política
  de segredos, logging, métricas e procedimentos de recuperação.
- #15–#17: cadastro de entidades, fornecedores, equipes e usuários,
  cadastros unificados e documentos, tudo com pesquisa e auditoria.
- #18–#20: protocolo/GED/tramitação/assinatura, notificações e suporte,
  integrados com os cadastros, interface e FAQ.
- #21–#23: orçamento PPA/LDO/LOA e ciclo contábil com regras normativas.
- #24–#26: tesouraria/contas/conciliação/execução financeira.
- #27–#29: prestação de contas e integrações externas verificadas.

## Portão de aceite por PR

- A funcionalidade existe e utiliza banco de dados real.
- Execução válida de migrations, incluindo PostgreSQL.
- Usuário consegue realizar o processo do início ao fim no frontend.
- Permissões, segregação de órgão e logs de auditoria implementados.
- Testes automatizados executados, com falhas bloqueantes corrigidas.
- Pelo menos um teste de integração de ponta a ponta para a entrega.
- Manual/FAQ de utilização e limitações documentadas.
- PR com links para commits e resultados, sem afirmações genéricas.

## Critérios de licitação

A prova de conceito de Dois Córregos requer demonstração de pelo menos
**85% de cada módulo** e **100% dos requisitos tecnológicos**.
Não há ainda cobertura por requisito oficial apurada nesta execução.
As 21 áreas são um mapa funcional, não prova de 21 módulos prontos.
Ao ampliar a matriz, registrar para cada requisito: identificador do
TR, unidade, API/tela, fonte/migração, teste executado e evidência de
demonstração. Só então calcular cobertura por módulo.

**Princípio:** menos PRs superficiais; mais entregas completas com
funcionamento reproduzido, sem confundir CI verde com produção pronta.
