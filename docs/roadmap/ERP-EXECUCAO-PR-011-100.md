# Plano de entregas do ERP Público — PRs 11 a 100 (projeção)

Produto próprio da G. COELHO DE MELO LTDA. Base: 21 módulos, 2.420 requisitos
funcionais e 52 tecnológicos informados na matriz de Dois Córregos/SP.
**Este é um orçamento de trabalho preliminar, não uma declaração de aderência
ou promessa de quantidade exata.** Os códigos oficiais de cada requisito serão
preenchidos após conferência individual do Termo de Referência e da matriz.

## Estimativa

Meta de planejamento: **90 Pull Requests adicionais, incluindo o PR #11**
(séries de trabalho P11–P100; numeração real do GitHub pode variar).
Intervalo plausível: **70 a 130 PRs**, a ser recalculado a cada cinco entregas.
A complexidade contábil, fiscal, de saúde e educação pode exigir subdivisões
adicionais; não comprimir fluxos só para cumprir a meta numérica.

| Faixa de trabalho (provisória) | Quant. | Objetivo e módulos | Gate ao encerrar a fase |
| --- | ---: | --- | --- |
| P11–P18 | 8 | HttpOnly/CSRF, migração de clientes JS, CSP, testes e2e, renovação, backups/restauração, RBAC/multi-entidade e observabilidade | Sessão segura, backup-restauração reproduzível, testes multi-tenant |
| P19–P27 | 9 | Núcleo: entidades/unidades, usuários/cargos/perfis, pessoas/fornecedores, exercício, documentação/versionamento, tramitação, notificações, relatórios, suporte/FAQ | Fluxos reutilizáveis com auditabilidade e permissões |
| P28–P39 | 12 | Contabilidade, PPA/LDO/LOA, tesouraria e prestação de contas AUDESP/eSocial | Regras fiscais verificadas com fontes e dados de teste |
| P40–P51 | 12 | Compras/licitações/contratos, patrimônio, almoxarifado e monitoramento de NF-e | Ciclos integrados entre requisição, contrato, recebimento e patrimônio |
| P52–P63 | 12 | RH/folha/portal/ponto/eSocial e gestão tributária/protestos | Cálculos e integrações validados por domínio e dados representativos |
| P64–P74 | 11 | Atendimento ao cidadão, transparência, protocolo e gestão documental | Acesso público protegido, trilhas e fluxos de ponta a ponta |
| P75–P86 | 12 | Frotas, cemitérios, obras, educação e saúde | Permissões setoriais, LGPD e integrações verificadas |
| P87–P91 | 5 | BI/painéis, assistente virtual e integrações transversais | Resultados reproduzíveis e restrição de acesso aos dados |
| P92–P100 | 9 | Homologação, desempenho, acessibilidade, segurança, migração de legados, FAQ, cenários de POC e evidências por requisito | Cobertura por módulo e tecnologia comprovada sem extrapolação |

## Próximos PRs definidos

- **P11 (em desenvolvimento):** API de sessão browser opt-in, HttpOnly,
  CSRF com dupla submissão assinada, login/MFA/refresh/logout; sem mudança
  automática do cliente legado.
- **P12:** converter login, fluxo MFA, logout, painéis e chamadas frontend
  restantes para autenticação por cookies; substituir verificação superficial
  de sessão por checagem válida; remover armazenamento de bearer em
  `localStorage`; testes de navegação e e2e.
- **P13:** renovação coordenada entre abas, prevenção de refresh concorrente,
  fallback para sessão expirada, cookies em proxy/TLS e CSRF em formulários
  e exportações.
- **P14:** CSP, cabeçalhos de segurança, validação de origens e revisão
  de bibliotecas de frontend.
- **P15–P18:** backup/restauração PostgreSQL, observabilidade/alertas,
  políticas de perfis e exercício de isolamento com exploração IDOR controlada.

## Definição obrigatória de pronto para cada funcionalidade

Uma funcionalidade só pode ir de `em desenvolvimento` para `testada`
quando existirem, conforme aplicável: modelo/migração de banco, regra de
negócio, API, UI, RBAC/multi-entidade, validações, auditoria, documentação
de operação, teste executado em CI e evidência reproduzível.

Não marcar `demonstrável` sem validação no ambiente da prova de conceito
e identificação do item exato do TR. Registrar em cada requisito: código do
TR, módulo, arquivos, endpoint/tela, teste, execução, pendências e status.

Critério de POC: **ao menos 85% das funcionalidades de CADA módulo** e
**100% dos requisitos tecnológicos**, não apenas média global.
Cobertura ainda não aferida. 2.420 e 52 são quantitativos informados,
não validação individual dos itens.

## Riscos que podem alterar a quantidade estimada

1. Regras e layouts externos (AUDESP, eSocial, NF-e, saúde), certificação,
   mudanças normativas e homologações que exigem evidência específica.
2. Isolamento multi-entidade em tabelas legadas sem `tenant_id`;
   migração com dados existentes e integrações entre órgãos.
3. Migração browser para cookies/CSRF em telas com fetch direto ou tokens
   JavaScript; não habilitar modo cookie em produção antes do corte completo.
4. Completude da matriz técnica e testes de demonstração de requisitos por
   município, não substituíveis por contagem de commits.
5. Integrações externas, infraestrutura, SLA e retenção documental contratual.

**Política de entrega:** PR pequeno e reversível, CI verde, análise de risco,
sem merge e sem deploy automáticos. O número de PRs representa capacidade
de trabalho estimada, não percentual de requisito implementado.
