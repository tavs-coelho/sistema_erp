"use client";

import { useEffect, useState } from "react";
import { authJson, authDownload } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/cn";

// ── Types ─────────────────────────────────────────────────────────────────────

type VeiculoRow = {
  veiculo_id: number; placa: string; descricao: string; tipo: string;
  combustivel: string; departamento_id: number | null;
  n_abastecimentos: number; total_litros: number; custo_abastecimento: number;
  n_manutencoes: number; custo_manutencao_servico: number;
  n_pecas_almoxarifado: number; custo_pecas_almoxarifado: number; custo_total: number;
};

type DeptRow = {
  departamento_id: number | null; departamento_nome: string;
  n_abastecimentos: number; total_litros: number; custo_abastecimento: number;
  n_manutencoes: number; custo_manutencao_servico: number;
  n_pecas_almoxarifado: number; custo_pecas_almoxarifado: number; custo_total: number;
};

type Totais = {
  total_geral: number; total_abastecimento: number;
  total_manutencao_servico: number; total_pecas_almoxarifado: number;
  [key: string]: number;
};

type RelResponse<T> = { filtros: object; totais: Totais; itens: T[] };

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtBRL(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
function msgFrom(e: unknown) { return e instanceof Error ? e.message : "Falha na operação"; }

const today = new Date().toISOString().slice(0, 10);
const firstOfYear = new Date(new Date().getFullYear(), 0, 1).toISOString().slice(0, 10);

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RelatoriosPage() {
  const [tab, setTab] = useState<"veiculo" | "departamento">("veiculo");

  const TABS = [
    { key: "veiculo", label: "Custo por Veículo" },
    { key: "departamento", label: "Custo por Departamento" },
  ] as const;

  return (
    <main className="module-page">
      <div>
        <h1>Relatórios Operacionais</h1>
        <p className="muted">
          Custos consolidados de frota cruzando abastecimentos, manutenções e peças do almoxarifado.
        </p>
      </div>

      <nav className="tab-strip">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={cn("tab-btn", tab === t.key && "active")}
            onClick={() => { setTab(t.key); }}
          >
            {t.label}
          </button>
        ))}
        <Button
          className="btn-export no-print"
          style={{ marginLeft: "auto" }}
          onClick={() => window.print()}
          title="Salvar como PDF ou imprimir"
        >
          🖨️ Imprimir / PDF
        </Button>
      </nav>

      {tab === "veiculo" && <CustoPorVeiculoTab />}
      {tab === "departamento" && <CustoPorDepartamentoTab />}
    </main>
  );
}

// ── Custo por Veículo ─────────────────────────────────────────────────────────

function CustoPorVeiculoTab() {
  const { toast } = useToast();
  const [data, setData] = useState<RelResponse<VeiculoRow> | null>(null);
  const [loading, setLoading] = useState(false);
  const [fInicio, setFInicio] = useState(firstOfYear);
  const [fFim, setFim] = useState(today);
  const [fVeiculoId, setFVeiculoId] = useState("");
  const [fDeptId, setFDeptId] = useState("");

  const buildParams = () => {
    const p = new URLSearchParams();
    if (fInicio) p.set("data_inicio", fInicio);
    if (fFim) p.set("data_fim", fFim);
    if (fVeiculoId) p.set("veiculo_id", fVeiculoId);
    if (fDeptId) p.set("departamento_id", fDeptId);
    return p.toString();
  };

  const load = async () => {
    setLoading(true);
    try {
      setData(await authJson(`/relatorios/frota/custo-por-veiculo?${buildParams()}`));
    } catch (e) { toast("Erro: " + msgFrom(e), "error"); }
    setLoading(false);
  };

  const exportCsv = async () => {
    try {
      await authDownload(
        `/relatorios/frota/custo-por-veiculo?${buildParams()}&export=csv`,
        `custo_por_veiculo_${fInicio || "inicio"}_${fFim || "fim"}.csv`
      );
    } catch (e) { toast("Erro ao exportar: " + msgFrom(e), "error"); }
  };

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const rows = data?.itens || [];
  const totais = data?.totais;

  return (
    <section className="section-stack">
      <h2>Custo por Veículo</h2>
      <p className="muted text-sm">
        Composição: abastecimento + serviço de manutenção + peças/insumos do almoxarifado.
      </p>

      <div className="toolbar">
        <label className="field-group" style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
          De <input type="date" value={fInicio} onChange={(e) => setFInicio(e.target.value)} style={{ width: 140 }} />
        </label>
        <label className="field-group" style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
          Até <input type="date" value={fFim} onChange={(e) => setFim(e.target.value)} style={{ width: 140 }} />
        </label>
        <input placeholder="ID Veículo" value={fVeiculoId} style={{ width: 100 }}
          onChange={(e) => setFVeiculoId(e.target.value)} />
        <input placeholder="ID Departamento" value={fDeptId} style={{ width: 120 }}
          onChange={(e) => setFDeptId(e.target.value)} />
        <Button onClick={load} disabled={loading}>
          {loading ? "Carregando..." : "Gerar"}
        </Button>
        <Button className="btn-export" onClick={exportCsv}>
          ⬇ CSV
        </Button>
      </div>

      {totais && (
        <div className="kpi-grid">
          <div className="kpi-card">
            <span className="kpi-label">Total Geral</span>
            <span className="kpi-value">{fmtBRL(totais.total_geral)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Abastecimento</span>
            <span className="kpi-value">{fmtBRL(totais.total_abastecimento)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Manutenção (serviço)</span>
            <span className="kpi-value">{fmtBRL(totais.total_manutencao_servico)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Peças Almoxarifado</span>
            <span className="kpi-value">{fmtBRL(totais.total_pecas_almoxarifado)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Veículos no período</span>
            <span className="kpi-value">{data?.totais.total_veiculos ?? rows.length}</span>
          </div>
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>Placa</th><th>Descrição</th><th>Tipo</th><th>Dept</th>
            <th className="text-right">Abast.</th><th className="text-right">Litros</th><th className="text-right">Custo Abast.</th>
            <th className="text-right">Manut.</th><th className="text-right">Custo Serviço</th>
            <th className="text-right">Peças</th><th className="text-right">Custo Peças</th>
            <th className="text-right"><strong>Custo Total</strong></th>
          </tr>
        </thead>
        <tbody>
          {rows.length ? rows.map((r) => (
            <tr key={r.veiculo_id}>
              <td><strong>{r.placa}</strong></td>
              <td className="td-truncate">{r.descricao}</td>
              <td>{r.tipo}</td>
              <td>{r.departamento_id || "—"}</td>
              <td className="text-right">{r.n_abastecimentos}</td>
              <td className="text-right">{r.total_litros.toLocaleString("pt-BR")} L</td>
              <td className="text-right">{fmtBRL(r.custo_abastecimento)}</td>
              <td className="text-right">{r.n_manutencoes}</td>
              <td className="text-right">{fmtBRL(r.custo_manutencao_servico)}</td>
              <td className="text-right">{r.n_pecas_almoxarifado}</td>
              <td className="text-right">{fmtBRL(r.custo_pecas_almoxarifado)}</td>
              <td className="text-right"><strong>{fmtBRL(r.custo_total)}</strong></td>
            </tr>
          )) : (
            <tr><td colSpan={12} className="empty-state">Nenhum dado encontrado para o período.</td></tr>
          )}
        </tbody>
        {rows.length > 0 && totais && (
          <tfoot>
            <tr>
              <td colSpan={6}><strong>Totais</strong></td>
              <td className="text-right">{fmtBRL(totais.total_abastecimento)}</td>
              <td></td>
              <td className="text-right">{fmtBRL(totais.total_manutencao_servico)}</td>
              <td></td>
              <td className="text-right">{fmtBRL(totais.total_pecas_almoxarifado)}</td>
              <td className="text-right">{fmtBRL(totais.total_geral)}</td>
            </tr>
          </tfoot>
        )}
      </table>
    </section>
  );
}

// ── Custo por Departamento ────────────────────────────────────────────────────

function CustoPorDepartamentoTab() {
  const { toast } = useToast();
  const [data, setData] = useState<RelResponse<DeptRow> | null>(null);
  const [loading, setLoading] = useState(false);
  const [fInicio, setFInicio] = useState(firstOfYear);
  const [fFim, setFim] = useState(today);
  const [fDeptId, setFDeptId] = useState("");

  const buildParams = () => {
    const p = new URLSearchParams();
    if (fInicio) p.set("data_inicio", fInicio);
    if (fFim) p.set("data_fim", fFim);
    if (fDeptId) p.set("departamento_id", fDeptId);
    return p.toString();
  };

  const load = async () => {
    setLoading(true);
    try {
      setData(await authJson(`/relatorios/frota/custo-por-departamento?${buildParams()}`));
    } catch (e) { toast("Erro: " + msgFrom(e), "error"); }
    setLoading(false);
  };

  const exportCsv = async () => {
    try {
      await authDownload(
        `/relatorios/frota/custo-por-departamento?${buildParams()}&export=csv`,
        `custo_por_departamento_${fInicio || "inicio"}_${fFim || "fim"}.csv`
      );
    } catch (e) { toast("Erro ao exportar: " + msgFrom(e), "error"); }
  };

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const rows = data?.itens || [];
  const totais = data?.totais;

  return (
    <section className="section-stack">
      <h2>Custo por Departamento</h2>
      <p className="muted text-sm">
        Composição: abastecimento + serviço de manutenção + peças/insumos do almoxarifado
        atribuídos ao departamento.
      </p>

      <div className="toolbar">
        <label className="field-group" style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
          De <input type="date" value={fInicio} onChange={(e) => setFInicio(e.target.value)} style={{ width: 140 }} />
        </label>
        <label className="field-group" style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
          Até <input type="date" value={fFim} onChange={(e) => setFim(e.target.value)} style={{ width: 140 }} />
        </label>
        <input placeholder="ID Departamento" value={fDeptId} style={{ width: 120 }}
          onChange={(e) => setFDeptId(e.target.value)} />
        <Button onClick={load} disabled={loading}>
          {loading ? "Carregando..." : "Gerar"}
        </Button>
        <Button className="btn-export" onClick={exportCsv}>
          ⬇ CSV
        </Button>
      </div>

      {totais && (
        <div className="kpi-grid">
          <div className="kpi-card">
            <span className="kpi-label">Total Geral</span>
            <span className="kpi-value">{fmtBRL(totais.total_geral)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Abastecimento</span>
            <span className="kpi-value">{fmtBRL(totais.total_abastecimento)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Manutenção (serviço)</span>
            <span className="kpi-value">{fmtBRL(totais.total_manutencao_servico)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Peças Almoxarifado</span>
            <span className="kpi-value">{fmtBRL(totais.total_pecas_almoxarifado)}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Departamentos com custo</span>
            <span className="kpi-value">{rows.length}</span>
          </div>
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>Departamento</th>
            <th className="text-right">Abast.</th><th className="text-right">Litros</th><th className="text-right">Custo Abast.</th>
            <th className="text-right">Manut.</th><th className="text-right">Custo Serviço</th>
            <th className="text-right">Peças</th><th className="text-right">Custo Peças</th>
            <th className="text-right"><strong>Custo Total</strong></th>
          </tr>
        </thead>
        <tbody>
          {rows.length ? rows.map((r, i) => (
            <tr key={i}>
              <td>
                <strong>{r.departamento_nome}</strong>
                <br />
                <span className="muted text-xs">id={r.departamento_id ?? "—"}</span>
              </td>
              <td className="text-right">{r.n_abastecimentos}</td>
              <td className="text-right">{r.total_litros.toLocaleString("pt-BR")} L</td>
              <td className="text-right">{fmtBRL(r.custo_abastecimento)}</td>
              <td className="text-right">{r.n_manutencoes}</td>
              <td className="text-right">{fmtBRL(r.custo_manutencao_servico)}</td>
              <td className="text-right">{r.n_pecas_almoxarifado}</td>
              <td className="text-right">{fmtBRL(r.custo_pecas_almoxarifado)}</td>
              <td className="text-right"><strong>{fmtBRL(r.custo_total)}</strong></td>
            </tr>
          )) : (
            <tr><td colSpan={9} className="empty-state">Nenhum dado encontrado para o período.</td></tr>
          )}
        </tbody>
        {rows.length > 0 && totais && (
          <tfoot>
            <tr>
              <td><strong>Totais</strong></td>
              <td></td><td></td>
              <td className="text-right">{fmtBRL(totais.total_abastecimento)}</td>
              <td></td>
              <td className="text-right">{fmtBRL(totais.total_manutencao_servico)}</td>
              <td></td>
              <td className="text-right">{fmtBRL(totais.total_pecas_almoxarifado)}</td>
              <td className="text-right">{fmtBRL(totais.total_geral)}</td>
            </tr>
          </tfoot>
        )}
      </table>
    </section>
  );
}
