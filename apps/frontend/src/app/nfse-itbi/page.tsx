"use client";

import { FormEvent, useEffect, useState } from "react";
import { authJson } from "@/lib/auth";

// ── Types ──────────────────────────────────────────────────────────────────

type Paged<T> = { total: number; page: number; size: number; items: T[] };

type NFSe = {
  id: number;
  numero: string;
  prestador_id: number;
  tomador_id: number | null;
  descricao_servico: string;
  codigo_servico: string;
  competencia: string;
  data_emissao: string;
  valor_servico: number;
  valor_deducoes: number;
  aliquota_iss: number;
  valor_iss: number;
  retencao_fonte: boolean;
  status: string;
  lancamento_id: number | null;
};

type ITBI = {
  id: number;
  numero: string;
  transmitente_id: number;
  adquirente_id: number;
  imovel_id: number;
  natureza_operacao: string;
  data_operacao: string;
  valor_declarado: number;
  valor_venal_referencia: number;
  base_calculo: number;
  aliquota_itbi: number;
  valor_devido: number;
  status: string;
  lancamento_id: number | null;
};

type Contribuinte = { id: number; cpf_cnpj: string; nome: string; tipo: string };
type Imovel = { id: number; inscricao: string; logradouro: string; numero: string; valor_venal: number };

type Dashboard = {
  nfse: {
    total: number;
    emitidas: number;
    canceladas: number;
    total_valor_servicos: number;
    total_iss_emitido: number;
    total_iss_arrecadado: number;
  };
  itbi: {
    total: number;
    aberto: number;
    pago: number;
    cancelado: number;
    total_pendente: number;
    total_arrecadado: number;
  };
};

// ── Helpers ────────────────────────────────────────────────────────────────

const NATUREZA_ITBI = ["compra_venda", "doacao", "permuta", "heranca", "adjudicacao", "integralizacao_capital"];

function fmt(v: number) { return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
function pct(v: number) { return `${v.toFixed(2)}%`; }
function messageFrom(e: unknown) { return e instanceof Error ? e.message : "Falha na operação"; }

const CHIP_NFSE: Record<string, string> = { emitida: "pago", cancelada: "baixado", substituida: "pendente" };
const CHIP_ITBI: Record<string, string> = { aberto: "pendente", pago: "pago", cancelado: "baixado" };

// ── Component ─────────────────────────────────────────────────────────────────

export default function NfseItbiPage() {
  const [msg, setMsg] = useState("");
  const isError = msg.toLowerCase().includes("erro") || msg.toLowerCase().includes("falha");
  const [tab, setTab] = useState<"dashboard" | "nfse" | "itbi">("dashboard");

  // Dashboard
  const [dash, setDash] = useState<Dashboard | null>(null);

  // NFS-e list
  const [nfseList, setNfseList] = useState<Paged<NFSe> | null>(null);
  const [nfsePage, setNfsePage] = useState(1);
  const [nfseStatus, setNfseStatus] = useState("");
  const [nfseCompetencia, setNfseCompetencia] = useState("");

  // NFS-e form
  const [showNfseForm, setShowNfseForm] = useState(false);
  const [nfsePrestadorId, setNfsePrestadorId] = useState("");
  const [nfseTomadorId, setNfseTomadorId] = useState("");
  const [nfseDescricao, setNfseDescricao] = useState("");
  const [nfseCodigo, setNfseCodigo] = useState("");
  const [nfseCompetenciaForm, setNfseCompetenciaForm] = useState("");
  const [nfseDataEmissao, setNfseDataEmissao] = useState("");
  const [nfseValorServico, setNfseValorServico] = useState("");
  const [nfseValorDeducoes, setNfseValorDeducoes] = useState("0");
  const [nfseAliquota, setNfseAliquota] = useState("2.0");
  const [nfseRetencao, setNfseRetencao] = useState(false);

  // ITBI list
  const [itbiList, setItbiList] = useState<Paged<ITBI> | null>(null);
  const [itbiPage, setItbiPage] = useState(1);
  const [itbiStatus, setItbiStatus] = useState("");
  const [itbiNatureza, setItbiNatureza] = useState("");

  // ITBI form
  const [showItbiForm, setShowItbiForm] = useState(false);
  const [itbiTransmitente, setItbiTransmitente] = useState("");
  const [itbiAdquirente, setItbiAdquirente] = useState("");
  const [itbiImovelId, setItbiImovelId] = useState("");
  const [itbiNaturezaForm, setItbiNaturezaForm] = useState("compra_venda");
  const [itbiDataOperacao, setItbiDataOperacao] = useState("");
  const [itbiValorDeclarado, setItbiValorDeclarado] = useState("");
  const [itbiValorVenal, setItbiValorVenal] = useState("0");
  const [itbiAliquota, setItbiAliquota] = useState("2.0");

  // Reference data
  const [contribuintes, setContribuintes] = useState<Contribuinte[]>([]);
  const [imoveis, setImoveis] = useState<Imovel[]>([]);

  // ── Fetch ──────────────────────────────────────────────────────────────────

  async function loadDashboard() {
    try {
      const d = await authJson("/nfse-itbi/dashboard");
      setDash(d);
    } catch (e) { setMsg("Erro ao carregar dashboard: " + messageFrom(e)); }
  }

  async function loadNfse() {
    try {
      const params = new URLSearchParams({ page: String(nfsePage), size: "20" });
      if (nfseStatus) params.set("status", nfseStatus);
      if (nfseCompetencia) params.set("competencia", nfseCompetencia);
      const d = await authJson(`/nfse?${params}`);
      setNfseList(d);
    } catch (e) { setMsg("Erro ao carregar NFS-e: " + messageFrom(e)); }
  }

  async function loadItbi() {
    try {
      const params = new URLSearchParams({ page: String(itbiPage), size: "20" });
      if (itbiStatus) params.set("status", itbiStatus);
      if (itbiNatureza) params.set("natureza_operacao", itbiNatureza);
      const d = await authJson(`/itbi?${params}`);
      setItbiList(d);
    } catch (e) { setMsg("Erro ao carregar ITBI: " + messageFrom(e)); }
  }

  async function loadReferenceData() {
    try {
      const [c, i] = await Promise.all([
        authJson("/tributario/contribuintes?size=200"),
        authJson("/tributario/imoveis?size=200"),
      ]);
      setContribuintes(c.items ?? []);
      setImoveis(i.items ?? []);
    } catch {}
  }

  useEffect(() => { loadDashboard(); }, []);
  useEffect(() => { if (tab === "dashboard") loadDashboard(); }, [tab]);
  useEffect(() => { if (tab === "nfse") { loadNfse(); loadReferenceData(); } }, [tab, nfsePage, nfseStatus, nfseCompetencia]);
  useEffect(() => { if (tab === "itbi") { loadItbi(); loadReferenceData(); } }, [tab, itbiPage, itbiStatus, itbiNatureza]);

  // ── NFS-e submit ───────────────────────────────────────────────────────────

  async function submitNfse(e: FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      await authJson("/nfse/emitir", {
        method: "POST",
        body: JSON.stringify({
          prestador_id: Number(nfsePrestadorId),
          tomador_id: nfseTomadorId ? Number(nfseTomadorId) : null,
          descricao_servico: nfseDescricao,
          codigo_servico: nfseCodigo,
          competencia: nfseCompetenciaForm,
          data_emissao: nfseDataEmissao,
          valor_servico: Number(nfseValorServico),
          valor_deducoes: Number(nfseValorDeducoes),
          aliquota_iss: Number(nfseAliquota),
          retencao_fonte: nfseRetencao,
        }),
      });
      setMsg("NFS-e emitida com sucesso!");
      setShowNfseForm(false);
      loadNfse();
      loadDashboard();
    } catch (e) { setMsg("Erro: " + messageFrom(e)); }
  }

  async function cancelarNfse(id: number) {
    if (!confirm("Confirma cancelamento desta NFS-e?")) return;
    try {
      await authJson(`/nfse/${id}/cancelar?motivo=Cancelado via interface`, { method: "PATCH" });
      setMsg("NFS-e cancelada.");
      loadNfse();
      loadDashboard();
    } catch (e) { setMsg("Erro: " + messageFrom(e)); }
  }

  function exportNfse() {
    const params = new URLSearchParams({ export: "csv", size: "500" });
    if (nfseStatus) params.set("status", nfseStatus);
    if (nfseCompetencia) params.set("competencia", nfseCompetencia);
    window.location.href = `/api/proxy/nfse/relatorio?${params}`;
  }

  // ── ITBI submit ────────────────────────────────────────────────────────────

  async function submitItbi(e: FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      await authJson("/itbi/registrar", {
        method: "POST",
        body: JSON.stringify({
          transmitente_id: Number(itbiTransmitente),
          adquirente_id: Number(itbiAdquirente),
          imovel_id: Number(itbiImovelId),
          natureza_operacao: itbiNaturezaForm,
          data_operacao: itbiDataOperacao,
          valor_declarado: Number(itbiValorDeclarado),
          valor_venal_referencia: Number(itbiValorVenal),
          aliquota_itbi: Number(itbiAliquota),
        }),
      });
      setMsg("Operação ITBI registrada com sucesso!");
      setShowItbiForm(false);
      loadItbi();
      loadDashboard();
    } catch (e) { setMsg("Erro: " + messageFrom(e)); }
  }

  async function cancelarItbi(id: number) {
    if (!confirm("Confirma cancelamento desta operação ITBI?")) return;
    try {
      await authJson(`/itbi/${id}/cancelar?motivo=Cancelado via interface`, { method: "PATCH" });
      setMsg("Operação ITBI cancelada.");
      loadItbi();
      loadDashboard();
    } catch (e) { setMsg("Erro: " + messageFrom(e)); }
  }

  function exportItbi() {
    const params = new URLSearchParams({ export: "csv", size: "500" });
    if (itbiStatus) params.set("status", itbiStatus);
    if (itbiNatureza) params.set("natureza_operacao", itbiNatureza);
    window.location.href = `/api/proxy/itbi/relatorio?${params}`;
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <main className="page-content">
      <h1 className="page-title">NFS-e / ITBI</h1>

      {msg && (
        <div className={`alert ${isError ? "alert-error" : "alert-success"}`}>
          {msg}
          <button onClick={() => setMsg("")} className="alert-close">×</button>
        </div>
      )}

      <div className="tabs">
        {(["dashboard", "nfse", "itbi"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={tab === t ? "tab active" : "tab"}>
            {t === "dashboard" ? "Dashboard" : t === "nfse" ? "NFS-e" : "ITBI"}
          </button>
        ))}
      </div>

      {/* ── DASHBOARD ────────────────────────────────────────────────────── */}
      {tab === "dashboard" && dash && (
        <div>
          <h2 className="section-title">NFS-e — Notas Fiscais de Serviços</h2>
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-label">Emitidas</div>
              <div className="kpi-value">{dash.nfse.emitidas}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Canceladas</div>
              <div className="kpi-value">{dash.nfse.canceladas}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Total Serviços</div>
              <div className="kpi-value">{fmt(dash.nfse.total_valor_servicos)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">ISS Emitido</div>
              <div className="kpi-value">{fmt(dash.nfse.total_iss_emitido)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">ISS Arrecadado</div>
              <div className="kpi-value">{fmt(dash.nfse.total_iss_arrecadado)}</div>
            </div>
          </div>

          <h2 className="section-title" style={{ marginTop: "1.5rem" }}>ITBI — Transmissão Imobiliária</h2>
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-label">Total Operações</div>
              <div className="kpi-value">{dash.itbi.total}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Em Aberto</div>
              <div className="kpi-value">{dash.itbi.aberto}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Pagas</div>
              <div className="kpi-value">{dash.itbi.pago}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Pendente</div>
              <div className="kpi-value">{fmt(dash.itbi.total_pendente)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Arrecadado</div>
              <div className="kpi-value">{fmt(dash.itbi.total_arrecadado)}</div>
            </div>
          </div>

          {dash.itbi.total > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "0.35rem" }}>
                Arrecadação ITBI ({dash.itbi.pago} de {dash.itbi.total - dash.itbi.cancelado} operações)
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{
                    width: `${Math.min(100, dash.itbi.total - dash.itbi.cancelado > 0
                      ? (dash.itbi.pago / (dash.itbi.total - dash.itbi.cancelado)) * 100
                      : 0)}%`,
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── NFS-e ─────────────────────────────────────────────────────────── */}
      {tab === "nfse" && (
        <div>
          <div className="toolbar">
            <div className="filter-row">
              <select value={nfseStatus} onChange={(e) => { setNfseStatus(e.target.value); setNfsePage(1); }} className="filter-select">
                <option value="">Todos os status</option>
                <option value="emitida">Emitida</option>
                <option value="cancelada">Cancelada</option>
                <option value="substituida">Substituída</option>
              </select>
              <input
                type="month"
                value={nfseCompetencia}
                onChange={(e) => { setNfseCompetencia(e.target.value); setNfsePage(1); }}
                className="filter-input"
                placeholder="Competência"
              />
            </div>
            <div className="action-row">
              <button className="btn btn-primary" onClick={() => setShowNfseForm(!showNfseForm)}>
                + Emitir NFS-e
              </button>
              <button className="btn btn-secondary" onClick={exportNfse}>
                ↓ CSV
              </button>
            </div>
          </div>

          {showNfseForm && (
            <form onSubmit={submitNfse} className="form-card">
              <h3 className="form-title">Emitir Nova NFS-e</h3>
              <div className="form-grid">
                <div className="form-group">
                  <label>Prestador *</label>
                  <select value={nfsePrestadorId} onChange={(e) => setNfsePrestadorId(e.target.value)} required className="form-select">
                    <option value="">Selecione...</option>
                    {contribuintes.map((c) => (
                      <option key={c.id} value={c.id}>{c.nome} ({c.cpf_cnpj})</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Tomador</label>
                  <select value={nfseTomadorId} onChange={(e) => setNfseTomadorId(e.target.value)} className="form-select">
                    <option value="">Sem tomador</option>
                    {contribuintes.map((c) => (
                      <option key={c.id} value={c.id}>{c.nome} ({c.cpf_cnpj})</option>
                    ))}
                  </select>
                </div>
                <div className="form-group form-group-full">
                  <label>Descrição do Serviço *</label>
                  <input value={nfseDescricao} onChange={(e) => setNfseDescricao(e.target.value)} required className="form-input" />
                </div>
                <div className="form-group">
                  <label>Código do Serviço (LC 116)</label>
                  <input value={nfseCodigo} onChange={(e) => setNfseCodigo(e.target.value)} className="form-input" placeholder="ex: 1.07" />
                </div>
                <div className="form-group">
                  <label>Competência *</label>
                  <input type="month" value={nfseCompetenciaForm} onChange={(e) => setNfseCompetenciaForm(e.target.value)} required className="form-input" />
                </div>
                <div className="form-group">
                  <label>Data de Emissão *</label>
                  <input type="date" value={nfseDataEmissao} onChange={(e) => setNfseDataEmissao(e.target.value)} required className="form-input" />
                </div>
                <div className="form-group">
                  <label>Valor do Serviço (R$) *</label>
                  <input type="number" step="0.01" min="0.01" value={nfseValorServico} onChange={(e) => setNfseValorServico(e.target.value)} required className="form-input" />
                </div>
                <div className="form-group">
                  <label>Valor Deduções (R$)</label>
                  <input type="number" step="0.01" min="0" value={nfseValorDeducoes} onChange={(e) => setNfseValorDeducoes(e.target.value)} className="form-input" />
                </div>
                <div className="form-group">
                  <label>Alíquota ISS (%) *</label>
                  <input type="number" step="0.01" min="0.01" value={nfseAliquota} onChange={(e) => setNfseAliquota(e.target.value)} required className="form-input" />
                </div>
                <div className="form-group" style={{ display: "flex", alignItems: "center", gap: "0.5rem", paddingTop: "1.5rem" }}>
                  <input type="checkbox" id="retencao" checked={nfseRetencao} onChange={(e) => setNfseRetencao(e.target.checked)} />
                  <label htmlFor="retencao">ISS retido na fonte</label>
                </div>
              </div>
              {nfseValorServico && nfseAliquota && (
                <div className="calc-preview">
                  ISS estimado: <strong>{fmt((Number(nfseValorServico) - Number(nfseValorDeducoes)) * Number(nfseAliquota) / 100)}</strong>
                </div>
              )}
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Emitir</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowNfseForm(false)}>Cancelar</button>
              </div>
            </form>
          )}

          {nfseList && (
            <>
              <div className="table-meta">{nfseList.total} nota(s) encontrada(s)</div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Número</th>
                      <th>Data Emissão</th>
                      <th>Competência</th>
                      <th>Prestador</th>
                      <th>Valor Serviço</th>
                      <th>Alíq. ISS</th>
                      <th>Valor ISS</th>
                      <th>Retenção</th>
                      <th>Status</th>
                      <th>Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {nfseList.items.map((n) => (
                      <tr key={n.id}>
                        <td>{n.numero}</td>
                        <td>{n.data_emissao}</td>
                        <td>{n.competencia}</td>
                        <td>{n.prestador_id}</td>
                        <td>{fmt(n.valor_servico)}</td>
                        <td>{pct(n.aliquota_iss)}</td>
                        <td>{fmt(n.valor_iss)}</td>
                        <td>{n.retencao_fonte ? "Sim" : "Não"}</td>
                        <td><span className={`status-chip ${CHIP_NFSE[n.status] ?? "pendente"}`}>{n.status}</span></td>
                        <td>
                          {n.status === "emitida" && (
                            <button className="btn btn-xs btn-danger" onClick={() => cancelarNfse(n.id)}>Cancelar</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <button disabled={nfsePage <= 1} onClick={() => setNfsePage(nfsePage - 1)} className="btn btn-secondary btn-sm">‹</button>
                <span>Página {nfsePage} de {Math.max(1, Math.ceil(nfseList.total / 20))}</span>
                <button disabled={nfsePage >= Math.ceil(nfseList.total / 20)} onClick={() => setNfsePage(nfsePage + 1)} className="btn btn-secondary btn-sm">›</button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── ITBI ──────────────────────────────────────────────────────────── */}
      {tab === "itbi" && (
        <div>
          <div className="toolbar">
            <div className="filter-row">
              <select value={itbiStatus} onChange={(e) => { setItbiStatus(e.target.value); setItbiPage(1); }} className="filter-select">
                <option value="">Todos os status</option>
                <option value="aberto">Aberto</option>
                <option value="pago">Pago</option>
                <option value="cancelado">Cancelado</option>
              </select>
              <select value={itbiNatureza} onChange={(e) => { setItbiNatureza(e.target.value); setItbiPage(1); }} className="filter-select">
                <option value="">Qualquer natureza</option>
                {NATUREZA_ITBI.map((n) => <option key={n} value={n}>{n.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div className="action-row">
              <button className="btn btn-primary" onClick={() => setShowItbiForm(!showItbiForm)}>
                + Registrar ITBI
              </button>
              <button className="btn btn-secondary" onClick={exportItbi}>
                ↓ CSV
              </button>
            </div>
          </div>

          {showItbiForm && (
            <form onSubmit={submitItbi} className="form-card">
              <h3 className="form-title">Registrar Operação ITBI</h3>
              <div className="form-grid">
                <div className="form-group">
                  <label>Transmitente (vendedor) *</label>
                  <select value={itbiTransmitente} onChange={(e) => setItbiTransmitente(e.target.value)} required className="form-select">
                    <option value="">Selecione...</option>
                    {contribuintes.map((c) => (
                      <option key={c.id} value={c.id}>{c.nome} ({c.cpf_cnpj})</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Adquirente (comprador) *</label>
                  <select value={itbiAdquirente} onChange={(e) => setItbiAdquirente(e.target.value)} required className="form-select">
                    <option value="">Selecione...</option>
                    {contribuintes.map((c) => (
                      <option key={c.id} value={c.id}>{c.nome} ({c.cpf_cnpj})</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Imóvel *</label>
                  <select value={itbiImovelId} onChange={(e) => setItbiImovelId(e.target.value)} required className="form-select">
                    <option value="">Selecione...</option>
                    {imoveis.map((i) => (
                      <option key={i.id} value={i.id}>{i.inscricao} — {i.logradouro} {i.numero}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Natureza da Operação *</label>
                  <select value={itbiNaturezaForm} onChange={(e) => setItbiNaturezaForm(e.target.value)} className="form-select">
                    {NATUREZA_ITBI.map((n) => <option key={n} value={n}>{n.replace(/_/g, " ")}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Data da Operação *</label>
                  <input type="date" value={itbiDataOperacao} onChange={(e) => setItbiDataOperacao(e.target.value)} required className="form-input" />
                </div>
                <div className="form-group">
                  <label>Valor Declarado (R$) *</label>
                  <input type="number" step="0.01" min="1" value={itbiValorDeclarado} onChange={(e) => setItbiValorDeclarado(e.target.value)} required className="form-input" />
                </div>
                <div className="form-group">
                  <label>Valor Venal Referência (R$)</label>
                  <input type="number" step="0.01" min="0" value={itbiValorVenal} onChange={(e) => setItbiValorVenal(e.target.value)} className="form-input" placeholder="0 = usa venal do imóvel" />
                </div>
                <div className="form-group">
                  <label>Alíquota ITBI (%) *</label>
                  <input type="number" step="0.01" min="0.01" value={itbiAliquota} onChange={(e) => setItbiAliquota(e.target.value)} required className="form-input" />
                </div>
              </div>
              {itbiValorDeclarado && itbiAliquota && (
                <div className="calc-preview">
                  Base cálculo estimada: <strong>{fmt(Math.max(Number(itbiValorDeclarado), Number(itbiValorVenal)))}</strong>
                  {" → "}ITBI estimado: <strong>{fmt(Math.max(Number(itbiValorDeclarado), Number(itbiValorVenal)) * Number(itbiAliquota) / 100)}</strong>
                </div>
              )}
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Registrar</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowItbiForm(false)}>Cancelar</button>
              </div>
            </form>
          )}

          {itbiList && (
            <>
              <div className="table-meta">{itbiList.total} operação(ões) encontrada(s)</div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Número</th>
                      <th>Data</th>
                      <th>Natureza</th>
                      <th>Imóvel</th>
                      <th>Adquirente</th>
                      <th>Vl. Declarado</th>
                      <th>Base Cálculo</th>
                      <th>Alíq.</th>
                      <th>Valor Devido</th>
                      <th>Status</th>
                      <th>Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {itbiList.items.map((o) => (
                      <tr key={o.id}>
                        <td>{o.numero}</td>
                        <td>{o.data_operacao}</td>
                        <td>{o.natureza_operacao.replace(/_/g, " ")}</td>
                        <td>{o.imovel_id}</td>
                        <td>{o.adquirente_id}</td>
                        <td>{fmt(o.valor_declarado)}</td>
                        <td>{fmt(o.base_calculo)}</td>
                        <td>{pct(o.aliquota_itbi)}</td>
                        <td>{fmt(o.valor_devido)}</td>
                        <td><span className={`status-chip ${CHIP_ITBI[o.status] ?? "pendente"}`}>{o.status}</span></td>
                        <td>
                          {o.status === "aberto" && (
                            <button className="btn btn-xs btn-danger" onClick={() => cancelarItbi(o.id)}>Cancelar</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <button disabled={itbiPage <= 1} onClick={() => setItbiPage(itbiPage - 1)} className="btn btn-secondary btn-sm">‹</button>
                <span>Página {itbiPage} de {Math.max(1, Math.ceil(itbiList.total / 20))}</span>
                <button disabled={itbiPage >= Math.ceil(itbiList.total / 20)} onClick={() => setItbiPage(itbiPage + 1)} className="btn btn-secondary btn-sm">›</button>
              </div>
            </>
          )}
        </div>
      )}
    </main>
  );
}
