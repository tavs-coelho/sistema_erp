"use client";

import { useEffect, useState } from "react";
import { authJson, authDownload } from "@/lib/auth";

// ── Types ─────────────────────────────────────────────────────────────────────

type LinhaDemonstrat = {
  descricao: string;
  bimestre?: number | null;
  quadrimestre?: number | null;
  acumulado: number;
};

type RREOIndicadores = {
  saldo_execucao_acumulado: number;
  pct_receita_realizada: number;
  pct_despesa_executada: number;
  resultado: "superavit" | "deficit";
};

type RGFIndicadores = {
  rcl_12meses: number;
  despesa_pessoal_acumulada: number;
  limite_pessoal_60pct_rcl: number;
  pct_despesa_pessoal_rcl: number;
  excesso_despesa_pessoal: number;
  situacao_despesa_pessoal: "REGULAR" | "ALERTA" | "EXCEDIDO";
  divida_consolidada: number;
  disponibilidade_financeira: number;
  saldo_exercicio: number;
};

type RREOResponse = {
  cabecalho: { exercicio: number; bimestre: number; referencia: string; periodo_bimestre: { inicio: string; fim: string } };
  linhas: LinhaDemonstrat[];
  indicadores: RREOIndicadores;
};

type RGFResponse = {
  cabecalho: { exercicio: number; quadrimestre: number; referencia: string; periodo_quadrimestre: { inicio: string; fim: string } };
  linhas: LinhaDemonstrat[];
  indicadores: RGFIndicadores;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtBRL(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
function fmtPct(v: number) { return `${v.toFixed(2)}%`; }
function msgFrom(e: unknown) { return e instanceof Error ? e.message : "Falha na operação"; }

const thisYear = new Date().getFullYear();
const thisBimestre = Math.min(6, Math.floor((new Date().getMonth()) / 2) + 1);
const thisQuadrimestre = Math.min(3, Math.floor((new Date().getMonth()) / 4) + 1);

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LRFPage() {
  const [tab, setTab] = useState<"rreo" | "rgf">("rreo");
  const [msg, setMsg] = useState("");
  const isError = msg.toLowerCase().includes("erro") || msg.toLowerCase().includes("falha");

  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Demonstrativos LRF</h1>
      <p className="muted">
        Relatórios da Lei de Responsabilidade Fiscal — base legal: LRF art. 52-55.
      </p>

      {msg && (
        <div className={`alert ${isError ? "error" : "success"}`} style={{ marginBottom: 8 }}>
          {msg}
        </div>
      )}

      <nav style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {(["rreo", "rgf"] as const).map((t) => (
          <button key={t} className={`tab-btn ${tab === t ? "active" : ""}`}
            onClick={() => { setTab(t); setMsg(""); }}>
            {t === "rreo" ? "RREO (art. 52-53)" : "RGF (art. 55)"}
          </button>
        ))}
      </nav>

      {tab === "rreo" && <RREOTab setMsg={setMsg} />}
      {tab === "rgf" && <RGFTab setMsg={setMsg} />}
    </main>
  );
}

// ── RREO ──────────────────────────────────────────────────────────────────────

function RREOTab({ setMsg }: { setMsg: (m: string) => void }) {
  const [data, setData] = useState<RREOResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [ano, setAno] = useState(String(thisYear));
  const [bimestre, setBimestre] = useState(String(thisBimestre));

  const load = async () => {
    setLoading(true);
    try {
      setData(await authJson(`/lrf/rreo?ano=${ano}&bimestre=${bimestre}`));
      setMsg("");
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
    setLoading(false);
  };

  const exportCsv = async () => {
    try {
      await authDownload(`/lrf/rreo?ano=${ano}&bimestre=${bimestre}&export=csv`,
        `rreo_${ano}_bim${bimestre}.csv`);
    } catch (e) { setMsg("Erro ao exportar: " + msgFrom(e)); }
  };

  useEffect(() => { load(); }, []);

  const ind = data?.indicadores;
  const linhas = data?.linhas || [];

  const situacaoColor = ind?.resultado === "superavit" ? "#28a745" : "#dc3545";

  return (
    <section className="section-stack">
      <h2>RREO — Relatório Resumido da Execução Orçamentária</h2>
      <p className="muted" style={{ fontSize: 13 }}>
        Publicação bimestral — LRF art. 52-53. Confronta receita prevista vs. arrecadada e
        despesa autorizada vs. executada.
      </p>

      <div className="toolbar" style={{ gap: 8, marginBottom: 12 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
          Exercício
          <input type="number" value={ano} min={2020} max={2100} style={{ width: 80 }}
            onChange={(e) => setAno(e.target.value)} />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
          Bimestre
          <select value={bimestre} onChange={(e) => setBimestre(e.target.value)} style={{ width: 60 }}>
            {[1, 2, 3, 4, 5, 6].map((b) => <option key={b} value={b}>{b}º</option>)}
          </select>
        </label>
        <button className="btn" onClick={load} disabled={loading}>
          {loading ? "Carregando..." : "Gerar"}
        </button>
        <button className="btn" style={{ background: "#28a745", color: "white" }} onClick={exportCsv}>
          ⬇ CSV
        </button>
      </div>

      {data && (
        <p style={{ fontSize: 13, color: "#6c757d", marginBottom: 8 }}>
          {data.cabecalho.referencia} &nbsp;|&nbsp;
          {data.cabecalho.periodo_bimestre.inicio} a {data.cabecalho.periodo_bimestre.fim} &nbsp;|&nbsp;
          <strong style={{ color: situacaoColor }}>
            {ind?.resultado?.toUpperCase()}
          </strong>
        </p>
      )}

      {ind && (
        <div className="kpi-grid" style={{ marginBottom: 12 }}>
          <div className="kpi-card">
            <span className="kpi-label">Saldo Execução (acumulado)</span>
            <span className="kpi-value" style={{ color: situacaoColor }}>
              {fmtBRL(ind.saldo_execucao_acumulado)}
            </span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">% Receita Realizada</span>
            <span className="kpi-value">{fmtPct(ind.pct_receita_realizada)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">% Despesa Executada</span>
            <span className="kpi-value">{fmtPct(ind.pct_despesa_executada)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Resultado</span>
            <span className="kpi-value" style={{ color: situacaoColor }}>
              {ind.resultado === "superavit" ? "Superávit" : "Déficit"}
            </span>
          </div>
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>Descrição</th>
            <th style={{ textAlign: "right" }}>No Bimestre</th>
            <th style={{ textAlign: "right" }}>Acumulado no Ano</th>
          </tr>
        </thead>
        <tbody>
          {linhas.length ? linhas.map((l, i) => (
            <tr key={i}>
              <td>{l.descricao}</td>
              <td style={{ textAlign: "right" }}>
                {l.bimestre != null ? fmtBRL(l.bimestre) : "—"}
              </td>
              <td style={{ textAlign: "right" }}><strong>{fmtBRL(l.acumulado)}</strong></td>
            </tr>
          )) : (
            <tr><td colSpan={3} className="empty-state">Nenhum dado encontrado.</td></tr>
          )}
        </tbody>
      </table>
    </section>
  );
}

// ── RGF ───────────────────────────────────────────────────────────────────────

function RGFTab({ setMsg }: { setMsg: (m: string) => void }) {
  const [data, setData] = useState<RGFResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [ano, setAno] = useState(String(thisYear));
  const [quad, setQuad] = useState(String(thisQuadrimestre));

  const load = async () => {
    setLoading(true);
    try {
      setData(await authJson(`/lrf/rgf?ano=${ano}&quadrimestre=${quad}`));
      setMsg("");
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
    setLoading(false);
  };

  const exportCsv = async () => {
    try {
      await authDownload(`/lrf/rgf?ano=${ano}&quadrimestre=${quad}&export=csv`,
        `rgf_${ano}_quad${quad}.csv`);
    } catch (e) { setMsg("Erro ao exportar: " + msgFrom(e)); }
  };

  useEffect(() => { load(); }, []);

  const ind = data?.indicadores as RGFIndicadores | undefined;
  const linhas = data?.linhas || [];

  const situacaoColor = !ind ? "#495057"
    : ind.situacao_despesa_pessoal === "EXCEDIDO" ? "#dc3545"
    : ind.situacao_despesa_pessoal === "ALERTA" ? "#fd7e14"
    : "#28a745";

  return (
    <section className="section-stack">
      <h2>RGF — Relatório de Gestão Fiscal</h2>
      <p className="muted" style={{ fontSize: 13 }}>
        Publicação quadrimestral — LRF art. 55. Apura despesa com pessoal, dívida consolidada
        e disponibilidade financeira. Limite pessoal: 60 % da RCL (municípios).
      </p>

      <div className="toolbar" style={{ gap: 8, marginBottom: 12 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
          Exercício
          <input type="number" value={ano} min={2020} max={2100} style={{ width: 80 }}
            onChange={(e) => setAno(e.target.value)} />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
          Quadrimestre
          <select value={quad} onChange={(e) => setQuad(e.target.value)} style={{ width: 60 }}>
            {[1, 2, 3].map((q) => <option key={q} value={q}>{q}º</option>)}
          </select>
        </label>
        <button className="btn" onClick={load} disabled={loading}>
          {loading ? "Carregando..." : "Gerar"}
        </button>
        <button className="btn" style={{ background: "#28a745", color: "white" }} onClick={exportCsv}>
          ⬇ CSV
        </button>
      </div>

      {data && (
        <p style={{ fontSize: 13, color: "#6c757d", marginBottom: 8 }}>
          {data.cabecalho.referencia} &nbsp;|&nbsp;
          {data.cabecalho.periodo_quadrimestre.inicio} a {data.cabecalho.periodo_quadrimestre.fim}
        </p>
      )}

      {ind && (
        <div className="kpi-grid" style={{ marginBottom: 12 }}>
          <div className="kpi-card">
            <span className="kpi-label">RCL 12 meses</span>
            <span className="kpi-value">{fmtBRL(ind.rcl_12meses)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Despesa Pessoal (acumulado)</span>
            <span className="kpi-value">{fmtBRL(ind.despesa_pessoal_acumulada)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">% Pessoal / RCL</span>
            <span className="kpi-value" style={{ color: situacaoColor }}>
              {fmtPct(ind.pct_despesa_pessoal_rcl)}
              &nbsp;<small>(limite 60 %)</small>
            </span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Situação Pessoal</span>
            <span className="kpi-value" style={{ color: situacaoColor, fontSize: 16 }}>
              {ind.situacao_despesa_pessoal}
            </span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Dívida Consolidada</span>
            <span className="kpi-value">{fmtBRL(ind.divida_consolidada)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Disponibilidade Financeira</span>
            <span className="kpi-value" style={{ color: ind.disponibilidade_financeira >= 0 ? "#28a745" : "#dc3545" }}>
              {fmtBRL(ind.disponibilidade_financeira)}
            </span>
          </div>
        </div>
      )}

      {ind?.situacao_despesa_pessoal === "EXCEDIDO" && (
        <div className="alert error" style={{ marginBottom: 12 }}>
          ⚠ Despesa com pessoal excede o limite legal (60 % RCL).
          Excesso: {fmtBRL(ind.excesso_despesa_pessoal)}. Medidas de contenção são obrigatórias (LRF art. 23).
        </div>
      )}
      {ind?.situacao_despesa_pessoal === "ALERTA" && (
        <div className="alert" style={{ marginBottom: 12, background: "#fff3cd", borderColor: "#ffc107", color: "#856404" }}>
          ⚠ Despesa com pessoal atingiu a faixa de alerta prudencial (54 % RCL).
          Novas despesas de pessoal são vedadas (LRF art. 22).
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>Descrição</th>
            <th style={{ textAlign: "right" }}>No Quadrimestre</th>
            <th style={{ textAlign: "right" }}>Acumulado no Ano</th>
          </tr>
        </thead>
        <tbody>
          {linhas.length ? linhas.map((l, i) => (
            <tr key={i}>
              <td>{l.descricao}</td>
              <td style={{ textAlign: "right" }}>
                {(l as any).quadrimestre != null ? fmtBRL((l as any).quadrimestre) : "—"}
              </td>
              <td style={{ textAlign: "right" }}><strong>{fmtBRL(l.acumulado)}</strong></td>
            </tr>
          )) : (
            <tr><td colSpan={3} className="empty-state">Nenhum dado encontrado.</td></tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
