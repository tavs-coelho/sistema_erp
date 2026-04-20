"""Geração de XML SICONFI — Onda 19 Fase 1.

Este módulo converte os payloads JSON da Onda 18 para XML estruturado
compatível com o layout SICONFI/FINBRA/RREO/RGF, e valida localmente
contra XSD inline (aproximado do layout Tesouro Nacional).

NOTAS SOBRE OS LAYOUTS:
  - Os XSD aqui são *aproximações* do layout publicado pelo Tesouro Nacional
    em https://siconfi.tesouro.gov.br. A estrutura real pode diferir em
    versões futuras dos webservices.
  - Os campos de identificação (cod_municipio, cnpj, cod_ibge) devem ser
    configurados em ConfiguracaoEntidade antes de gerar.
  - Os valores monetários são exprestos em R$ com 2 casas decimais.
  - Para envio real (Fase 2) o XML deve ser assinado digitalmente com
    certificado ICP-Brasil A1/A3 antes de postar no webservice.

ESTRUTURA DO XML GERADO:
  <SiconfiRelatorio versao="1.0" tipo="FINBRA|RREO|RGF">
    <Cabecalho>
      <NomeEntidade/><CNPJ/><CodigoIBGE/><UF/><Esfera/><Poder/>
      <Exercicio/><Periodo/><DataGeracao/>
    </Cabecalho>
    <Dados>
      ... conteúdo específico de cada relatório ...
    </Dados>
  </SiconfiRelatorio>
"""

from __future__ import annotations

import textwrap
from datetime import date
from typing import Any

from lxml import etree

# ── XSD inline (aproximação) ──────────────────────────────────────────────────

_XSD_SICONFI_BASE = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">

  <xs:element name="SiconfiRelatorio">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="Cabecalho" type="TipoCabecalho"/>
        <xs:element name="Dados" type="TipoDadosAberto"/>
      </xs:sequence>
      <xs:attribute name="versao" type="xs:string" use="required"/>
      <xs:attribute name="tipo"   type="xs:string" use="required"/>
    </xs:complexType>
  </xs:element>

  <xs:complexType name="TipoCabecalho">
    <xs:sequence>
      <xs:element name="NomeEntidade"  type="xs:string"  minOccurs="1"/>
      <xs:element name="CNPJ"          type="TipoCNPJ"   minOccurs="1"/>
      <xs:element name="CodigoIBGE"    type="TipoIBGE"   minOccurs="1"/>
      <xs:element name="UF"            type="TipoUF"     minOccurs="1"/>
      <xs:element name="Esfera"        type="xs:string"  minOccurs="1"/>
      <xs:element name="Poder"         type="xs:string"  minOccurs="1"/>
      <xs:element name="Exercicio"     type="xs:integer" minOccurs="1"/>
      <xs:element name="Periodo"       type="xs:string"  minOccurs="1"/>
      <xs:element name="DataGeracao"   type="xs:date"    minOccurs="1"/>
      <xs:element name="Responsavel"   type="TipoResponsavel" minOccurs="0"/>
    </xs:sequence>
  </xs:complexType>

  <xs:complexType name="TipoResponsavel">
    <xs:sequence>
      <xs:element name="Nome"  type="xs:string" minOccurs="0"/>
      <xs:element name="Cargo" type="xs:string" minOccurs="0"/>
      <xs:element name="CPF"   type="xs:string" minOccurs="0"/>
    </xs:sequence>
  </xs:complexType>

  <!-- Dados é aberto para acomodar FINBRA / RREO / RGF / SIOP com conteúdo variável -->
  <xs:complexType name="TipoDadosAberto">
    <xs:sequence>
      <xs:any minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
    </xs:sequence>
  </xs:complexType>

  <xs:simpleType name="TipoCNPJ">
    <xs:restriction base="xs:string">
      <xs:pattern value="\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}"/>
    </xs:restriction>
  </xs:simpleType>

  <xs:simpleType name="TipoIBGE">
    <xs:restriction base="xs:string">
      <xs:minLength value="7"/>
      <xs:maxLength value="7"/>
      <xs:pattern value="\\d{7}"/>
    </xs:restriction>
  </xs:simpleType>

  <xs:simpleType name="TipoUF">
    <xs:restriction base="xs:string">
      <xs:minLength value="2"/>
      <xs:maxLength value="2"/>
    </xs:restriction>
  </xs:simpleType>

</xs:schema>
"""

_XSD_FINBRA_DADOS = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="BalancoOrcamentario">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="Receitas"  type="TipoReceitas"/>
        <xs:element name="Despesas"  type="TipoDespesas"/>
        <xs:element name="IndicadoresLRF" type="TipoIndicadoresLRF"/>
        <xs:element name="Resultado" type="TipoResultado"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>

  <xs:complexType name="TipoReceitas">
    <xs:sequence>
      <xs:element name="ReceitaPrevista"     type="xs:decimal"/>
      <xs:element name="ReceitaArrecadada"   type="xs:decimal"/>
      <xs:element name="Diferenca"           type="xs:decimal"/>
      <xs:element name="PctRealizacao"       type="xs:decimal"/>
    </xs:sequence>
  </xs:complexType>

  <xs:complexType name="TipoDespesas">
    <xs:sequence>
      <xs:element name="DotacaoAutorizada" type="xs:decimal"/>
      <xs:element name="Empenhada"         type="xs:decimal"/>
      <xs:element name="Liquidada"         type="xs:decimal"/>
      <xs:element name="Paga"              type="xs:decimal"/>
      <xs:element name="SaldoAPagar"       type="xs:decimal"/>
    </xs:sequence>
  </xs:complexType>

  <xs:complexType name="TipoIndicadoresLRF">
    <xs:sequence>
      <xs:element name="RCL12Meses"            type="xs:decimal"/>
      <xs:element name="DespesaPessoalBruta"   type="xs:decimal"/>
      <xs:element name="PctPessoalRCL"         type="xs:decimal"/>
      <xs:element name="LimitePessoal60Pct"    type="xs:decimal"/>
      <xs:element name="SituacaoPessoal"       type="xs:string"/>
      <xs:element name="DividaConsolidada"     type="xs:decimal"/>
    </xs:sequence>
  </xs:complexType>

  <xs:complexType name="TipoResultado">
    <xs:sequence>
      <xs:element name="Receita" type="xs:decimal"/>
      <xs:element name="Despesa" type="xs:decimal"/>
      <xs:element name="Saldo"   type="xs:decimal"/>
      <xs:element name="Tipo"    type="xs:string"/>
    </xs:sequence>
  </xs:complexType>
</xs:schema>
"""


# ── Helpers XML ───────────────────────────────────────────────────────────────

def _elem(parent: etree._Element, tag: str, text: str | None = None) -> etree._Element:
    e = etree.SubElement(parent, tag)
    if text is not None:
        e.text = str(text)
    return e


def _money(v: float) -> str:
    return f"{v:.2f}"


# ── Cabeçalho ────────────────────────────────────────────────────────────────

def _build_cabecalho(
    root: etree._Element,
    cfg: dict,
    exercicio: int,
    periodo: str,
) -> None:
    cab = _elem(root, "Cabecalho")
    _elem(cab, "NomeEntidade", cfg.get("nome_entidade", ""))
    _elem(cab, "CNPJ", cfg.get("cnpj", ""))
    _elem(cab, "CodigoIBGE", cfg.get("codigo_ibge", ""))
    _elem(cab, "UF", cfg.get("uf", ""))
    _elem(cab, "Esfera", cfg.get("esfera", "Municipal"))
    _elem(cab, "Poder", cfg.get("poder", "Executivo"))
    _elem(cab, "Exercicio", str(exercicio))
    _elem(cab, "Periodo", periodo)
    _elem(cab, "DataGeracao", date.today().isoformat())
    if cfg.get("responsavel_nome"):
        resp = _elem(cab, "Responsavel")
        _elem(resp, "Nome", cfg.get("responsavel_nome", ""))
        _elem(resp, "Cargo", cfg.get("responsavel_cargo", ""))
        _elem(resp, "CPF", cfg.get("responsavel_cpf", ""))


# ── FINBRA XML ────────────────────────────────────────────────────────────────

def build_xml_finbra(payload: dict, cfg: dict) -> bytes:
    """Converte payload FINBRA (JSON) para XML SICONFI."""
    exercicio = payload["cabecalho"]["exercicio"]
    root = etree.Element("SiconfiRelatorio", versao="1.0", tipo="FINBRA")
    _build_cabecalho(root, cfg, exercicio, "ANUAL")

    dados = _elem(root, "Dados")
    bal = _elem(dados, "BalancoOrcamentario")

    rec = _elem(bal, "Receitas")
    br = payload["balanco_receita"]
    _elem(rec, "ReceitaPrevista",   _money(br["receita_prevista_loa"]))
    _elem(rec, "ReceitaArrecadada", _money(br["receita_arrecadada"]))
    _elem(rec, "Diferenca",         _money(br["diferenca_arrecadamento"]))
    _elem(rec, "PctRealizacao",     _money(br["pct_realizacao"]))

    dep = _elem(bal, "Despesas")
    bd = payload["balanco_despesa"]
    _elem(dep, "DotacaoAutorizada", _money(bd["dotacao_autorizada"]))
    _elem(dep, "Empenhada",         _money(bd["despesa_empenhada"]))
    _elem(dep, "Liquidada",         _money(bd["despesa_liquidada"]))
    _elem(dep, "Paga",              _money(bd["despesa_paga"]))
    _elem(dep, "SaldoAPagar",       _money(bd["saldo_a_pagar"]))

    ind = _elem(bal, "IndicadoresLRF")
    il = payload["indicadores_lrf"]
    _elem(ind, "RCL12Meses",          _money(il["rcl_12meses"]))
    _elem(ind, "DespesaPessoalBruta", _money(il["despesa_pessoal_bruta"]))
    _elem(ind, "PctPessoalRCL",       _money(il["pct_pessoal_rcl"]))
    _elem(ind, "LimitePessoal60Pct",  _money(il["limite_pessoal_60pct"]))
    _elem(ind, "SituacaoPessoal",     il["situacao_pessoal"])
    _elem(ind, "DividaConsolidada",   _money(il["divida_consolidada"]))

    res = _elem(bal, "Resultado")
    rr = payload["resultado_exercicio"]
    _elem(res, "Receita", _money(rr["receita"]))
    _elem(res, "Despesa", _money(rr["despesa"]))
    _elem(res, "Saldo",   _money(rr["saldo"]))
    _elem(res, "Tipo",    rr["tipo"])

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")


# ── RREO XML ──────────────────────────────────────────────────────────────────

def build_xml_rreo(payload: dict, cfg: dict) -> bytes:
    """Converte payload RREO bimestral para XML SICONFI."""
    exercicio = payload["cabecalho"]["exercicio"]
    bimestre = payload["cabecalho"]["bimestre"]
    periodo = f"BIMESTRE_{bimestre}"

    root = etree.Element("SiconfiRelatorio", versao="1.0", tipo="RREO")
    _build_cabecalho(root, cfg, exercicio, periodo)

    dados = _elem(root, "Dados")
    rreo = _elem(dados, "BalancoOrcamentarioBimestral")
    _elem(rreo, "Bimestre", str(bimestre))
    _elem(rreo, "PeriodoInicio", payload["cabecalho"]["periodo"]["inicio"])
    _elem(rreo, "PeriodoFim",    payload["cabecalho"]["periodo"]["fim"])

    rec = _elem(rreo, "Receitas")
    r = payload["receitas"]
    _elem(rec, "PrevistaLOA",        _money(r["prevista_loa"]))
    _elem(rec, "ArrecadadaBimestre", _money(r["arrecadada_bimestre"]))
    _elem(rec, "ArrecadadaAcumulada",_money(r["arrecadada_acumulada"]))

    dep = _elem(rreo, "DespesasTotais")
    dt = payload["despesas_totais"]
    _elem(dep, "EmpenhadaExercicio",    _money(dt["empenhada_exercicio"]))
    _elem(dep, "LiquidadaBimestre",     _money(dt["liquidada_bimestre"]))
    _elem(dep, "PagaBimestre",          _money(dt["paga_bimestre"]))
    _elem(dep, "PagaAcumulada",         _money(dt["paga_acumulada"]))

    if payload.get("despesas_por_funcao"):
        funcs = _elem(rreo, "DespesasPorFuncao")
        for f in payload["despesas_por_funcao"]:
            linha = _elem(funcs, "Funcao")
            _elem(linha, "Codigo",             f["function_code"])
            _elem(linha, "DotacaoAutorizada",  _money(f["dotacao_autorizada"]))
            _elem(linha, "DotacaoExecutada",   _money(f["dotacao_executada"]))

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")


# ── RGF XML ───────────────────────────────────────────────────────────────────

def build_xml_rgf(payload: dict, cfg: dict) -> bytes:
    """Converte payload RGF quadrimestral para XML SICONFI."""
    exercicio = payload["cabecalho"]["exercicio"]
    quad = payload["cabecalho"]["quadrimestre"]
    periodo = f"QUADRIMESTRE_{quad}"

    root = etree.Element("SiconfiRelatorio", versao="1.0", tipo="RGF")
    _build_cabecalho(root, cfg, exercicio, periodo)

    dados = _elem(root, "Dados")
    rgf = _elem(dados, "RelatorioGestaoFiscal")
    _elem(rgf, "Quadrimestre", str(quad))
    _elem(rgf, "PeriodoInicio", payload["cabecalho"]["periodo"]["inicio"])
    _elem(rgf, "PeriodoFim",    payload["cabecalho"]["periodo"]["fim"])

    dp = _elem(rgf, "DespesaPessoal")
    d = payload["despesa_pessoal"]
    _elem(dp, "Quadrimestre",      _money(d["quadrimestre"]))
    _elem(dp, "AcumuladaAno",      _money(d["acumulada_ano"]))
    _elem(dp, "RCL12Meses",        _money(d["rcl_12meses"]))
    _elem(dp, "LimiteLegal60Pct",  _money(d["limite_legal_60pct"]))
    _elem(dp, "LimiteAlerta54Pct", _money(d["limite_alerta_54pct"]))
    _elem(dp, "PctRCL",            _money(d["pct_rcl"]))
    _elem(dp, "Excesso",           _money(d["excesso"]))
    _elem(dp, "Situacao",          d["situacao"])

    dc = _elem(rgf, "DividaConsolidada")
    _elem(dc, "Saldo", _money(payload["divida_consolidada"]["saldo"]))

    df = _elem(rgf, "DisponibilidadeFinanceira")
    dispf = payload["disponibilidade_financeira"]
    _elem(df, "ReceitaAcumulada",  _money(dispf["receita_acumulada"]))
    _elem(df, "DespesaPagaAcumulada", _money(dispf["despesa_paga_acumulada"]))
    _elem(df, "Saldo",             _money(dispf["saldo"]))

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")


# ── Validação XSD ─────────────────────────────────────────────────────────────

def _parse_schema(xsd_str: str) -> etree.XMLSchema:
    schema_doc = etree.fromstring(xsd_str.encode())
    return etree.XMLSchema(schema_doc)


def validate_xml(xml_bytes: bytes, tipo: str) -> tuple[bool, list[str], list[str]]:
    """Valida XML contra XSD base + XSD de dados (inline).

    Retorna:
        (valido: bool, erros: list[str], avisos: list[str])
    """
    erros: list[str] = []
    avisos: list[str] = []

    # Parse XML
    try:
        doc = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        return False, [f"XML mal formado: {e}"], []

    # Validação XSD base (cabeçalho obrigatório)
    try:
        schema_base = _parse_schema(_XSD_SICONFI_BASE)
        schema_base.assertValid(doc)
    except etree.DocumentInvalid as e:
        erros.extend([str(err) for err in schema_base.error_log])

    # Validação XSD dos dados específicos (apenas FINBRA tem XSD detalhado inline)
    if tipo == "finbra":
        dados_el = doc.find("Dados")
        if dados_el is not None:
            # Extrai apenas o elemento BalancoOrcamentario para validar
            bal_el = dados_el.find("BalancoOrcamentario")
            if bal_el is not None:
                try:
                    schema_finbra = _parse_schema(_XSD_FINBRA_DADOS)
                    schema_finbra.assertValid(bal_el)
                except etree.DocumentInvalid:
                    erros.extend([str(err) for err in schema_finbra.error_log])
            else:
                erros.append("FINBRA: elemento BalancoOrcamentario ausente em <Dados>")

    # Verificações semânticas adicionais (avisos, não erros XSD)
    cab = doc.find("Cabecalho")
    if cab is not None:
        cnpj_el = cab.find("CNPJ")
        if cnpj_el is not None:
            cnpj = (cnpj_el.text or "").replace(".", "").replace("/", "").replace("-", "")
            if len(cnpj) != 14:
                erros.append(f"CNPJ inválido: '{cnpj_el.text}' (esperado 14 dígitos)")

        ibge_el = cab.find("CodigoIBGE")
        if ibge_el is not None and (ibge_el.text or "") == "":
            erros.append("CodigoIBGE vazio — obrigatório para envio SICONFI")

        resp_el = cab.find("Responsavel/Nome")
        if resp_el is None or not (resp_el.text or "").strip():
            avisos.append("Responsável não informado no cabeçalho (requerido para assinatura digital)")

    # Aviso sobre itens ainda não conformes com o layout real do Tesouro
    avisos.append(
        "XSD utilizado é aproximação inline — valide contra o XSD oficial do "
        "Tesouro Nacional em https://siconfi.tesouro.gov.br antes do envio real."
    )

    valido = len(erros) == 0
    return valido, erros, avisos


# ── Utilitário: XML → string (trunca em 50 KB para storage) ──────────────────

MAX_XML_STORE = 50 * 1024  # 50 KB


def xml_bytes_to_str(xml_bytes: bytes, max_bytes: int = MAX_XML_STORE) -> str:
    s = xml_bytes.decode("utf-8")
    if len(s) > max_bytes:
        s = s[:max_bytes] + "\n<!-- [TRUNCADO — arquivo completo disponível via endpoint] -->"
    return s
