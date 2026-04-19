"use client";

import { useEffect, useState } from "react";
import { authJson, authDownload } from "@/lib/auth";

// ── Types ─────────────────────────────────────────────────────────────────────

type ContaBancaria = {
  id: number;
  banco: string;
  agencia: string;
  numero_conta: string;
  descricao: string;
  tipo: string;
  ativa: boolean;
  saldo_inicial: number;
  data_saldo_inicial: string;
};

type Lancamento = {
  id: number;
  conta_id: number;
  data_lancamento: string;
  tipo: "credito" | "debito";
  valor: number;
  descricao: string;
  documento_ref: string;
  status: "pendente" | "conciliado" | "divergente" | "ignorado";
  payment_id: number | null;
  revenue_entry_id: number | null;
  divergencia_obs: string | null;
  conciliado_em: string | null;
};

type Dashboard = {
  total_lancamentos: number;
  conciliados: number;
  divergentes: number;
  pendentes: number;
  ignorados: number;
  pct_conciliado: number;
  total_creditos: number;
  total_debitos: number;
  saldo_inicial_contas: number;
  saldo_projetado: number;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtBRL(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
function msgFrom(e: unknown) { return e instanceof Error ? e.message : "Falha na operação"; }

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    conciliado: "#28a745",
    divergente: "#fd7e14",
    pendente: "#6c757d",
    ignorado: "#adb5bd",
  };
  return (
    <span style={{
      background: map[status] || "#aaa", color: "white",
      borderRadius: 4, padding: "2px 7px", fontSize: 12, fontWeight: 600,
    }}>
      {status}
    </span>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ConciliacaoPage() {
  const [tab, setTab] = useState<"dashboard" | "lancamentos" | "contas">("dashboard");
  const [msg, setMsg] = useState("");
  const isError = msg.toLowerCase().includes("erro") || msg.toLowerCase().includes("falha");

  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Conciliação Bancária</h1>
      <p className="muted">
        Cruzamento entre extratos bancários e os pagamentos/receitas registrados no ERP.
      </p>

      {msg && (
        <div className={`alert ${isError ? "error" : "success"}`} style={{ marginBottom: 8 }}>
          {msg}
        </div>
      )}

      <nav style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {(["dashboard", "lancamentos", "contas"] as const).map((t) => (
          <button key={t} className={`tab-btn ${tab === t ? "active" : ""}`}
            onClick={() => { setTab(t); setMsg(""); }}>
            {t === "dashboard" ? "Dashboard" : t === "lancamentos" ? "Lançamentos / Extrato" : "Contas Bancárias"}
          </button>
        ))}
      </nav>

      {tab === "dashboard" && <DashboardTab setMsg={setMsg} />}
      {tab === "lancamentos" && <LancamentosTab setMsg={setMsg} />}
      {tab === "contas" && <ContasTab setMsg={setMsg} />}
    </main>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

function DashboardTab({ setMsg }: { setMsg: (m: string) => void }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [contaId, setContaId] = useState("");
  const [loading, setLoading] = useState(false);
  const [autoLoading, setAutoLoading] = useState(false);
  const [autoResult, setAutoResult] = useState<Record<string, unknown> | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const qs = contaId ? `?conta_id=${contaId}` : "";
      setData(await authJson(`/banco/dashboard${qs}`));
      setMsg("");
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
    setLoading(false);
  };

  const runAuto = async () => {
    setAutoLoading(true);
    try {
      const qs = contaId ? `?conta_id=${contaId}` : "";
      const res = await authJson(`/banco/conciliacao/auto${qs}`, { method: "POST" });
      setAutoResult(res);
      setMsg("✅ Conciliação automática concluída.");
      load();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
    setAutoLoading(false);
  };

  useEffect(() => { load(); }, []);

  const pct = data?.pct_conciliado ?? 0;
  const barColor = pct >= 80 ? "#28a745" : pct >= 50 ? "#fd7e14" : "#dc3545";

  return (
    <section className="section-stack">
      <h2>Resumo de Conciliação</h2>

      <div className="toolbar" style={{ gap: 8, marginBottom: 12 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
          Conta (ID)
          <input type="number" value={contaId} style={{ width: 80 }}
            placeholder="Todos"
            onChange={(e) => setContaId(e.target.value)} />
        </label>
        <button className="btn" onClick={load} disabled={loading}>
          {loading ? "Carregando..." : "Atualizar"}
        </button>
        <button
          className="btn"
          style={{ background: "#0d6efd", color: "white" }}
          onClick={runAuto}
          disabled={autoLoading}
        >
          {autoLoading ? "Conciliando..." : "⚡ Conciliar Automaticamente"}
        </button>
      </div>

      {autoResult && (
        <div className="alert success" style={{ marginBottom: 12 }}>
          Resultado: {autoResult.conciliados as number} conciliados | {autoResult.divergentes as number} divergentes | {autoResult.pendentes as number} pendentes
          &nbsp;(tolerância {autoResult.tolerancia_dias as number} dias)
        </div>
      )}

      {data && (
        <>
          <div className="kpi-grid" style={{ marginBottom: 12 }}>
            <div className="kpi-card">
              <span className="kpi-label">Total de Lançamentos</span>
              <span className="kpi-value">{data.total_lancamentos}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Conciliados</span>
              <span className="kpi-value" style={{ color: "#28a745" }}>{data.conciliados}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Divergentes</span>
              <span className="kpi-value" style={{ color: "#fd7e14" }}>{data.divergentes}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Pendentes</span>
              <span className="kpi-value" style={{ color: "#6c757d" }}>{data.pendentes}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Total Créditos</span>
              <span className="kpi-value" style={{ color: "#28a745" }}>{fmtBRL(data.total_creditos)}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Total Débitos</span>
              <span className="kpi-value" style={{ color: "#dc3545" }}>{fmtBRL(data.total_debitos)}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Saldo Inicial (contas)</span>
              <span className="kpi-value">{fmtBRL(data.saldo_inicial_contas)}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Saldo Projetado</span>
              <span className="kpi-value" style={{ color: data.saldo_projetado >= 0 ? "#28a745" : "#dc3545" }}>
                {fmtBRL(data.saldo_projetado)}
              </span>
            </div>
          </div>

          <div style={{ marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
              <span>Progresso de Conciliação</span>
              <strong style={{ color: barColor }}>{pct}%</strong>
            </div>
            <div style={{ height: 10, background: "#e9ecef", borderRadius: 5, overflow: "hidden" }}>
              <div style={{ width: `${Math.min(100, pct)}%`, height: "100%", background: barColor, borderRadius: 5 }} />
            </div>
          </div>
        </>
      )}
    </section>
  );
}

// ── Lançamentos ───────────────────────────────────────────────────────────────

function LancamentosTab({ setMsg }: { setMsg: (m: string) => void }) {
  const [items, setItems] = useState<Lancamento[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterTipo, setFilterTipo] = useState("");
  const [filterConta, setFilterConta] = useState("");
  const [loading, setLoading] = useState(false);

  // New lancamento form
  const [form, setForm] = useState({
    conta_id: "", data_lancamento: "", tipo: "debito", valor: "", descricao: "", documento_ref: "",
  });
  const [showForm, setShowForm] = useState(false);

  const SIZE = 20;

  const load = async (p = page) => {
    setLoading(true);
    try {
      let url = `/banco/lancamentos?page=${p}&size=${SIZE}`;
      if (filterStatus) url += `&status=${filterStatus}`;
      if (filterTipo) url += `&tipo=${filterTipo}`;
      if (filterConta) url += `&conta_id=${filterConta}`;
      const d = await authJson(url);
      setItems(d.items);
      setTotal(d.total);
      setMsg("");
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
    setLoading(false);
  };

  const exportCsv = async () => {
    try {
      let url = `/banco/conciliacao/relatorio?export=csv`;
      if (filterStatus) url += `&status=${filterStatus}`;
      if (filterConta) url += `&conta_id=${filterConta}`;
      await authDownload(url, "conciliacao.csv");
    } catch (e) { setMsg("Erro ao exportar: " + msgFrom(e)); }
  };

  const handleCriar = async () => {
    try {
      const qs = new URLSearchParams({
        conta_id: form.conta_id,
        data_lancamento: form.data_lancamento,
        tipo: form.tipo,
        valor: form.valor,
        descricao: form.descricao,
        documento_ref: form.documento_ref,
      }).toString();
      await authJson(`/banco/lancamentos?${qs}`, { method: "POST" });
      setMsg("✅ Lançamento criado.");
      setShowForm(false);
      setForm({ conta_id: "", data_lancamento: "", tipo: "debito", valor: "", descricao: "", documento_ref: "" });
      load(1);
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const handleIgnorar = async (id: number) => {
    try {
      await authJson(`/banco/lancamentos/${id}/ignorar?obs=Ignorado pelo usuário`, { method: "PATCH" });
      setMsg("✅ Lançamento ignorado.");
      load();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  useEffect(() => { load(1); }, [filterStatus, filterTipo, filterConta]);

  const totalPages = Math.ceil(total / SIZE);

  return (
    <section className="section-stack">
      <h2>Extrato / Lançamentos Bancários</h2>

      <div className="toolbar" style={{ gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} style={{ fontSize: 13 }}>
          <option value="">Todos os status</option>
          <option value="pendente">Pendente</option>
          <option value="conciliado">Conciliado</option>
          <option value="divergente">Divergente</option>
          <option value="ignorado">Ignorado</option>
        </select>
        <select value={filterTipo} onChange={(e) => setFilterTipo(e.target.value)} style={{ fontSize: 13 }}>
          <option value="">Crédito e Débito</option>
          <option value="credito">Crédito</option>
          <option value="debito">Débito</option>
        </select>
        <input type="number" value={filterConta} placeholder="Conta ID" style={{ width: 90, fontSize: 13 }}
          onChange={(e) => setFilterConta(e.target.value)} />
        <button className="btn" onClick={() => load(page)} disabled={loading}>
          {loading ? "..." : "Filtrar"}
        </button>
        <button className="btn" style={{ background: "#28a745", color: "white" }} onClick={exportCsv}>⬇ CSV</button>
        <button className="btn" style={{ background: "#0d6efd", color: "white" }}
          onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancelar" : "+ Lançamento"}
        </button>
      </div>

      {showForm && (
        <div style={{ border: "1px solid #dee2e6", borderRadius: 6, padding: 12, marginBottom: 12, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <label style={{ fontSize: 13 }}>
            Conta ID *
            <input type="number" value={form.conta_id} onChange={(e) => setForm({ ...form, conta_id: e.target.value })} />
          </label>
          <label style={{ fontSize: 13 }}>
            Data *
            <input type="date" value={form.data_lancamento} onChange={(e) => setForm({ ...form, data_lancamento: e.target.value })} />
          </label>
          <label style={{ fontSize: 13 }}>
            Tipo *
            <select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              <option value="debito">Débito</option>
              <option value="credito">Crédito</option>
            </select>
          </label>
          <label style={{ fontSize: 13 }}>
            Valor (R$) *
            <input type="number" step="0.01" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} />
          </label>
          <label style={{ fontSize: 13 }}>
            Descrição
            <input type="text" value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
          </label>
          <label style={{ fontSize: 13 }}>
            Doc. Referência
            <input type="text" value={form.documento_ref} onChange={(e) => setForm({ ...form, documento_ref: e.target.value })} />
          </label>
          <div style={{ gridColumn: "1 / -1", textAlign: "right" }}>
            <button className="btn" style={{ background: "#28a745", color: "white" }} onClick={handleCriar}>
              Salvar Lançamento
            </button>
          </div>
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>Data</th>
            <th>Tipo</th>
            <th style={{ textAlign: "right" }}>Valor</th>
            <th>Descrição</th>
            <th>Doc. Ref.</th>
            <th>Status</th>
            <th>Vínculo ERP</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {items.length ? items.map((l) => (
            <tr key={l.id}>
              <td style={{ whiteSpace: "nowrap" }}>{l.data_lancamento}</td>
              <td>
                <span style={{ color: l.tipo === "credito" ? "#28a745" : "#dc3545", fontWeight: 600 }}>
                  {l.tipo === "credito" ? "C" : "D"}
                </span>
              </td>
              <td style={{ textAlign: "right" }}>{fmtBRL(l.valor)}</td>
              <td style={{ fontSize: 12, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {l.descricao}
              </td>
              <td style={{ fontSize: 12 }}>{l.documento_ref || "—"}</td>
              <td><StatusBadge status={l.status} /></td>
              <td style={{ fontSize: 12 }}>
                {l.payment_id ? `Pag. #${l.payment_id}` : l.revenue_entry_id ? `Rec. #${l.revenue_entry_id}` : "—"}
                {l.divergencia_obs && (
                  <div style={{ color: "#fd7e14", fontSize: 11 }} title={l.divergencia_obs}>⚠ divergência</div>
                )}
              </td>
              <td>
                {l.status === "pendente" && (
                  <button
                    className="btn"
                    style={{ padding: "2px 8px", fontSize: 12, background: "#6c757d", color: "white" }}
                    onClick={() => handleIgnorar(l.id)}
                  >
                    Ignorar
                  </button>
                )}
              </td>
            </tr>
          )) : (
            <tr><td colSpan={8} className="empty-state">Nenhum lançamento encontrado.</td></tr>
          )}
        </tbody>
      </table>

      {totalPages > 1 && (
        <div style={{ display: "flex", gap: 4, marginTop: 8 }}>
          <button className="btn" disabled={page <= 1} onClick={() => { setPage(page - 1); load(page - 1); }}>‹</button>
          <span style={{ alignSelf: "center", fontSize: 13 }}>Pág {page}/{totalPages}</span>
          <button className="btn" disabled={page >= totalPages} onClick={() => { setPage(page + 1); load(page + 1); }}>›</button>
        </div>
      )}
    </section>
  );
}

// ── Contas ────────────────────────────────────────────────────────────────────

function ContasTab({ setMsg }: { setMsg: (m: string) => void }) {
  const [contas, setContas] = useState<ContaBancaria[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    banco: "", agencia: "", numero_conta: "", descricao: "", tipo: "corrente",
    saldo_inicial: "0", data_saldo_inicial: "",
  });

  const load = async () => {
    setLoading(true);
    try {
      const d = await authJson("/banco/contas?size=50");
      setContas(d.items);
      setMsg("");
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
    setLoading(false);
  };

  const handleCriar = async () => {
    try {
      const qs = new URLSearchParams({
        banco: form.banco,
        agencia: form.agencia,
        numero_conta: form.numero_conta,
        descricao: form.descricao,
        tipo: form.tipo,
        saldo_inicial: form.saldo_inicial,
        data_saldo_inicial: form.data_saldo_inicial,
      }).toString();
      await authJson(`/banco/contas?${qs}`, { method: "POST" });
      setMsg("✅ Conta criada.");
      setShowForm(false);
      load();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const toggleAtiva = async (c: ContaBancaria) => {
    try {
      await authJson(`/banco/contas/${c.id}?ativa=${!c.ativa}`, { method: "PATCH" });
      load();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  useEffect(() => { load(); }, []);

  return (
    <section className="section-stack">
      <h2>Contas Bancárias</h2>

      <div className="toolbar" style={{ marginBottom: 8 }}>
        <button className="btn" style={{ background: "#0d6efd", color: "white" }} onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancelar" : "+ Nova Conta"}
        </button>
      </div>

      {showForm && (
        <div style={{ border: "1px solid #dee2e6", borderRadius: 6, padding: 12, marginBottom: 12, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          {(["banco", "agencia", "numero_conta", "descricao"] as const).map((f) => (
            <label key={f} style={{ fontSize: 13 }}>
              {f.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              <input value={form[f]} onChange={(e) => setForm({ ...form, [f]: e.target.value })} />
            </label>
          ))}
          <label style={{ fontSize: 13 }}>
            Tipo
            <select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              <option value="corrente">Corrente</option>
              <option value="poupanca">Poupança</option>
              <option value="aplicacao">Aplicação</option>
            </select>
          </label>
          <label style={{ fontSize: 13 }}>
            Saldo Inicial (R$)
            <input type="number" step="0.01" value={form.saldo_inicial}
              onChange={(e) => setForm({ ...form, saldo_inicial: e.target.value })} />
          </label>
          <label style={{ fontSize: 13 }}>
            Data do Saldo Inicial
            <input type="date" value={form.data_saldo_inicial}
              onChange={(e) => setForm({ ...form, data_saldo_inicial: e.target.value })} />
          </label>
          <div style={{ gridColumn: "1 / -1", textAlign: "right" }}>
            <button className="btn" style={{ background: "#28a745", color: "white" }} onClick={handleCriar}>
              Salvar Conta
            </button>
          </div>
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>Banco</th>
            <th>Agência</th>
            <th>Conta</th>
            <th>Descrição</th>
            <th>Tipo</th>
            <th style={{ textAlign: "right" }}>Saldo Inicial</th>
            <th>Situação</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {loading && <tr><td colSpan={8} className="empty-state">Carregando...</td></tr>}
          {!loading && !contas.length && <tr><td colSpan={8} className="empty-state">Nenhuma conta cadastrada.</td></tr>}
          {contas.map((c) => (
            <tr key={c.id}>
              <td>{c.banco}</td>
              <td>{c.agencia}</td>
              <td>{c.numero_conta}</td>
              <td style={{ fontSize: 12 }}>{c.descricao || "—"}</td>
              <td>{c.tipo}</td>
              <td style={{ textAlign: "right" }}>{fmtBRL(c.saldo_inicial)}</td>
              <td>
                <span style={{ color: c.ativa ? "#28a745" : "#dc3545", fontWeight: 600 }}>
                  {c.ativa ? "Ativa" : "Inativa"}
                </span>
              </td>
              <td>
                <button
                  className="btn"
                  style={{ padding: "2px 8px", fontSize: 12, background: c.ativa ? "#dc3545" : "#28a745", color: "white" }}
                  onClick={() => toggleAtiva(c)}
                >
                  {c.ativa ? "Desativar" : "Ativar"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
