"use client";

import { FormEvent, useEffect, useState } from "react";
import { authJson, authDownload, readCookie } from "@/lib/auth";

// ── Types ─────────────────────────────────────────────────────────────────────

type Paged<T> = { total: number; page: number; size: number; items: T[] };

type Item = {
  id: number; codigo: string; descricao: string; unidade: string;
  categoria: string; localizacao: string; estoque_minimo: number;
  estoque_atual: number; valor_unitario: number; ativo: boolean;
};

type Movimentacao = {
  id: number; item_id: number; tipo: string; quantidade: number;
  valor_unitario: number; valor_total: number; data_movimentacao: string;
  departamento_id: number | null; responsavel_id: number | null;
  documento_ref: string; saldo_pos: number;
};

type Saldo = {
  item_id: number; codigo: string; descricao: string; unidade: string;
  estoque_atual: number; estoque_minimo: number; valor_unitario: number;
  valor_estoque: number; abaixo_minimo: boolean;
};

type Dashboard = {
  total_itens_ativos: number; itens_abaixo_minimo: number;
  valor_total_estoque: number; entradas_no_mes: number; saidas_no_mes: number;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const CATEGORIAS = ["geral", "material_consumo", "permanente", "medicamento", "limpeza", "informatica"];
const UNIDADES = ["UN", "CX", "RM", "KG", "L", "PCT", "MT", "PAR"];

function fmtBRL(v: number) { return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
function msgFrom(e: unknown) { return e instanceof Error ? e.message : "Falha na operação"; }

const CHIP: Record<string, string> = { entrada: "pago", saida: "pendente" };

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AlmoxarifadoPage() {
  const [role] = useState(() => readCookie("role"));
  const [msg, setMsg] = useState("");
  const isError = msg.toLowerCase().includes("erro") || msg.toLowerCase().includes("falha");
  const [tab, setTab] = useState<"dashboard" | "itens" | "movimentacoes" | "historico">("dashboard");

  const canWrite = role === "admin" || role === "procurement";

  const TABS = [
    { key: "dashboard", label: "Dashboard" },
    { key: "itens", label: "Itens / Materiais" },
    { key: "movimentacoes", label: "Entrada / Saída" },
    { key: "historico", label: "Histórico" },
  ] as const;

  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Almoxarifado</h1>
      <p className="muted">Controle de estoque de materiais e suprimentos.</p>

      {msg && <div className={`alert ${isError ? "error" : "success"}`} style={{ marginBottom: 8 }}>{msg}</div>}

      <nav style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {TABS.map((t) => (
          <button key={t.key} className={`tab-btn ${tab === t.key ? "active" : ""}`}
            onClick={() => { setTab(t.key); setMsg(""); }}>
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "dashboard" && <DashboardTab />}
      {tab === "itens" && <ItensTab setMsg={setMsg} canWrite={canWrite} />}
      {tab === "movimentacoes" && <MovimentacaoTab setMsg={setMsg} canWrite={canWrite} />}
      {tab === "historico" && <HistoricoTab setMsg={setMsg} />}
    </main>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

function DashboardTab() {
  const [data, setData] = useState<Dashboard | null>(null);

  useEffect(() => {
    authJson("/almoxarifado/dashboard").then(setData).catch(() => null);
  }, []);

  if (!data) return <p className="muted">Carregando…</p>;

  const cards = [
    { label: "Itens ativos", value: data.total_itens_ativos },
    { label: "Abaixo do mínimo", value: data.itens_abaixo_minimo, warn: data.itens_abaixo_minimo > 0 },
    { label: "Valor em estoque", value: fmtBRL(data.valor_total_estoque) },
    { label: "Entradas no mês", value: data.entradas_no_mes },
    { label: "Saídas no mês", value: data.saidas_no_mes },
  ];

  return (
    <section>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
        {cards.map((c) => (
          <div key={c.label} style={{
            background: c.warn ? "#fff3cd" : "var(--card-bg, #f5f5f5)",
            border: c.warn ? "1px solid #ffc107" : "1px solid #ddd",
            borderRadius: 8, padding: "12px 20px", minWidth: 160,
          }}>
            <div className="muted" style={{ fontSize: 12 }}>{c.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{c.value}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── Itens ─────────────────────────────────────────────────────────────────────

function ItensTab({ setMsg, canWrite }: { setMsg: (m: string) => void; canWrite: boolean }) {
  const [itens, setItens] = useState<Paged<Item> | null>(null);
  const [search, setSearch] = useState("");
  const [categoria, setCategoria] = useState("");
  const [apenasAbaixo, setApenasAbaixo] = useState(false);
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Item | null>(null);

  // Form create
  const [fCodigo, setFCodigo] = useState("");
  const [fDescricao, setFDescricao] = useState("");
  const [fUnidade, setFUnidade] = useState("UN");
  const [fCategoria, setFCategoria] = useState("geral");
  const [fLocalizacao, setFLocalizacao] = useState("");
  const [fEstoqueMin, setFEstoqueMin] = useState("0");
  const [fValorUnit, setFValorUnit] = useState("0");

  const load = async () => {
    try {
      const qs = new URLSearchParams({ page: String(page), size: "20" });
      if (search) qs.set("search", search);
      if (categoria) qs.set("categoria", categoria);
      if (apenasAbaixo) qs.set("abaixo_minimo", "true");
      setItens(await authJson(`/almoxarifado/itens?${qs}`));
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  useEffect(() => { load(); }, [page, categoria, apenasAbaixo]);

  const handleCreate = async (ev: FormEvent) => {
    ev.preventDefault();
    try {
      await authJson("/almoxarifado/itens", { method: "POST", body: JSON.stringify({
        codigo: fCodigo, descricao: fDescricao, unidade: fUnidade, categoria: fCategoria,
        localizacao: fLocalizacao, estoque_minimo: +fEstoqueMin, valor_unitario: +fValorUnit,
      })});
      setMsg("Item cadastrado."); setFCodigo(""); setFDescricao(""); setFLocalizacao(""); load();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const handleUpdate = async (ev: FormEvent) => {
    ev.preventDefault();
    if (!editing) return;
    try {
      await authJson(`/almoxarifado/itens/${editing.id}`, { method: "PUT", body: JSON.stringify({
        descricao: editing.descricao, unidade: editing.unidade, categoria: editing.categoria,
        localizacao: editing.localizacao, estoque_minimo: editing.estoque_minimo,
        valor_unitario: editing.valor_unitario, ativo: editing.ativo,
      })});
      setMsg("Item atualizado."); setEditing(null); load();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const handleSaldo = async (id: number) => {
    try {
      const s: Saldo = await authJson(`/almoxarifado/saldo/${id}`);
      alert(`Saldo: ${s.estoque_atual} ${s.unidade}\nValor em estoque: ${fmtBRL(s.valor_estoque)}\n${s.abaixo_minimo ? "⚠️ ABAIXO DO MÍNIMO" : "✅ Estoque OK"}`);
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  return (
    <section className="section-stack">
      <div className="toolbar" style={{ flexWrap: "wrap", gap: 8 }}>
        <input placeholder="Buscar código ou descrição…" value={search} onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load()} style={{ minWidth: 200 }} />
        <select value={categoria} onChange={(e) => setCategoria(e.target.value)}>
          <option value="">Todas as categorias</option>
          {CATEGORIAS.map((c) => <option key={c}>{c}</option>)}
        </select>
        <label style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <input type="checkbox" checked={apenasAbaixo} onChange={(e) => setApenasAbaixo(e.target.checked)} />
          Só abaixo do mínimo
        </label>
        <button className="btn" onClick={load}>Buscar</button>
        <button className="btn" onClick={() => authDownload("/almoxarifado/itens?export=csv", "itens_almoxarifado.csv").catch(() => setMsg("Erro ao exportar"))}>
          Exportar CSV
        </button>
      </div>

      <table>
        <thead>
          <tr>
            <th>Código</th><th>Descrição</th><th>Un.</th><th>Cat.</th>
            <th>Saldo</th><th>Mínimo</th><th>Valor unit.</th><th>Status</th><th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {itens?.items.length ? itens.items.map((it) => (
            <tr key={it.id} style={it.estoque_atual < it.estoque_minimo ? { background: "#fff3cd" } : {}}>
              <td>{it.codigo}</td>
              <td>{it.descricao}</td>
              <td>{it.unidade}</td>
              <td>{it.categoria}</td>
              <td><b>{it.estoque_atual}</b></td>
              <td>{it.estoque_minimo}</td>
              <td>{fmtBRL(it.valor_unitario)}</td>
              <td><span className={`chip ${it.ativo ? "pago" : "baixado"}`}>{it.ativo ? "ativo" : "inativo"}</span></td>
              <td style={{ display: "flex", gap: 4 }}>
                <button className="btn" onClick={() => handleSaldo(it.id)}>Saldo</button>
                {canWrite && <button className="btn" onClick={() => setEditing(it)}>Editar</button>}
              </td>
            </tr>
          )) : <tr><td colSpan={9} className="empty-state">Nenhum item encontrado.</td></tr>}
        </tbody>
      </table>
      <div className="pagination">
        <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
        <span>Pág {page} · Total: {itens?.total || 0}</span>
        <button className="btn" disabled={(itens?.items?.length || 0) < 20} onClick={() => setPage((p) => p + 1)}>Próxima</button>
      </div>

      {editing && (
        <div style={{ background: "#f9f9f9", border: "1px solid #ddd", borderRadius: 8, padding: 16, marginTop: 16 }}>
          <h3>Editar item #{editing.id} — {editing.codigo}</h3>
          <form className="form-grid" onSubmit={handleUpdate}>
            <label>Descrição<input value={editing.descricao} onChange={(e) => setEditing({ ...editing, descricao: e.target.value })} required /></label>
            <label>Unidade
              <select value={editing.unidade} onChange={(e) => setEditing({ ...editing, unidade: e.target.value })}>
                {UNIDADES.map((u) => <option key={u}>{u}</option>)}
              </select>
            </label>
            <label>Categoria
              <select value={editing.categoria} onChange={(e) => setEditing({ ...editing, categoria: e.target.value })}>
                {CATEGORIAS.map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
            <label>Localização<input value={editing.localizacao} onChange={(e) => setEditing({ ...editing, localizacao: e.target.value })} /></label>
            <label>Estoque mínimo<input type="number" step="0.01" value={editing.estoque_minimo} onChange={(e) => setEditing({ ...editing, estoque_minimo: +e.target.value })} /></label>
            <label>Valor unitário (R$)<input type="number" step="0.01" value={editing.valor_unitario} onChange={(e) => setEditing({ ...editing, valor_unitario: +e.target.value })} /></label>
            <label style={{ display: "flex", gap: 4, alignItems: "center" }}>
              <input type="checkbox" checked={editing.ativo} onChange={(e) => setEditing({ ...editing, ativo: e.target.checked })} /> Ativo
            </label>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn" type="submit">Salvar</button>
              <button className="btn" type="button" onClick={() => setEditing(null)}>Cancelar</button>
            </div>
          </form>
        </div>
      )}

      {canWrite && (
        <details style={{ marginTop: 16 }}>
          <summary style={{ cursor: "pointer", fontWeight: 600 }}>Cadastrar novo item</summary>
          <form className="form-grid" onSubmit={handleCreate} style={{ marginTop: 8 }}>
            <label>Código *<input value={fCodigo} onChange={(e) => setFCodigo(e.target.value)} required /></label>
            <label>Descrição *<input value={fDescricao} onChange={(e) => setFDescricao(e.target.value)} required /></label>
            <label>Unidade
              <select value={fUnidade} onChange={(e) => setFUnidade(e.target.value)}>
                {UNIDADES.map((u) => <option key={u}>{u}</option>)}
              </select>
            </label>
            <label>Categoria
              <select value={fCategoria} onChange={(e) => setFCategoria(e.target.value)}>
                {CATEGORIAS.map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
            <label>Localização<input value={fLocalizacao} onChange={(e) => setFLocalizacao(e.target.value)} /></label>
            <label>Estoque mínimo<input type="number" step="0.01" value={fEstoqueMin} onChange={(e) => setFEstoqueMin(e.target.value)} /></label>
            <label>Valor unitário (R$)<input type="number" step="0.01" value={fValorUnit} onChange={(e) => setFValorUnit(e.target.value)} /></label>
            <button className="btn" type="submit">Cadastrar</button>
          </form>
        </details>
      )}
    </section>
  );
}

// ── Entrada / Saída ───────────────────────────────────────────────────────────

function MovimentacaoTab({ setMsg, canWrite }: { setMsg: (m: string) => void; canWrite: boolean }) {
  const [tipo, setTipo] = useState<"entrada" | "saida">("entrada");
  const [itemId, setItemId] = useState("");
  const [quantidade, setQuantidade] = useState("");
  const [valorUnit, setValorUnit] = useState("0");
  const [dataMovimentacao, setDataMovimentacao] = useState(new Date().toISOString().slice(0, 10));
  const [deptoId, setDeptoId] = useState("");
  const [docRef, setDocRef] = useState("");
  const [obs, setObs] = useState("");
  const [saldoPreview, setSaldoPreview] = useState<Saldo | null>(null);

  const loadSaldo = async (id: string) => {
    if (!id) { setSaldoPreview(null); return; }
    try { setSaldoPreview(await authJson(`/almoxarifado/saldo/${id}`)); }
    catch { setSaldoPreview(null); }
  };

  const handleSubmit = async (ev: FormEvent) => {
    ev.preventDefault();
    try {
      const r = await authJson("/almoxarifado/movimentacoes", {
        method: "POST",
        body: JSON.stringify({
          item_id: +itemId, tipo, quantidade: +quantidade, valor_unitario: +valorUnit,
          data_movimentacao: dataMovimentacao,
          departamento_id: deptoId ? +deptoId : null,
          documento_ref: docRef, observacoes: obs,
        }),
      });
      setMsg(`${tipo === "entrada" ? "Entrada" : "Saída"} registrada. Saldo atual: ${r.saldo_pos}`);
      setQuantidade(""); setDocRef(""); setObs("");
      loadSaldo(itemId);
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  if (!canWrite) return <p className="muted">Acesso restrito a administradores e compras.</p>;

  return (
    <section className="section-stack">
      <h2>Registrar Movimentação</h2>
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        {(["entrada", "saida"] as const).map((t) => (
          <button key={t} className={`btn ${tipo === t ? "active" : ""}`}
            style={{ fontWeight: tipo === t ? 700 : 400, background: tipo === t ? (t === "entrada" ? "#d4edda" : "#f8d7da") : undefined }}
            onClick={() => setTipo(t)}>
            {t === "entrada" ? "📥 Entrada" : "📤 Saída / Requisição"}
          </button>
        ))}
      </div>

      {saldoPreview && (
        <div style={{ background: saldoPreview.abaixo_minimo ? "#fff3cd" : "#d4edda", borderRadius: 8, padding: 12, marginBottom: 12 }}>
          <b>{saldoPreview.descricao}</b> ({saldoPreview.codigo}) · Saldo atual: <b>{saldoPreview.estoque_atual} {saldoPreview.unidade}</b>
          {saldoPreview.abaixo_minimo && <span style={{ color: "#856404", marginLeft: 8 }}>⚠️ Abaixo do mínimo ({saldoPreview.estoque_minimo})</span>}
        </div>
      )}

      <form className="form-grid" onSubmit={handleSubmit}>
        <label>ID do Item *
          <input value={itemId} onChange={(e) => { setItemId(e.target.value); loadSaldo(e.target.value); }} required />
        </label>
        <label>Quantidade *<input type="number" step="0.001" min="0.001" value={quantidade} onChange={(e) => setQuantidade(e.target.value)} required /></label>
        <label>Valor unitário (R$)<input type="number" step="0.01" min="0" value={valorUnit} onChange={(e) => setValorUnit(e.target.value)} /></label>
        <label>Data<input type="date" value={dataMovimentacao} onChange={(e) => setDataMovimentacao(e.target.value)} required /></label>
        {tipo === "saida" && (
          <label>Departamento (ID)<input value={deptoId} onChange={(e) => setDeptoId(e.target.value)} placeholder="opcional" /></label>
        )}
        <label>Documento referência (NF, REQ…)<input value={docRef} onChange={(e) => setDocRef(e.target.value)} /></label>
        <label>Observações<input value={obs} onChange={(e) => setObs(e.target.value)} /></label>
        <button className="btn" type="submit"
          style={{ background: tipo === "entrada" ? "#28a745" : "#dc3545", color: "white" }}>
          Confirmar {tipo === "entrada" ? "Entrada" : "Saída"}
        </button>
      </form>
    </section>
  );
}

// ── Histórico ─────────────────────────────────────────────────────────────────

function HistoricoTab({ setMsg }: { setMsg: (m: string) => void }) {
  const [movs, setMovs] = useState<Paged<Movimentacao> | null>(null);
  const [fItemId, setFItemId] = useState("");
  const [fTipo, setFTipo] = useState("");
  const [fDepto, setFDepto] = useState("");
  const [fInicio, setFInicio] = useState("");
  const [fFim, setFFim] = useState("");
  const [page, setPage] = useState(1);

  const buildQS = () => {
    const p = new URLSearchParams({ page: String(page), size: "20" });
    if (fItemId) p.set("item_id", fItemId);
    if (fTipo) p.set("tipo", fTipo);
    if (fDepto) p.set("departamento_id", fDepto);
    if (fInicio) p.set("data_inicio", fInicio);
    if (fFim) p.set("data_fim", fFim);
    return p.toString();
  };

  const load = async () => {
    try {
      setMovs(await authJson(`/almoxarifado/movimentacoes?${buildQS()}`));
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const exportCSV = () => {
    const p = new URLSearchParams();
    if (fItemId) p.set("item_id", fItemId);
    if (fTipo) p.set("tipo", fTipo);
    if (fDepto) p.set("departamento_id", fDepto);
    if (fInicio) p.set("data_inicio", fInicio);
    if (fFim) p.set("data_fim", fFim);
    p.set("export", "csv");
    authDownload(`/almoxarifado/movimentacoes?${p.toString()}`, "movimentacoes.csv").catch(() => setMsg("Erro ao exportar"));
  };

  useEffect(() => { load(); }, [page]);

  return (
    <section className="section-stack">
      <h2>Histórico de Movimentações</h2>
      <div className="toolbar" style={{ flexWrap: "wrap", gap: 8 }}>
        <input placeholder="ID item" value={fItemId} onChange={(e) => setFItemId(e.target.value)} style={{ width: 90 }} />
        <select value={fTipo} onChange={(e) => setFTipo(e.target.value)}>
          <option value="">Todos tipos</option>
          <option value="entrada">Entrada</option>
          <option value="saida">Saída</option>
        </select>
        <input placeholder="ID depto" value={fDepto} onChange={(e) => setFDepto(e.target.value)} style={{ width: 90 }} />
        <label style={{ display: "flex", gap: 4, alignItems: "center" }}>De: <input type="date" value={fInicio} onChange={(e) => setFInicio(e.target.value)} /></label>
        <label style={{ display: "flex", gap: 4, alignItems: "center" }}>Até: <input type="date" value={fFim} onChange={(e) => setFFim(e.target.value)} /></label>
        <button className="btn" onClick={() => { setPage(1); load(); }}>Filtrar</button>
        <button className="btn" onClick={exportCSV}>Exportar CSV</button>
      </div>

      <table>
        <thead>
          <tr>
            <th>ID</th><th>Item</th><th>Tipo</th><th>Qtd</th><th>V. Unit</th><th>V. Total</th>
            <th>Data</th><th>Depto</th><th>Doc. Ref</th><th>Saldo após</th>
          </tr>
        </thead>
        <tbody>
          {movs?.items.length ? movs.items.map((m) => (
            <tr key={m.id}>
              <td>{m.id}</td>
              <td>{m.item_id}</td>
              <td><span className={`chip ${CHIP[m.tipo] || "pendente"}`}>{m.tipo}</span></td>
              <td>{m.quantidade}</td>
              <td>{fmtBRL(m.valor_unitario)}</td>
              <td>{fmtBRL(m.valor_total)}</td>
              <td>{m.data_movimentacao}</td>
              <td>{m.departamento_id || "—"}</td>
              <td>{m.documento_ref || "—"}</td>
              <td><b>{m.saldo_pos}</b></td>
            </tr>
          )) : <tr><td colSpan={10} className="empty-state">Nenhuma movimentação encontrada.</td></tr>}
        </tbody>
      </table>
      <div className="pagination">
        <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
        <span>Pág {page} · Total: {movs?.total || 0}</span>
        <button className="btn" disabled={(movs?.items?.length || 0) < 20} onClick={() => setPage((p) => p + 1)}>Próxima</button>
      </div>
    </section>
  );
}
