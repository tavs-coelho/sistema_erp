# SICONFI / SIOP — Documentação Técnica (Onda 18)

## Objetivo

Implementar a **camada preparatória** de prestação de contas ao governo federal,
separando a *preparação dos dados* (ERP → payload estruturado) do *envio externo*
(payload → webservice gov.br), elevando a aderência legal sem depender imediatamente
de credenciais/certificados digitais externos.

---

## Mapeamento ERP → SICONFI/SIOP

| Módulo ERP | Conjunto SICONFI/SIOP |
|---|---|
| `FiscalYear` + `LOAItem` (category=receita) | FINBRA — Receita Prevista (LOA) |
| `RevenueEntry` | FINBRA — Receita Arrecadada |
| `LOAItem` (category≠receita) | FINBRA — Dotação Autorizada |
| `Commitment` | FINBRA/RREO — Despesa Empenhada |
| `Liquidation` | FINBRA/RREO — Despesa Liquidada |
| `Payment` | FINBRA/RREO/RGF — Despesa Paga |
| `Payslip.gross_amount` | RGF — Despesa de Pessoal (proxy bruto) |
| `LOAItem` agrupado por `function_code` | RREO — Despesa por Função |
| `PPA` + `PPAProgram` | SIOP — Programas do PPA |
| `LOAItem` (código função/programa/ação) | SIOP — Ações LOA |
| `LDO` + `LDOGoal` | SIOP — Metas e Diretrizes da LDO |
| `ConfiguracaoEntidade` | Cabeçalho de todas as exportações |

---

## Modelos adicionados

### `ConfiguracaoEntidade` (tabela `configuracoes_entidade`)

| Campo | Tipo | Descrição |
|---|---|---|
| `cnpj` | str(18) | CNPJ da entidade (XX.XXX.XXX/XXXX-XX) |
| `codigo_ibge` | str(7) | Código IBGE do município (7 dígitos) |
| `uf` | str(2) | Sigla da UF |
| `esfera` | str(20) | Municipal / Estadual / Federal |
| `poder` | str(20) | Executivo / Legislativo / Judiciário |
| `responsavel_nome/cargo/cpf` | str | Dados do gestor responsável |

### `ExportacaoSiconfi` (tabela `exportacoes_siconfi`)

| Campo | Tipo | Descrição |
|---|---|---|
| `tipo` | str(40) | `finbra` \| `rreo` \| `rgf` \| `siop_programas` |
| `exercicio` | int | Ano do exercício fiscal |
| `periodo` | str\|null | ex: `bimestre_3`, `quad_2` |
| `status` | str(20) | `rascunho` \| `validado` |
| `inconsistencias` | int | Nº de inconsistências detectadas na geração |
| `payload_json` | JSON | Snapshot dos dados gerados (auditável) |
| `gerado_por_id` | FK users | Usuário que gerou |

---

## Endpoints

| Método | Rota | Descrição | Roles |
|---|---|---|---|
| GET | `/siconfi/config` | Retorna configuração da entidade | autenticado |
| POST | `/siconfi/config` | Cria/atualiza configuração | admin |
| GET | `/siconfi/validar?exercicio=X` | Lista inconsistências pré-exportação | autenticado |
| GET | `/siconfi/dashboard?exercicio=X` | Resumo executivo de preparação | autenticado |
| GET | `/siconfi/finbra?exercicio=X` | Balanço Orçamentário FINBRA | autenticado |
| GET | `/siconfi/rreo?exercicio=X&bimestre=N` | RREO bimestral estruturado | autenticado |
| GET | `/siconfi/rgf?exercicio=X&quadrimestre=N` | RGF quadrimestral estruturado | autenticado |
| GET | `/siconfi/siop-programas?exercicio=X` | Programas PPA/LOA/LDO para SIOP | autenticado |
| POST | `/siconfi/exportar` | Gera e registra snapshot exportável | admin, accountant |
| GET | `/siconfi/exportacoes` | Lista histórico de exportações | autenticado |

---

## Validações internas (`GET /siconfi/validar`)

| Código | Severidade | Condição |
|---|---|---|
| FY001 | ERRO | Exercício fiscal não cadastrado |
| ENT001 | ERRO | `ConfiguracaoEntidade` não cadastrada |
| ENT002 | ERRO | CNPJ com formato inválido (≠14 dígitos) |
| ENT003 | ERRO | Código IBGE com formato inválido (≠7 dígitos) |
| ENT004 | AVISO | Nome do responsável em branco |
| LOA001 | ERRO | LOA do exercício não encontrada |
| LOA002 | AVISO | LOA em status rascunho |
| LOA003 | AVISO | Receita e despesa da LOA não equilibradas |
| PPA001 | AVISO | Nenhum PPA vigente para o exercício |
| LDO001 | AVISO | LDO do exercício não encontrada |
| EXE001 | AVISO | Despesa paga > Receita arrecadada (deficit de caixa) |
| LRF001 | ERRO | Despesa pessoal > 60% da RCL (LRF art. 19) |
| LRF002 | AVISO | Despesa pessoal > 54% da RCL (alerta prudencial) |

**`pode_exportar = true`** somente quando não há nenhum ERRO.

---

## Idempotência das exportações

- Cada chamada `POST /siconfi/exportar` cria **um novo registro** no log com snapshot do momento
- Múltiplas exportações do mesmo tipo/exercício são permitidas (histórico auditável)
- O status `validado` é atribuído automaticamente quando não há ERROs na validação
- Não há unicidade forçada por `(tipo, exercicio, periodo)` — isso permite reenvio/correção

---

## Premissas e Limitações

| # | Premissa / Limitação |
|---|---|
| 1 | **Sem envio externo**: não realiza chamadas a webservices do Tesouro Nacional. O payload gerado deve ser extraído manualmente ou via script de integração a implementar na Onda 19. |
| 2 | **Classificação funcional simplificada**: `function_code` do LOAItem não é validado contra a tabela de funções SICONFI. Mapeamento real requer adoção do `portaria_mog_42_1999`. |
| 3 | **Despesa pessoal = gross bruto**: `Payslip.gross_amount` é proxy. Encargos patronais (INSS empregador, RPPS) não são incluídos porque não há módulo de previdência própria. |
| 4 | **Natureza de receita não estruturada**: `RevenueEntry` não possui campo de classificação (1.1.x.x.xx). Para SICONFI real, é necessário vincular cada receita à natureza 4-8 dígitos. |
| 5 | **Sem assinatura digital**: exportações para SICONFI real requerem certificado digital ICP-Brasil A3/A1 do gestor. |
| 6 | **Sem XSD validation**: o payload é JSON estruturado. Conversão para XSD SICONFI e validação de schema são passos da Onda 19. |
| 7 | **Sem código de unidade orçamentária (UO)**: SIOP real requer estrutura `órgão/UO/ação/meta`. O modelo atual agrega no nível LOAItem. |
| 8 | **Períodos bimestrais/quadrimestrais aproximados**: calculados por fórmula calendrical simples, sem ajuste para feriados ou datas de publicação DOU. |

---

## Próximas evoluções (Onda 19)

1. **Conversão JSON → XSD SICONFI**: gerar XML validado conforme layout FINBRA/RREO/RGF do Tesouro Nacional
2. **Envio via webservice SICONFI**: `POST /siconfi/enviar` com autenticação via certificado digital A1 (pfx/p12)
3. **Natureza de receita 8 dígitos**: campo adicional em `RevenueEntry` com tabela classificadora
4. **Unidade orçamentária no LOAItem**: campo `orgao_code` + `uo_code` para estrutura SIOP completa
5. **Estrutura programática por UO para SIOP**: mapeamento `PPAProgram` ↔ `LOAItem` via código de programa
6. **Prazo de publicação**: alertas automáticos de prazo RREO/RGF baseados no calendário LRF

---

## Próximo passo ideal

> Com a onda 18 concluída, a decisão entre **envio SICONFI/SIOP (Onda 19)** e
> **auditoria final do TR** depende da prioridade:
>
> - Se o objetivo é demonstrar **aderência legal máxima** para o edital: prosseguir com
>   a Onda 19 (XSD + webservice SICONFI).
> - Se o objetivo é fechar pendências de **gestão interna**: realizar auditoria final do TR
>   (revisar checklist, cobertura de requisitos, geração de PDF de holerite em lote).
>
> **Recomendação**: Onda 19 (SICONFI real) — pois é a fronteira que separa o ERP de
> uma solução legalmente compliant para municípios brasileiros.
