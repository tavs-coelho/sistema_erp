# Núcleo Municipal e Processos — entregas #15 a #20

Esta etapa contém **seis fluxos funcionais**, desenvolvidos em Pull Requests
encadeados sobre a `main` com a plataforma anterior integrada. Cada PR precisa
ser aprovado separadamente; o conjunto só deve ser anunciado como integrado após
os seis merges e a CI da `main` com último head confirmado.

## Matriz de entregas

| PR | Modelo / migração | API | Interface | Teste |
|---|---|---|---|---|
| #15 | `MunicipalUnit` / 0022 | `/nucleo/unidades` | `/nucleo/unidades` | `test_nucleo_unidades.py` |
| #16 | `MunicipalParty` / 0023 | `/nucleo/pessoas` | `/nucleo/pessoas` | `test_nucleo_pessoas.py` |
| #17 | `MunicipalAssignment` / 0024 | `/nucleo/lotacoes` | `/nucleo/lotacoes` | `test_nucleo_lotacoes.py` |
| #18 | `MunicipalDocument` / 0025 | `/nucleo/documentos` | `/nucleo/documentos` | `test_nucleo_documentos.py` |
| #19 | `MunicipalTask` / 0026 | `/nucleo/tarefas` | `/nucleo/tarefas` | `test_nucleo_tarefas.py` |
| #20 | `MunicipalNotice/SupportTicket/Reply` / 0027 | `/nucleo/central` | `/nucleo/central` | `test_nucleo_central.py` |

## Percurso operacional integrado

1. Entrar em uma instância **de demonstração isolada**, com a autenticação
   HttpOnly/MFA do ERP (não utilizar contas de teste em servidores públicos).
2. Em **Núcleo · Unidades**, cadastrar uma unidade vinculada à própria secretaria.
3. Em **Núcleo · Pessoas**, registrar um fornecedor fictício e pesquisar o cadastro.
4. Em **Núcleo · Lotações**, vincular um usuário da mesma entidade a uma unidade.
5. Em **Protocolo**, criar um processo; em **Núcleo · Documentos**, vincular
   documento ao processo, enviar revisão textual/PDF e baixar a revisão correta.
6. Em **Núcleo · Tarefas**, criar tarefa com protocolo, responsável e prazo,
   mudar para `em_andamento` e `concluida`.
7. Em **Núcleo · Central**, verificar a notificação de atribuição, abrir
   chamado, responder, atualizar a situação e consultar o FAQ contextual.
8. Encerrar a sessão e verificar que a API privada não aceita novas consultas.

O script `python3 scripts/smoke_nucleo_erp.py`, integrado ao job Docker/Compose,
repete esse percurso com dados sintéticos e valida a persistência em PostgreSQL,
upload e download reais, CSRF e revogação de sessão. Requer o mesmo gate
`ERP_SMOKE_ALLOW_DEMO=1` do smoke existente: **nunca apontar a produção**.

## Autorização e limites de escopo

Os seis conjuntos têm `tenant_id` nas tabelas, validação do dono da operação
e testes com duas entidades. Estes testes **não** tornam automaticamente seguras
as tabelas legadas de contabilidade, folha, compras, tributação e saúde.

- **Pessoas/fornecedores:** diretório institucional separado de `vendors`.
  A sincronização com a execução financeira legado seria insegura sem isolar
  toda a cadeia de fornecedores/contratos; não está implementada.
- **Lotações:** vínculo organizacional, **não** uma política de escopo aplicada
  a todos os módulos. Não elevar permissões com base numa lotação.
- **Documentos:** sem antivírus, assinatura digital regulamentar,
  classificação por secretaria, gestão de retenção, backup de anexos e
  armazenamento externo de produção. Não expor classificações restritas
  em canais públicos.
- **Tarefas:** sem calendário de feriados, regras de SLA/encaminhamento ou
  notificações externas. Estados terminais não podem ser reabertos.
- **Suporte:** não há equipe humana 24h, envio externo, SLA contratual,
  anexos, chat em tempo real nem garantia de atendimento.
- **Segurança:** as permissões por perfil/entidade são controles mínimos;
  requer revisão de IDOR transversal, logs de acesso e LGPD para documentos
  com dados reais. Limpar dados de demonstração após os testes.

## Critério de aceite antes de mesclar

- CI de **cada último commit** aprovada, incluindo backend, frontend, esquema
  PostgreSQL, segurança e testes E2E.
- Branch base de cada PR integrada antes do seguinte, sem rebase que suprima
  migrações; após a integração, revisar o diff e CI da `main`.
- No PR #20, validar execução de
  `scripts/smoke_nucleo_erp.py` contra os quatro containers reais.
- Testar manualmente perfis e entidades em ambiente descartável, não em
  produção.
- Não alegar aderência à POC de Dois Córregos sem mapear os códigos do TR
  e comprovar **85% por módulo e 100% tecnológicos**. A cobertura atual
  não foi aferida item a item.

## Integração planejada

`#15 → #16 → #17 → #18 → #19 → #20`.

Como estes PRs foram abertos com bases encadeadas, os commits do PR seguinte
dependem do anterior; mesclar fora de ordem pode criar múltiplos heads Alembic
ou duplicação de alterações. **Não mesclar automaticamente**.
