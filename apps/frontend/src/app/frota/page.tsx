"use client";

import { FormEvent, useEffect, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { authJson, readCookie } from "@/lib/auth";

// ── Types ─────────────────────────────────────────────────────────────────────

type Paged<T> = { total: number; page: number; size: number; items: T[] };

type Veiculo = {
  id: number; placa: string; descricao: string; tipo: string;
  marca: string; modelo: string; ano_fabricacao: number | null;
  combustivel: string; odometro_atual: number;
  departamento_id: number | null; status: string; observacoes: string; criado_em: string;
};

type Abastecimento = {
  id: number; veiculo_id: number; data_abastecimento: string;
  combustivel: string; litros: number; valor_litro: number; valor_total: number;
  odometro: number; posto: string; nota_fiscal: string;
  departamento_id: number | null; motorista_id: number | null;
  movimentacao_id: number | null; observacoes: string;
};

type ItemManutencao = {
  id: number; manutencao_id: number; descricao: string;
  quantidade: number; valor_unitario: number; valor_total: number;
  item_almoxarifado_id: number | null; movimentacao_id: number | null;
};

type Manutencao = {
  id: number; veiculo_id: number; tipo: string; descricao: string;
  data_abertura: string; data_conclusao: string | null;
  odometro: number; oficina: string; valor_servico: number;
  status: string; departamento_id: number | null; responsavel_id: number | null;
  observacoes: string; itens: ItemManutencao[];
};

type Dashboard = {
  total_veiculos: number; ativos: number; em_manutencao: number; inativos: number;
  abastecimentos_mes: number; litros_mes: number; custo_abastecimento_mes: number;
  manutencoes_abertas: number; custo_manutencao_mes: number;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtBRL(v: number) { return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
function msgFrom(e: unknown) { return e instanceof Error ? e.message : "Falha na operação"; }

const TIPOS = ["leve", "pesado", "onibus", "maquina", "moto"];
const COMBUSTIVEIS = ["flex", "gasolina", "diesel", "etanol", "eletrico", "gnv"];
const STATUS_VEICULO = ["ativo", "manutencao", "inativo"];
const TIPOS_MAN = ["preventiva", "corretiva", "revisao"];

const STATUS_CHIP: Record<string, string> = {
  ativo: "pago",
  manutencao: "pendente",
  inativo: "baixado",
  aberta: "pendente",
  em_andamento: "pendente",
  concluida: "pago",
  cancelada: "baixado",
};

// ── Page ──────────────────────────────────────────────────────────────────────

export default function FrotaPage() {
  const [role] = useState(() => readCookie("role"));
  const { toast } = useToast();
  const [tab, setTab] = useState<"dashboard" | "veiculos" | "abastecimentos" | "manutencoes">("dashboard");

  const canWrite = role === "admin" || role === "procurement";

  const TABS = [
    { key: "dashboard", label: "Dashboard" },
    { key: "veiculos", label: "Veículos" },
    { key: "abastecimentos", label: "Abastecimentos" },
    { key: "manutencoes", label: "Manutenções" },
  ] as const;

  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Frota</h1>
      <p className="muted">Gestão de veículos, abastecimentos e manutenções da frota municipal.</p>

      <nav style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {TABS.map((t) => (
          <button key={t.key} className={`tab-btn ${tab === t.key ? "active" : ""}`}
            onClick={() => { setTab(t.key); }}>
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "dashboard" && <DashboardTab />}
      {tab === "veiculos" && <VeiculosTab canWrite={canWrite} />}
      {tab === "abastecimentos" && <AbastecimentosTab canWrite={canWrite} />}
      {tab === "manutencoes" && <ManutencoesTab canWrite={canWrite} />}
    </main>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

function DashboardTab() {
  const [dash, setDash] = useState<Dashboard | null>(null);

  useEffect(() => {
    authJson("/frota/veiculos/dashboard").then(setDash).catch(() => {});
  }, []);

  if (!dash) return <p className="muted">Carregando...</p>;

  return (
    <section className="section-stack">
      <h2>Resumo da Frota</h2>
      <div className="kpi-grid">
        <div className="kpi-card"><span className="kpi-label">Total de Veículos</span><span className="kpi-value">{dash.total_veiculos}</span></div>
        <div className="kpi-card"><span className="kpi-label">Ativos</span><span className="kpi-value" style={{ color: "#28a745" }}>{dash.ativos}</span></div>
        <div className="kpi-card"><span className="kpi-label">Em Manutenção</span><span className="kpi-value" style={{ color: "#ffc107" }}>{dash.em_manutencao}</span></div>
        <div className="kpi-card"><span className="kpi-label">Inativos</span><span className="kpi-value" style={{ color: "#6c757d" }}>{dash.inativos}</span></div>
        <div className="kpi-card"><span className="kpi-label">Abastecimentos (mês)</span><span className="kpi-value">{dash.abastecimentos_mes}</span></div>
        <div className="kpi-card"><span className="kpi-label">Litros (mês)</span><span className="kpi-value">{dash.litros_mes.toLocaleString("pt-BR")} L</span></div>
        <div className="kpi-card"><span className="kpi-label">Custo Combustível (mês)</span><span className="kpi-value">{fmtBRL(dash.custo_abastecimento_mes)}</span></div>
        <div className="kpi-card"><span className="kpi-label">Manutenções Abertas</span><span className="kpi-value" style={{ color: dash.manutencoes_abertas > 0 ? "#dc3545" : "#28a745" }}>{dash.manutencoes_abertas}</span></div>
        <div className="kpi-card"><span className="kpi-label">Custo Manutenção (mês)</span><span className="kpi-value">{fmtBRL(dash.custo_manutencao_mes)}</span></div>
      </div>
    </section>
  );
}

// ── Veículos ──────────────────────────────────────────────────────────────────

function VeiculosTab({ canWrite }: { canWrite: boolean }) {
  const { toast } = useToast();
  const [veiculos, setVeiculos] = useState<Paged<Veiculo> | null>(null);
  const [creating, setCreating] = useState(false);
  const [page, setPage] = useState(1);
  const [fSearch, setFSearch] = useState("");
  const [fTipo, setFTipo] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [editId, setEditId] = useState<number | null>(null);
  const [editStatus, setEditStatus] = useState("");
  const [editOdo, setEditOdo] = useState("");

  // Form
  const [fPlaca, setFPlaca] = useState("");
  const [fDesc, setFDesc] = useState("");
  const [fTipoF, setFTipoF] = useState("leve");
  const [fMarca, setFMarca] = useState("");
  const [fModelo, setFModelo] = useState("");
  const [fAno, setFAno] = useState("");
  const [fComb, setFComb] = useState("flex");
  const [fOdo, setFOdo] = useState("0");
  const [fDept, setFDept] = useState("");

  const load = async () => {
    try {
      const p = new URLSearchParams({ page: String(page), size: "20" });
      if (fSearch) p.set("search", fSearch);
      if (fTipo) p.set("tipo", fTipo);
      if (fStatus) p.set("status", fStatus);
      setVeiculos(await authJson(`/frota/veiculos?${p}`));
    } catch (e) { toast("Erro: " + msgFrom(e), "error"); }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [page]);

  const handleCreate = async (ev: FormEvent) => {
    ev.preventDefault();
    try {
      await authJson("/frota/veiculos", {
        method: "POST",
        body: JSON.stringify({
          placa: fPlaca, descricao: fDesc, tipo: fTipoF,
          marca: fMarca, modelo: fModelo,
          ano_fabricacao: fAno ? +fAno : null,
          combustivel: fComb, odometro_atual: +fOdo,
          departamento_id: fDept ? +fDept : null,
        }),
      });
      toast("Veículo cadastrado com sucesso.");
      setCreating(false);
      setFPlaca(""); setFDesc(""); setFMarca(""); setFModelo(""); setFAno(""); setFOdo("0"); setFDept("");
      load();
    } catch (e) { toast("Erro: " + msgFrom(e), "error"); }
  };

  const handleUpdate = async (id: number) => {
    try {
      const body: Record<string, unknown> = {};
      if (editStatus) body["status"] = editStatus;
      if (editOdo) body["odometro_atual"] = +editOdo;
      await authJson(`/frota/veiculos/${id}`, { method: "PATCH", body: JSON.stringify(body) });
      toast("Veículo atualizado.");
      setEditId(null);
      load();
    } catch (e) { toast("Erro: " + msgFrom(e), "error"); }
  };

  return (
    <section className="section-stack">
      <h2>Veículos da Frota</h2>

      <div className="toolbar" style={{ flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
        <input placeholder="Buscar placa / descrição" value={fSearch}
          onChange={(e) => setFSearch(e.target.value)} style={{ width: 200 }} />
        <select value={fTipo} onChange={(e) => setFTipo(e.target.value)}>
          <option value="">Todos os tipos</option>
          {TIPOS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
          <option value="">Todos status</option>
          {STATUS_VEICULO.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <button className="btn" onClick={() => { setPage(1); load(); }}>Filtrar</button>
        {canWrite && <button className="btn" style={{ background: "#17a2b8", color: "white" }}
          onClick={() => setCreating(!creating)}>
          {creating ? "Cancelar" : "+ Novo Veículo"}
        </button>}
      </div>

      {creating && canWrite && (
        <div style={{ background: "#f0f8ff", border: "1px solid #bee5eb", borderRadius: 8, padding: 16, marginBottom: 12 }}>
          <h3>Novo Veículo</h3>
          <form className="form-grid" onSubmit={handleCreate}>
            <label>Placa *<input value={fPlaca} onChange={(e) => setFPlaca(e.target.value)} required /></label>
            <label>Descrição *<input value={fDesc} onChange={(e) => setFDesc(e.target.value)} required /></label>
            <label>Tipo *
              <select value={fTipoF} onChange={(e) => setFTipoF(e.target.value)}>
                {TIPOS.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <label>Combustível *
              <select value={fComb} onChange={(e) => setFComb(e.target.value)}>
                {COMBUSTIVEIS.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <label>Marca<input value={fMarca} onChange={(e) => setFMarca(e.target.value)} /></label>
            <label>Modelo<input value={fModelo} onChange={(e) => setFModelo(e.target.value)} /></label>
            <label>Ano<input type="number" value={fAno} onChange={(e) => setFAno(e.target.value)} /></label>
            <label>Odômetro Atual (km)<input type="number" step="0.1" value={fOdo} onChange={(e) => setFOdo(e.target.value)} /></label>
            <label>ID Departamento<input value={fDept} onChange={(e) => setFDept(e.target.value)} placeholder="opcional" /></label>
            <div style={{ display: "flex", gap: 8, gridColumn: "1/-1" }}>
              <button className="btn" type="submit" style={{ background: "#17a2b8", color: "white" }}>Cadastrar</button>
              <button className="btn" type="button" onClick={() => setCreating(false)}>Cancelar</button>
            </div>
          </form>
        </div>
      )}

      <table>
        <thead>
          <tr><th>Placa</th><th>Descrição</th><th>Tipo</th><th>Combustível</th><th>Odômetro (km)</th><th>Dept</th><th>Status</th><th>Ações</th></tr>
        </thead>
        <tbody>
          {veiculos?.items.length ? veiculos.items.map((v) => (
            <tr key={v.id}>
              <td><strong>{v.placa}</strong></td>
              <td>{v.descricao}</td>
              <td>{v.tipo}</td>
              <td>{v.combustivel}</td>
              <td>{v.odometro_atual.toLocaleString("pt-BR")} km</td>
              <td>{v.departamento_id || "—"}</td>
              <td><span className={`chip ${STATUS_CHIP[v.status] || "pendente"}`}>{v.status}</span></td>
              <td>
                {canWrite && editId === v.id ? (
                  <span style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                    <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)} style={{ width: 110 }}>
                      <option value="">status</option>
                      {STATUS_VEICULO.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <input placeholder="km" value={editOdo} style={{ width: 80 }}
                      onChange={(e) => setEditOdo(e.target.value)} type="number" />
                    <button className="btn" style={{ background: "#28a745", color: "white", fontSize: 12 }}
                      onClick={() => handleUpdate(v.id)}>OK</button>
                    <button className="btn" style={{ fontSize: 12 }}
                      onClick={() => setEditId(null)}>×</button>
                  </span>
                ) : (
                  canWrite && <button className="btn" style={{ fontSize: 12 }}
                    onClick={() => { setEditId(v.id); setEditStatus(v.status); setEditOdo(String(v.odometro_atual)); }}>
                    ✏️ Editar
                  </button>
                )}
              </td>
            </tr>
          )) : <tr><td colSpan={8} className="empty-state">Nenhum veículo encontrado.</td></tr>}
        </tbody>
      </table>
      <div className="pagination">
        <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
        <span>Pág {page} · Total: {veiculos?.total || 0}</span>
        <button className="btn" disabled={(veiculos?.items?.length || 0) < 20} onClick={() => setPage((p) => p + 1)}>Próxima</button>
      </div>
    </section>
  );
}

// ── Abastecimentos ────────────────────────────────────────────────────────────

function AbastecimentosTab({ canWrite }: { canWrite: boolean }) {
  const { toast } = useToast();
  const [abast, setAbast] = useState<Paged<Abastecimento> | null>(null);
  const [creating, setCreating] = useState(false);
  const [page, setPage] = useState(1);
  const [fVeiculoId, setFVeiculoId] = useState("");

  const [fVId, setFVId] = useState("");
  const [fData, setFData] = useState(new Date().toISOString().slice(0, 10));
  const [fComb, setFComb] = useState("diesel");
  const [fLitros, setFLitros] = useState("");
  const [fVlLitro, setFVlLitro] = useState("");
  const [fOdo, setFOdo] = useState("");
  const [fPosto, setFPosto] = useState("");
  const [fNF, setFNF] = useState("");
  const [fDept, setFDept] = useState("");

  const load = async () => {
    try {
      const p = new URLSearchParams({ page: String(page), size: "20" });
      if (fVeiculoId) p.set("veiculo_id", fVeiculoId);
      setAbast(await authJson(`/frota/abastecimentos?${p}`));
    } catch (e) { toast("Erro: " + msgFrom(e), "error"); }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [page]);

  const handleCreate = async (ev: FormEvent) => {
    ev.preventDefault();
    try {
      await authJson("/frota/abastecimentos", {
        method: "POST",
        body: JSON.stringify({
          veiculo_id: +fVId,
          data_abastecimento: fData,
          combustivel: fComb,
          litros: +fLitros,
          valor_litro: +fVlLitro,
          odometro: fOdo ? +fOdo : 0,
          posto: fPosto,
          nota_fiscal: fNF,
          departamento_id: fDept ? +fDept : null,
        }),
      });
      toast("Abastecimento registrado.");
      setCreating(false);
      setFVId(""); setFLitros(""); setFVlLitro(""); setFOdo(""); setFPosto(""); setFNF(""); setFDept("");
      load();
    } catch (e) { toast("Erro: " + msgFrom(e), "error"); }
  };

  return (
    <section className="section-stack">
      <h2>Abastecimentos</h2>

      <div className="toolbar" style={{ gap: 8, marginBottom: 8 }}>
        <input placeholder="ID Veículo" value={fVeiculoId} style={{ width: 100 }}
          onChange={(e) => setFVeiculoId(e.target.value)} />
        <button className="btn" onClick={() => { setPage(1); load(); }}>Filtrar</button>
        {canWrite && <button className="btn" style={{ background: "#17a2b8", color: "white" }}
          onClick={() => setCreating(!creating)}>
          {creating ? "Cancelar" : "+ Registrar Abastecimento"}
        </button>}
      </div>

      {creating && canWrite && (
        <div style={{ background: "#f0f8ff", border: "1px solid #bee5eb", borderRadius: 8, padding: 16, marginBottom: 12 }}>
          <h3>Novo Abastecimento</h3>
          <form className="form-grid" onSubmit={handleCreate}>
            <label>ID Veículo *<input value={fVId} onChange={(e) => setFVId(e.target.value)} required /></label>
            <label>Data *<input type="date" value={fData} onChange={(e) => setFData(e.target.value)} required /></label>
            <label>Combustível *
              <select value={fComb} onChange={(e) => setFComb(e.target.value)}>
                {COMBUSTIVEIS.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <label>Litros *<input type="number" step="0.01" min="0.01" value={fLitros} onChange={(e) => setFLitros(e.target.value)} required /></label>
            <label>Valor/Litro (R$)<input type="number" step="0.001" value={fVlLitro} onChange={(e) => setFVlLitro(e.target.value)} /></label>
            <label>Odômetro (km)<input type="number" step="0.1" value={fOdo} onChange={(e) => setFOdo(e.target.value)} /></label>
            <label>Posto<input value={fPosto} onChange={(e) => setFPosto(e.target.value)} /></label>
            <label>Nota Fiscal<input value={fNF} onChange={(e) => setFNF(e.target.value)} /></label>
            <label>ID Departamento<input value={fDept} onChange={(e) => setFDept(e.target.value)} /></label>
            <div style={{ display: "flex", gap: 8, gridColumn: "1/-1" }}>
              <button className="btn" type="submit" style={{ background: "#17a2b8", color: "white" }}>Registrar</button>
              <button className="btn" type="button" onClick={() => setCreating(false)}>Cancelar</button>
            </div>
          </form>
        </div>
      )}

      <table>
        <thead>
          <tr><th>ID</th><th>Veículo</th><th>Data</th><th>Combustível</th><th>Litros</th><th>Valor/L</th><th>Total</th><th>Odômetro</th><th>Posto</th></tr>
        </thead>
        <tbody>
          {abast?.items.length ? abast.items.map((a) => (
            <tr key={a.id}>
              <td>{a.id}</td>
              <td>{a.veiculo_id}</td>
              <td>{a.data_abastecimento}</td>
              <td>{a.combustivel}</td>
              <td>{a.litros} L</td>
              <td>{fmtBRL(a.valor_litro)}</td>
              <td><strong>{fmtBRL(a.valor_total)}</strong></td>
              <td>{a.odometro > 0 ? `${a.odometro.toLocaleString("pt-BR")} km` : "—"}</td>
              <td>{a.posto || "—"}</td>
            </tr>
          )) : <tr><td colSpan={9} className="empty-state">Nenhum abastecimento encontrado.</td></tr>}
        </tbody>
      </table>
      <div className="pagination">
        <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
        <span>Pág {page} · Total: {abast?.total || 0}</span>
        <button className="btn" disabled={(abast?.items?.length || 0) < 20} onClick={() => setPage((p) => p + 1)}>Próxima</button>
      </div>
    </section>
  );
}

// ── Manutenções ───────────────────────────────────────────────────────────────

function ManutencoesTab({ canWrite }: { canWrite: boolean }) {
  const { toast } = useToast();
  const [mans, setMans] = useState<Paged<Manutencao> | null>(null);
  const [creating, setCreating] = useState(false);
  const [page, setPage] = useState(1);
  const [fStatus, setFStatus] = useState("");
  const [fVId, setFVId] = useState("");
  const [expandId, setExpandId] = useState<number | null>(null);
  const [concludeId, setConcludeId] = useState<number | null>(null);
  const [fConclData, setFConclData] = useState(new Date().toISOString().slice(0, 10));
  const [fConclValor, setFConclValor] = useState("");

  const [mVId, setMVId] = useState("");
  const [mTipo, setMTipo] = useState("preventiva");
  const [mDesc, setMDesc] = useState("");
  const [mData, setMData] = useState(new Date().toISOString().slice(0, 10));
  const [mOdo, setMOdo] = useState("");
  const [mOficina, setMOficina] = useState("");
  const [mDept, setMDept] = useState("");

  const load = async () => {
    try {
      const p = new URLSearchParams({ page: String(page), size: "20" });
      if (fStatus) p.set("status", fStatus);
      if (fVId) p.set("veiculo_id", fVId);
      setMans(await authJson(`/frota/manutencoes?${p}`));
    } catch (e) { toast("Erro: " + msgFrom(e), "error"); }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [page]);

  const handleCreate = async (ev: FormEvent) => {
    ev.preventDefault();
    try {
      await authJson("/frota/manutencoes", {
        method: "POST",
        body: JSON.stringify({
          veiculo_id: +mVId, tipo: mTipo, descricao: mDesc,
          data_abertura: mData, odometro: mOdo ? +mOdo : 0,
          oficina: mOficina, departamento_id: mDept ? +mDept : null,
          itens: [],
        }),
      });
      toast("Manutenção aberta com sucesso.");
      setCreating(false);
      setMVId(""); setMDesc(""); setMOdo(""); setMOficina(""); setMDept("");
      load();
    } catch (e) { toast("Erro: " + msgFrom(e), "error"); }
  };

  const handleConcluir = async (id: number) => {
    try {
      await authJson(`/frota/manutencoes/${id}/concluir`, {
        method: "POST",
        body: JSON.stringify({
          data_conclusao: fConclData,
          valor_servico: fConclValor ? +fConclValor : 0,
        }),
      });
      toast(`Manutenção #${id} concluída.`);
      setConcludeId(null); setFConclValor("");
      load();
    } catch (e) { toast("Erro: " + msgFrom(e), "error"); }
  };

  const handleCancelar = async (id: number) => {
    if (!confirm(`Cancelar manutenção #${id}?`)) return;
    try {
      await authJson(`/frota/manutencoes/${id}/cancelar`, { method: "POST" });
      toast(`Manutenção #${id} cancelada.`);
      load();
    } catch (e) { toast("Erro: " + msgFrom(e), "error"); }
  };

  return (
    <section className="section-stack">
      <h2>Manutenções</h2>

      <div className="toolbar" style={{ gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        <input placeholder="ID Veículo" value={fVId} style={{ width: 100 }}
          onChange={(e) => setFVId(e.target.value)} />
        <select value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
          <option value="">Todos status</option>
          {["aberta", "em_andamento", "concluida", "cancelada"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <button className="btn" onClick={() => { setPage(1); load(); }}>Filtrar</button>
        {canWrite && <button className="btn" style={{ background: "#17a2b8", color: "white" }}
          onClick={() => setCreating(!creating)}>
          {creating ? "Cancelar" : "+ Abrir Manutenção"}
        </button>}
      </div>

      {creating && canWrite && (
        <div style={{ background: "#f0f8ff", border: "1px solid #bee5eb", borderRadius: 8, padding: 16, marginBottom: 12 }}>
          <h3>Nova Ordem de Manutenção</h3>
          <form className="form-grid" onSubmit={handleCreate}>
            <label>ID Veículo *<input value={mVId} onChange={(e) => setMVId(e.target.value)} required /></label>
            <label>Tipo *
              <select value={mTipo} onChange={(e) => setMTipo(e.target.value)}>
                {TIPOS_MAN.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <label style={{ gridColumn: "1/-1" }}>Descrição *<input value={mDesc} onChange={(e) => setMDesc(e.target.value)} required /></label>
            <label>Data Abertura *<input type="date" value={mData} onChange={(e) => setMData(e.target.value)} required /></label>
            <label>Odômetro (km)<input type="number" step="0.1" value={mOdo} onChange={(e) => setMOdo(e.target.value)} /></label>
            <label>Oficina<input value={mOficina} onChange={(e) => setMOficina(e.target.value)} /></label>
            <label>ID Departamento<input value={mDept} onChange={(e) => setMDept(e.target.value)} /></label>
            <div style={{ display: "flex", gap: 8, gridColumn: "1/-1" }}>
              <button className="btn" type="submit" style={{ background: "#17a2b8", color: "white" }}>Abrir</button>
              <button className="btn" type="button" onClick={() => setCreating(false)}>Cancelar</button>
            </div>
          </form>
        </div>
      )}

      <table>
        <thead>
          <tr><th>ID</th><th>Veículo</th><th>Tipo</th><th>Descrição</th><th>Abertura</th><th>Conclusão</th><th>Valor</th><th>Status</th><th>Ações</th></tr>
        </thead>
        <tbody>
          {mans?.items.length ? mans.items.map((m) => (
            <>
              <tr key={m.id}>
                <td>{m.id}</td>
                <td>{m.veiculo_id}</td>
                <td>{m.tipo}</td>
                <td>{m.descricao}</td>
                <td>{m.data_abertura}</td>
                <td>{m.data_conclusao || "—"}</td>
                <td>{m.valor_servico > 0 ? fmtBRL(m.valor_servico) : "—"}</td>
                <td><span className={`chip ${STATUS_CHIP[m.status] || "pendente"}`}>{m.status}</span></td>
                <td style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  <button className="btn" style={{ fontSize: 12 }}
                    onClick={() => setExpandId(expandId === m.id ? null : m.id)}>
                    {expandId === m.id ? "▲ Itens" : "▼ Itens"} ({m.itens.length})
                  </button>
                  {canWrite && m.status !== "concluida" && m.status !== "cancelada" && (
                    concludeId === m.id ? (
                      <span style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        <input type="date" value={fConclData} style={{ width: 130 }} onChange={(e) => setFConclData(e.target.value)} />
                        <input type="number" placeholder="Valor R$" value={fConclValor} style={{ width: 90 }} onChange={(e) => setFConclValor(e.target.value)} />
                        <button className="btn" style={{ background: "#28a745", color: "white", fontSize: 12 }}
                          onClick={() => handleConcluir(m.id)}>✓ OK</button>
                        <button className="btn" style={{ fontSize: 12 }} onClick={() => setConcludeId(null)}>×</button>
                      </span>
                    ) : (
                      <>
                        <button className="btn" style={{ background: "#28a745", color: "white", fontSize: 12 }}
                          onClick={() => setConcludeId(m.id)}>✓ Concluir</button>
                        <button className="btn" style={{ background: "#dc3545", color: "white", fontSize: 12 }}
                          onClick={() => handleCancelar(m.id)}>✗ Cancelar</button>
                      </>
                    )
                  )}
                </td>
              </tr>
              {expandId === m.id && m.itens.length > 0 && (
                <tr key={`itens-${m.id}`}>
                  <td colSpan={9} style={{ padding: "4px 24px", background: "#f8f9fa" }}>
                    <table style={{ width: "100%", fontSize: 13 }}>
                      <thead><tr><th>Item</th><th>Qtd</th><th>Valor Unit.</th><th>Total</th><th>Almox.</th><th>Mov.</th></tr></thead>
                      <tbody>
                        {m.itens.map((it) => (
                          <tr key={it.id}>
                            <td>{it.descricao}</td>
                            <td>{it.quantidade}</td>
                            <td>{fmtBRL(it.valor_unitario)}</td>
                            <td>{fmtBRL(it.valor_total)}</td>
                            <td>{it.item_almoxarifado_id || "—"}</td>
                            <td>{it.movimentacao_id || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </td>
                </tr>
              )}
            </>
          )) : <tr><td colSpan={9} className="empty-state">Nenhuma manutenção encontrada.</td></tr>}
        </tbody>
      </table>
      <div className="pagination">
        <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
        <span>Pág {page} · Total: {mans?.total || 0}</span>
        <button className="btn" disabled={(mans?.items?.length || 0) < 20} onClick={() => setPage((p) => p + 1)}>Próxima</button>
      </div>
    </section>
  );
}
