# Roadmap atualizado — PRs grandes, com fluxos operacionais completos

**Substitui a estimativa anterior de 90 PRs pequenos.**
Produto: ERP Público próprio da G. COELHO DE MELO LTDA.
Meta: órgãos efetivamente conseguirem operar fluxos com persistência,
autorização, relatórios e trilha de auditoria.

A previsão é de **30 PRs de grande porte no roteiro-base (PR #11–#40)**,
com **faixa de 30–55 PRs** caso validações normativas, integrações e
requisitos específicos exijam desmembramento. A numeração posterior é
indicativa: PR real depende dos merges e de conflitos do GitHub.

Essa não é uma estimativa de prazo nem comprovação de cobertura:
o Termo de Referência de Dois Córregos/SP informa 2.420 requisitos funcionais,
52 tecnológicos, 85% por módulo e 100% tecnológicos. Há 21 módulos, muitos
com regulações e homologações próprias. Não é tecnicamente correto usar
quantidade de PRs para estimar automaticamente atendimento à POC.

## Critério obrigatório para cada PR grande

Nenhuma entrega é só visual. O PR deve conter, conforme aplicável, modelos,
migrações, API, interface navegável, negócio, RBAC, tenant, auditoria, testes
unitários + integrações + navegador real, migração testada em PostgreSQL,
manual/FAQ e evidência verificável. A CI deve testar o fluxo completo.

Para uma funcionalidade ser **demonstrável** na matriz da POC, exigir código
de requisito do TR, arquivos, endpoint/tela, caso de teste, log de execução,
cenário de demonstração e validação na entidade correta. Não substituir isso
por capturas de tela ou total de testes automatizados.

## Sequência orientada por dependência

| PR de referência | Entrega abrangente (escopo previsto) |
| --- | --- |
| #11 | **Aplicação utilizável no navegador:** login+MFA+sessões HttpOnly, CSRF, frontend inteiro sem JWT em storage, proxy Next/Nginx, Docker, primeiro admin, exercício financeiro, ciclo de despesa testado de ponta a ponta |
| #12 | **Segregação multi-entidade real:** migrações e FK de tenant para núcleo contábil e administrativo; consultas/exports/RBAC; testes de acesso cruzado e migração de legado |
| #13 | **Administração institucional:** cadastro de órgãos/unidades, usuários, cargos, permissões granulares, responsáveis, configuração por entidade e auditoria |
| #14 | **Execução contábil:** lançamento, dotação, empenho, liquidação, pagamento, estornos, validações, relatórios e rastreabilidade |
| #15 | **Planejamento completo:** PPA, LDO, LOA, ações, programas, créditos, alterações, vínculo com execução e relatórios |
| #16 | **Tesouraria:** contas, lançamentos, conciliação, fluxo de caixa, pagamento, classificação e trilhas |
| #17 | **Compras e planejamento:** requisições, pesquisa de preço, processos e planejamento de contratação |
| #18 | **Licitações:** edital, julgamento, propostas, homologação e integração com contratos (sem alegar integrações externas não testadas) |
| #19 | **Contratos e convênios:** prazos, aditivos, execução, atestos, medições, notificações e pagamentos vinculados |
| #20 | **Almoxarifado:** pedidos, recebimentos, conferência, saldos, requisições, movimentações, alertas e inventário |
| #21 | **Patrimônio:** registro, movimentação, localização, depreciação, inventário, tombamento e baixa |
| #22 | **Monitoramento de NF-e/NFS-e:** documentos fiscais, consulta, validações, entrada e vinculação a recebimentos |
| #23 | **Gestão tributária:** cadastro fiscal, lançamentos, guias, arrecadação, parcelamentos, dívida ativa e fiscalização |
| #24 | **Protestos e cobrança:** integração jurídica, remessas, notificações, histórico e status |
| #25 | **RH e cadastro funcional:** vínculos, cargos, lotação, benefícios, férias e histórico |
| #26 | **Folha:** cálculo, rubricas, eventos, conferências, fechamento, demonstrativos e exportações |
| #27 | **eSocial e obrigações trabalhistas:** eventos, validações de leiaute, filas, recibos e auditoria |
| #28 | **Ponto e portal do servidor:** jornada, exceções, abonos, integração folha, contracheques e solicitações |
| #29 | **Prestação de contas:** AUDESP e relatórios de responsabilidade fiscal, validação de regras e lotes |
| #30 | **Atendimento e protocolo:** requerimentos, cadastro cidadão, tramitação, prazos, responsáveis e notificações |
| #31 | **Transparência:** publicação segura por entidade, filtros, exportação, acessibilidade e dados agregados |
| #32 | **Documentos:** versionamento, classificação, pesquisa, anexos, assinatura, integridade e guarda |
| #33 | **Frotas e cemitérios:** fluxos operacionais completos, inventário e permissões próprias |
| #34 | **Obras:** projetos, contratos, fiscalização, boletins, medições, cronogramas e registros |
| #35 | **Educação:** cadastro de redes/unidades, turmas, matrículas, professores, frequência e relatórios |
| #36 | **Saúde:** unidades/equipes, atendimento e integrações, LGPD e controles de acesso reforçados |
| #37 | **BI:** painéis, indicadores, drill-down, exportação e segregação por entidade |
| #38 | **Assistente e central de ajuda:** pesquisa autorizada, trilhas de suporte, FAQ e manuais em cada fluxo |
| #39 | **Operação comercial:** implantação, backups/restauração, observabilidade, migração legada, desempenho e suporte |
| #40 | **Homologação e POC:** evidência por requisito, automação dos cenários dos 21 módulos, segurança, acessibilidade e desempenho |

Reavaliar após cada PR operacional. Não comprimir módulos complexos para
ajustar uma quantidade arbitrária de PRs. Na POC, a cobertura deverá ser
calculada individualmente por módulo e tecnologia, não por média geral.

## Gates antes de declarar "funcionando"

1. Instalar em PostgreSQL vazio (já coberto parcialmente pela CI anterior).
2. Ter primeiro administrador e autenticar via navegador sem credenciais fixas.
3. Concluir operação de ponta a ponta por interface + API + banco, não só
   renderizar uma tela.
4. Preservar dados após reinicialização do container.
5. Testar permissões e isolamento entre municípios; até esse gate, não
   afirmar produto multi-entidade pronto.
6. Ter restauração real de backup e alertas de infraestrutura.
7. Validar integrações normativas e fiscais com fontes e ambiente de teste.
8. Demonstrar pessoalmente cada requisito da matriz, com evidências auditáveis.

**Nenhum merge em main ou publicação de produção apenas por CI verde.**
