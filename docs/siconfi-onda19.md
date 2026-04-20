# SICONFI Onda 19 — Integração Real em Duas Fases

## Objetivo

Avançar da *camada preparatória* (Onda 18) para a *prestação de contas efetiva*,
convertendo os payloads JSON para XML estruturado, validando localmente contra XSD,
e preparando a infraestrutura para o envio via webservice do Tesouro Nacional.

---

## Fase 1 — Geração XML + Validação Local ✅ (implementado)

### O que foi implementado

| # | Item | Arquivo/Rota |
|---|---|---|
| 1 | Módulo `siconfi_xml.py` — builders XML para FINBRA, RREO, RGF | `app/siconfi_xml.py` |
| 2 | XSD inline (base + FINBRA) — aproximação do layout Tesouro Nacional | `app/siconfi_xml.py` |
| 3 | `GET /siconfi/xml/finbra` — JSON ou `?download=true` (application/xml) | `routers/siconfi_xml.py` |
| 4 | `GET /siconfi/xml/rreo?bimestre=N` — RREO bimestral | |
| 5 | `GET /siconfi/xml/rgf?quadrimestre=N` — RGF quadrimestral | |
| 6 | `POST /siconfi/xml/validar` — validação avulsa por tipo/período | |
| 7 | `GET /siconfi/xml/{id}/download` — download do XML de uma validação salva | |
| 8 | `GET /siconfi/xml/historico` — histórico paginado com filtros | |
| 9 | Model `ValidacaoXmlLog` — log de cada validação (exercicio, valido, erros, xml) | `app/models.py` |
| 10 | Model `EnvioSiconfiLog` — stub para log de envio real (Fase 2) | `app/models.py` |
| 11 | Migration `0016_siconfi_xml` | `alembic/versions/` |
| 12 | Fase 2 stub `POST /siconfi/envio` — retorna 501 com lista de pré-requisitos | |
| 13 | `GET /siconfi/envio/historico` — histórico de envios (vazio até Fase 2) | |
| 14 | 37 testes `test_siconfi_xml.py` | `tests/` |
| 15 | Frontend — aba "XML / Onda 19" em `/siconfi-siop` | `frontend/siconfi-siop/page.tsx` |

### Estrutura do XML gerado

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SiconfiRelatorio versao="1.0" tipo="FINBRA">
  <Cabecalho>
    <NomeEntidade>Prefeitura Municipal de Demo</NomeEntidade>
    <CNPJ>12.345.678/0001-90</CNPJ>
    <CodigoIBGE>1234567</CodigoIBGE>
    <UF>SP</UF>
    <Esfera>Municipal</Esfera>
    <Poder>Executivo</Poder>
    <Exercicio>2025</Exercicio>
    <Periodo>ANUAL</Periodo>
    <DataGeracao>2025-12-31</DataGeracao>
    <Responsavel>
      <Nome>João Silva</Nome>
      <Cargo>Prefeito</Cargo>
      <CPF>000.000.000-01</CPF>
    </Responsavel>
  </Cabecalho>
  <Dados>
    <BalancoOrcamentario>
      <Receitas>...</Receitas>
      <Despesas>...</Despesas>
      <IndicadoresLRF>...</IndicadoresLRF>
      <Resultado>...</Resultado>
    </BalancoOrcamentario>
  </Dados>
</SiconfiRelatorio>
```

### Validações XSD realizadas

| Código | Tipo | Condição |
|---|---|---|
| XSD-BASE | Erro | Cabeçalho (NomeEntidade, CNPJ, CodigoIBGE, UF, Exercicio, Periodo) obrigatórios |
| XSD-CNPJ | Erro | CNPJ deve corresponder ao padrão `XX.XXX.XXX/XXXX-XX` (14 dígitos) |
| XSD-IBGE | Erro | CodigoIBGE deve ter exatamente 7 dígitos |
| XSD-FINBRA | Erro | Estrutura de Receitas/Despesas/IndicadoresLRF obrigatória para FINBRA |
| SEM-RESP | Aviso | Responsável não informado (obrigatório para assinatura digital) |
| SEM-IBGE | Erro | CodigoIBGE vazio bloqueia envio SICONFI |
| XSD-FONTE | Aviso | XSD inline — validar contra XSD oficial do Tesouro antes do envio |

---

## Fase 2 — Envio Real (pendente) ⏳

### Endpoint stub disponível

```http
POST /siconfi/envio
Authorization: Bearer <token>   (role: admin)

{
  "validacao_xml_id": 42,
  "certificado_pfx_base64": "<base64>",
  "certificado_senha": "senha123",
  "url_webservice": "https://siconfi.tesouro.gov.br/siconfi/api/...",
  "dry_run": true
}
```

Retorna `501 Not Implemented` com lista de pré-requisitos.

### Pré-requisitos para Fase 2

| # | Pré-requisito | Como obter |
|---|---|---|
| 1 | **Credenciais gov.br** (usuário SICONFI) | Cadastro no portal SICONFI pelo gestor |
| 2 | **Certificado ICP-Brasil A1/A3** do responsável | Autoridade Certificadora credenciada (Serpro, Certisign, etc.) |
| 3 | **WSDL do webservice SICONFI** | https://siconfi.tesouro.gov.br/siconfi/pages/publico/arquivos/ |
| 4 | **Biblioteca WS-Security** (assinatura XML) | `signxml` (PyPI) ou `zeep` com plugin de assinatura |
| 5 | **XSD oficial validado** | Layout FINBRA/RREO/RGF publicado pelo Tesouro Nacional |

### Fluxo técnico planejado (Fase 2)

```
1. Carregar PFX (base64 → bytes) → extrair chave privada + certificado
2. Gerar XML via siconfi_xml.py (Fase 1)
3. Assinar XML com WS-Security (canonicalização C14N + RSA-SHA256)
4. Postar no endpoint SOAP/REST do SICONFI
5. Receber protocolo → salvar em EnvioSiconfiLog
6. Em caso de erro: salvar resposta_raw + erro_detalhe + incrementar tentativas
7. Reprocessamento: novo POST reutiliza validacao_xml_id anterior
```

### Schema de EnvioSiconfiLog (pronto para Fase 2)

| Campo | Tipo | Descrição |
|---|---|---|
| `status` | str | `pendente → enviado \| falha \| cancelado` |
| `protocolo` | str | Nº de protocolo retornado pelo SICONFI |
| `http_status` | int | Status HTTP da resposta |
| `resposta_raw` | text | Resposta bruta do webservice (XML SOAP) |
| `erro_detalhe` | text | Mensagem de erro estruturada |
| `certificado_serial` | str | Serial do certificado utilizado (sem chave) |
| `tentativas` | int | Contador de tentativas (reprocessamento) |

---

## Limitações conhecidas da Fase 1

| # | Limitação |
|---|---|
| 1 | XSD inline é aproximação — o Tesouro Nacional pode ter versões diferentes |
| 2 | Sem assinatura XML (WS-Security) — obrigatória para envio real |
| 3 | Nomenclatura dos elementos XML pode divergir do WSDL oficial |
| 4 | Sem suporte a SIOP programático (SIOP tem API REST separada do SICONFI) |
| 5 | `xml_gerado` é truncado a 50 KB no banco — arquivo completo via endpoint download |

---

## Próximo passo: Auditoria final do TR em paralelo?

**Sim — recomendado fazer em paralelo.**

| Atividade | Dependência | Pode rodar agora? |
|---|---|---|
| Auditoria final do TR (checklist requisitos) | Nenhuma | ✅ Sim |
| Fase 2 SICONFI (envio real) | Certificado A1 + credenciais gov.br | ❌ Depende do cliente |

A Fase 2 depende de artefatos externos (certificado ICP-Brasil, credenciais SICONFI)
que estão fora do controle do ERP. A auditoria do TR é puramente interna e pode
ser iniciada imediatamente, identificando lacunas de requisitos antes da entrega final.

**Recomendação:** iniciar auditoria final do TR agora, deixar Fase 2 para quando
o cliente fornecer o certificado digital e as credenciais SICONFI.
