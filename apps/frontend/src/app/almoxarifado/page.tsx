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
  processo_id: number | null; contrato_id: number | null; recebimento_id: number | null;
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

type Alerta = {
  id: number; item_id: number; movimentacao_id: number | null;
  saldo_no_momento: number; estoque_minimo: number;
  status: string; criado_em: string; resolvido_em: string | null;
};

type RequisicaoCompra = {
  id: number; item_id: number; departamento_id: number | null;
  alerta_id: number | null; processo_id: number | null;
  quantidade_sugerida: number; justificativa: string;
  status: string; solicitante_id: number | null; criado_em: string;
};

type ItemRec = {
  id: number; item_almoxarifado_id: number; quantidade_recebida: number;
  valor_unitario: number; valor_total: number; movimentacao_id: number | null;
};

type Recebimento = {
  id: number; processo_id: number; contrato_id: number | null; vendor_id: number | null;
  commitment_id: number | null; nota_fiscal: string; data_recebimento: string;
  status: string; observacoes: string; responsavel_id: number | null;
  created_at: string; itens: ItemRec[];
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
  const [tab, setTab] = useState<"dashboard" | "itens" | "movimentacoes" | "historico" | "recebimentos" | "requisicoes">("dashboard");

  const canWrite = role === "admin" || role === "procurement";

  const TABS = [
    { key: "dashboard", label: "Dashboard" },
    { key: "itens", label: "Itens / Materiais" },
    { key: "movimentacoes", label: "Entrada / Saída" },
    { key: "recebimentos", label: "Recebimentos de Compras" },
    { key: "requisicoes", label: "Requisições de Compra" },
    { key: "historico", label: "Histórico" },
  ] as const;

  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Almoxarifado</h1>
      <p className="muted">Controle de estoque de materiais e suprimentos.</p>

      {msg && <div className={`alert ${isError ? "error" : "success"}`} style={{ marginBottom: 8 }}>{msg}</div>}

      <AlertaBanner />

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
      {tab === "recebimentos" && <RecebimentosTab setMsg={setMsg} canWrite={canWrite} />}
      {tab === "requisicoes" && <RequisicaoTab setMsg={setMsg} canWrite={canWrite} />}
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


// ── Recebimentos de Compras ───────────────────────────────────────────────────

const STATUS_CHIP: Record<string, string> = {
  pendente: "pendente",
  conferido: "pago",
  recusado: "baixado",
};

function RecebimentosTab({ setMsg, canWrite }: { setMsg: (m: string) => void; canWrite: boolean }) {
  const [recs, setRecs] = useState<Paged<Recebimento> | null>(null);
  const [fProcesso, setFProcesso] = useState("");
  const [fContrato, setFContrato] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fInicio, setFInicio] = useState("");
  const [fFim, setFFim] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);

  // Formulário de criação
  const [fProcId, setFProcId] = useState("");
  const [fContratoId, setFContratoId] = useState("");
  const [fVendorId, setFVendorId] = useState("");
  const [fCommitmentId, setFCommitmentId] = useState("");
  const [fNF, setFNF] = useState("");
  const [fData, setFData] = useState(new Date().toISOString().slice(0, 10));
  const [fObs, setFObs] = useState("");
  const [fItens, setFItens] = useState<{ item_almoxarifado_id: string; quantidade_recebida: string; valor_unitario: string }[]>([
    { item_almoxarifado_id: "", quantidade_recebida: "", valor_unitario: "0" },
  ]);

  const buildQS = () => {
    const p = new URLSearchParams({ page: String(page), size: "20" });
    if (fProcesso) p.set("processo_id", fProcesso);
    if (fContrato) p.set("contrato_id", fContrato);
    if (fStatus) p.set("status", fStatus);
    if (fInicio) p.set("data_inicio", fInicio);
    if (fFim) p.set("data_fim", fFim);
    return p.toString();
  };

  const load = async () => {
    try {
      setRecs(await authJson(`/almoxarifado/recebimentos?${buildQS()}`));
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  useEffect(() => { load(); }, [page]);

  const addLinha = () => setFItens((prev) => [...prev, { item_almoxarifado_id: "", quantidade_recebida: "", valor_unitario: "0" }]);
  const removeLinha = (i: number) => setFItens((prev) => prev.filter((_, idx) => idx !== i));

  const handleCreate = async (ev: FormEvent) => {
    ev.preventDefault();
    try {
      await authJson("/almoxarifado/recebimentos", {
        method: "POST",
        body: JSON.stringify({
          processo_id: +fProcId,
          contrato_id: fContratoId ? +fContratoId : null,
          vendor_id: fVendorId ? +fVendorId : null,
          commitment_id: fCommitmentId ? +fCommitmentId : null,
          nota_fiscal: fNF,
          data_recebimento: fData,
          observacoes: fObs,
          itens: fItens.map((it) => ({
            item_almoxarifado_id: +it.item_almoxarifado_id,
            quantidade_recebida: +it.quantidade_recebida,
            valor_unitario: +it.valor_unitario,
          })),
        }),
      });
      setMsg("Recebimento registrado (pendente de confirmação).");
      setCreating(false);
      setFProcId(""); setFContratoId(""); setFNF(""); setFObs("");
      setFItens([{ item_almoxarifado_id: "", quantidade_recebida: "", valor_unitario: "0" }]);
      load();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const handleConfirmar = async (id: number) => {
    if (!confirm(`Confirmar recebimento #${id}?\nIsso criará entradas de estoque para cada item.`)) return;
    try {
      await authJson(`/almoxarifado/recebimentos/${id}/confirmar`, { method: "POST" });
      setMsg(`Recebimento #${id} confirmado — estoques atualizados.`);
      load();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const handleRecusar = async (id: number) => {
    const motivo = prompt("Motivo da recusa:");
    if (motivo === null) return;
    try {
      await authJson(`/almoxarifado/recebimentos/${id}/recusar?motivo=${encodeURIComponent(motivo)}`, { method: "POST" });
      setMsg(`Recebimento #${id} recusado.`);
      load();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  return (
    <section className="section-stack">
      <h2>Recebimentos de Material — Integração Compras ↔ Almoxarifado</h2>
      <p className="muted">
        Registre o recebimento físico de materiais vinculados a processos/contratos de compras.
        Ao confirmar, as entradas de estoque são criadas automaticamente com rastreabilidade completa.
      </p>

      <div className="toolbar" style={{ flexWrap: "wrap", gap: 8 }}>
        <input placeholder="ID Processo" value={fProcesso} onChange={(e) => setFProcesso(e.target.value)} style={{ width: 110 }} />
        <input placeholder="ID Contrato" value={fContrato} onChange={(e) => setFContrato(e.target.value)} style={{ width: 110 }} />
        <select value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
          <option value="">Todos status</option>
          <option value="pendente">Pendente</option>
          <option value="conferido">Conferido</option>
          <option value="recusado">Recusado</option>
        </select>
        <label style={{ display: "flex", gap: 4, alignItems: "center" }}>De: <input type="date" value={fInicio} onChange={(e) => setFInicio(e.target.value)} /></label>
        <label style={{ display: "flex", gap: 4, alignItems: "center" }}>Até: <input type="date" value={fFim} onChange={(e) => setFFim(e.target.value)} /></label>
        <button className="btn" onClick={() => { setPage(1); load(); }}>Filtrar</button>
        {canWrite && <button className="btn" style={{ background: "#17a2b8", color: "white" }} onClick={() => setCreating(!creating)}>
          {creating ? "Cancelar" : "+ Novo Recebimento"}
        </button>}
      </div>

      {creating && canWrite && (
        <div style={{ background: "#f0f8ff", border: "1px solid #bee5eb", borderRadius: 8, padding: 16, marginBottom: 12 }}>
          <h3>Registrar Recebimento</h3>
          <form className="form-grid" onSubmit={handleCreate}>
            <label>ID do Processo *<input value={fProcId} onChange={(e) => setFProcId(e.target.value)} required /></label>
            <label>ID do Contrato<input value={fContratoId} onChange={(e) => setFContratoId(e.target.value)} placeholder="opcional" /></label>
            <label>ID do Fornecedor<input value={fVendorId} onChange={(e) => setFVendorId(e.target.value)} placeholder="opcional" /></label>
            <label>ID do Empenho<input value={fCommitmentId} onChange={(e) => setFCommitmentId(e.target.value)} placeholder="opcional" /></label>
            <label>Nota Fiscal<input value={fNF} onChange={(e) => setFNF(e.target.value)} /></label>
            <label>Data do Recebimento<input type="date" value={fData} onChange={(e) => setFData(e.target.value)} required /></label>
            <label style={{ gridColumn: "1/-1" }}>Observações<input value={fObs} onChange={(e) => setFObs(e.target.value)} /></label>

            <div style={{ gridColumn: "1/-1" }}>
              <h4 style={{ margin: "8px 0 4px" }}>Itens do Recebimento</h4>
              {fItens.map((it, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 4, alignItems: "center", flexWrap: "wrap" }}>
                  <input placeholder="ID item" value={it.item_almoxarifado_id} style={{ width: 90 }}
                    onChange={(e) => setFItens((prev) => prev.map((r, idx) => idx === i ? { ...r, item_almoxarifado_id: e.target.value } : r))} required />
                  <input placeholder="Qtd" type="number" step="0.001" min="0.001" value={it.quantidade_recebida} style={{ width: 90 }}
                    onChange={(e) => setFItens((prev) => prev.map((r, idx) => idx === i ? { ...r, quantidade_recebida: e.target.value } : r))} required />
                  <input placeholder="Valor unit. R$" type="number" step="0.01" min="0" value={it.valor_unitario} style={{ width: 110 }}
                    onChange={(e) => setFItens((prev) => prev.map((r, idx) => idx === i ? { ...r, valor_unitario: e.target.value } : r))} />
                  {fItens.length > 1 && <button type="button" className="btn" onClick={() => removeLinha(i)}>×</button>}
                </div>
              ))}
              <button type="button" className="btn" onClick={addLinha} style={{ marginTop: 4 }}>+ Item</button>
            </div>

            <div style={{ display: "flex", gap: 8, gridColumn: "1/-1" }}>
              <button className="btn" type="submit" style={{ background: "#17a2b8", color: "white" }}>Registrar (Pendente)</button>
              <button className="btn" type="button" onClick={() => setCreating(false)}>Cancelar</button>
            </div>
          </form>
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>ID</th><th>Processo</th><th>Contrato</th><th>Fornecedor</th>
            <th>NF</th><th>Data</th><th>Itens</th><th>Status</th><th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {recs?.items.length ? recs.items.map((rec) => (
            <tr key={rec.id}>
              <td>{rec.id}</td>
              <td>{rec.processo_id}</td>
              <td>{rec.contrato_id || "—"}</td>
              <td>{rec.vendor_id || "—"}</td>
              <td>{rec.nota_fiscal || "—"}</td>
              <td>{rec.data_recebimento}</td>
              <td>{rec.itens?.length ?? "—"}</td>
              <td><span className={`chip ${STATUS_CHIP[rec.status] || "pendente"}`}>{rec.status}</span></td>
              <td style={{ display: "flex", gap: 4 }}>
                {rec.status === "pendente" && canWrite && (
                  <>
                    <button className="btn" style={{ background: "#28a745", color: "white" }} onClick={() => handleConfirmar(rec.id)}>
                      ✓ Confirmar
                    </button>
                    <button className="btn" style={{ background: "#dc3545", color: "white" }} onClick={() => handleRecusar(rec.id)}>
                      ✗ Recusar
                    </button>
                  </>
                )}
                {rec.status !== "pendente" && (
                  <span className="muted" style={{ fontSize: 12 }}>—</span>
                )}
              </td>
            </tr>
          )) : <tr><td colSpan={9} className="empty-state">Nenhum recebimento encontrado.</td></tr>}
        </tbody>
      </table>
      <div className="pagination">
        <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
        <span>Pág {page} · Total: {recs?.total || 0}</span>
        <button className="btn" disabled={(recs?.items?.length || 0) < 20} onClick={() => setPage((p) => p + 1)}>Próxima</button>
      </div>
    </section>
  );
}


// ── Alerta Banner ─────────────────────────────────────────────────────────────

function AlertaBanner() {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    authJson("/almoxarifado/alertas?status=aberto&size=1")
      .then((d: Paged<Alerta>) => setCount(d.total))
      .catch(() => {});
  }, []);

  if (!count) return null;

  return (
    <div style={{
      background: "#fff3cd", border: "1px solid #ffc107",
      borderRadius: 6, padding: "8px 14px", marginBottom: 12,
      display: "flex", alignItems: "center", gap: 8,
    }}>
      <span style={{ fontSize: 18 }}>⚠️</span>
      <span>
        <strong>{count} item(ns) abaixo do estoque mínimo.</strong>
        {" "}Acesse a aba <em>Requisições de Compra</em> para criar requisições de reposição.
      </span>
    </div>
  );
}


// ── Requisições de Compra ─────────────────────────────────────────────────────

const REQ_STATUS_CHIP: Record<string, string> = {
  rascunho: "pendente",
  aprovada: "pago",
  vinculada: "pago",
  cancelada: "baixado",
};

const ALERTA_STATUS_CHIP: Record<string, string> = {
  aberto: "pendente",
  em_processo: "pago",
  resolvido: "baixado",
};

function RequisicaoTab({ setMsg, canWrite }: { setMsg: (m: string) => void; canWrite: boolean }) {
  const [reqs, setReqs] = useState<Paged<RequisicaoCompra> | null>(null);
  const [alertas, setAlertas] = useState<Paged<Alerta> | null>(null);
  const [tabInner, setTabInner] = useState<"alertas" | "requisicoes">("alertas");
  const [page, setPage] = useState(1);
  const [fStatus, setFStatus] = useState("");
  const [fItemId, setFItemId] = useState("");
  const [creating, setCreating] = useState(false);

  // Formulário nova requisição
  const [fItemReq, setFItemReq] = useState("");
  const [fDeptId, setFDeptId] = useState("");
  const [fAlertaId, setFAlertaId] = useState("");
  const [fQtd, setFQtd] = useState("");
  const [fJustif, setFJustif] = useState("");
  const [fProcId, setFProcId] = useState("");
  const [linkingReqId, setLinkingReqId] = useState<number | null>(null);

  const loadAlertas = async () => {
    try {
      const qs = new URLSearchParams({ page: "1", size: "50", status: "aberto" }).toString();
      setAlertas(await authJson(`/almoxarifado/alertas?${qs}`));
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const loadReqs = async () => {
    try {
      const p = new URLSearchParams({ page: String(page), size: "20" });
      if (fStatus) p.set("status", fStatus);
      if (fItemId) p.set("item_id", fItemId);
      setReqs(await authJson(`/almoxarifado/requisicoes?${p}`));
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  useEffect(() => { loadAlertas(); loadReqs(); }, [page]);

  const handleCreateReq = async (ev: FormEvent) => {
    ev.preventDefault();
    try {
      await authJson("/almoxarifado/requisicoes", {
        method: "POST",
        body: JSON.stringify({
          item_id: +fItemReq,
          departamento_id: fDeptId ? +fDeptId : null,
          alerta_id: fAlertaId ? +fAlertaId : null,
          quantidade_sugerida: +fQtd,
          justificativa: fJustif,
        }),
      });
      setMsg("Requisição criada com sucesso.");
      setCreating(false);
      setFItemReq(""); setFDeptId(""); setFAlertaId(""); setFQtd(""); setFJustif("");
      loadReqs(); loadAlertas();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const handleAprovar = async (id: number) => {
    try {
      await authJson(`/almoxarifado/requisicoes/${id}/aprovar`, { method: "POST" });
      setMsg(`Requisição #${id} aprovada.`);
      loadReqs();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const handleCancelar = async (id: number) => {
    if (!confirm(`Cancelar requisição #${id}?`)) return;
    try {
      await authJson(`/almoxarifado/requisicoes/${id}/cancelar`, { method: "POST" });
      setMsg(`Requisição #${id} cancelada.`);
      loadReqs(); loadAlertas();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const handleVincular = async (id: number) => {
    if (!fProcId) return;
    try {
      await authJson(`/almoxarifado/requisicoes/${id}/vincular-processo`,
        { method: "POST", body: JSON.stringify({ processo_id: +fProcId }) });
      setMsg(`Requisição #${id} vinculada ao processo ${fProcId}.`);
      setLinkingReqId(null); setFProcId("");
      loadReqs(); loadAlertas();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  const handleResolverAlerta = async (id: number) => {
    if (!confirm(`Marcar alerta #${id} como resolvido manualmente?`)) return;
    try {
      await authJson(`/almoxarifado/alertas/${id}/resolver`, { method: "POST" });
      setMsg(`Alerta #${id} resolvido.`);
      loadAlertas();
    } catch (e) { setMsg("Erro: " + msgFrom(e)); }
  };

  return (
    <section className="section-stack">
      <h2>Requisições de Compra e Alertas de Estoque</h2>
      <p className="muted">
        Alertas são gerados automaticamente quando uma saída deixa o saldo abaixo do mínimo.
        A partir do alerta você pode criar uma requisição de compra e vinculá-la a um processo licitatório.
      </p>

      <nav style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button className={`tab-btn ${tabInner === "alertas" ? "active" : ""}`}
          onClick={() => setTabInner("alertas")}>
          ⚠️ Alertas {alertas?.total ? `(${alertas.total})` : ""}
        </button>
        <button className={`tab-btn ${tabInner === "requisicoes" ? "active" : ""}`}
          onClick={() => setTabInner("requisicoes")}>
          📋 Requisições {reqs?.total ? `(${reqs.total})` : ""}
        </button>
      </nav>

      {tabInner === "alertas" && (
        <div>
          <h3>Alertas de Estoque Mínimo (Abertos)</h3>
          <table>
            <thead>
              <tr><th>ID</th><th>Item</th><th>Saldo Atual</th><th>Mínimo</th><th>Criado em</th><th>Status</th><th>Ações</th></tr>
            </thead>
            <tbody>
              {alertas?.items.length ? alertas.items.map((a) => (
                <tr key={a.id}>
                  <td>{a.id}</td>
                  <td>{a.item_id}</td>
                  <td style={{ color: a.saldo_no_momento <= 0 ? "#dc3545" : "#856404" }}>
                    <strong>{a.saldo_no_momento}</strong>
                  </td>
                  <td>{a.estoque_minimo}</td>
                  <td>{a.criado_em.slice(0, 10)}</td>
                  <td><span className={`chip ${ALERTA_STATUS_CHIP[a.status] || "pendente"}`}>{a.status}</span></td>
                  <td style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                    {canWrite && a.status === "aberto" && (
                      <>
                        <button className="btn" style={{ background: "#17a2b8", color: "white", fontSize: 12 }}
                          onClick={() => { setFAlertaId(String(a.id)); setFItemReq(String(a.item_id)); setCreating(true); setTabInner("requisicoes"); }}>
                          + Requisição
                        </button>
                        <button className="btn" style={{ background: "#6c757d", color: "white", fontSize: 12 }}
                          onClick={() => handleResolverAlerta(a.id)}>
                          ✓ Resolver
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              )) : <tr><td colSpan={7} className="empty-state">Nenhum alerta aberto. Estoque dentro dos limites.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tabInner === "requisicoes" && (
        <div>
          <div className="toolbar" style={{ flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
            <input placeholder="ID Item" value={fItemId} onChange={(e) => setFItemId(e.target.value)} style={{ width: 90 }} />
            <select value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
              <option value="">Todos status</option>
              <option value="rascunho">Rascunho</option>
              <option value="aprovada">Aprovada</option>
              <option value="vinculada">Vinculada</option>
              <option value="cancelada">Cancelada</option>
            </select>
            <button className="btn" onClick={() => { setPage(1); loadReqs(); }}>Filtrar</button>
            {canWrite && <button className="btn" style={{ background: "#17a2b8", color: "white" }}
              onClick={() => setCreating(!creating)}>
              {creating ? "Cancelar" : "+ Nova Requisição"}
            </button>}
          </div>

          {creating && canWrite && (
            <div style={{ background: "#f0f8ff", border: "1px solid #bee5eb", borderRadius: 8, padding: 16, marginBottom: 12 }}>
              <h3>Nova Requisição de Compra</h3>
              <form className="form-grid" onSubmit={handleCreateReq}>
                <label>ID Item *<input value={fItemReq} onChange={(e) => setFItemReq(e.target.value)} required /></label>
                <label>ID Departamento<input value={fDeptId} onChange={(e) => setFDeptId(e.target.value)} placeholder="opcional" /></label>
                <label>ID Alerta<input value={fAlertaId} onChange={(e) => setFAlertaId(e.target.value)} placeholder="opcional" /></label>
                <label>Quantidade Sugerida *<input type="number" step="0.001" min="0.001" value={fQtd} onChange={(e) => setFQtd(e.target.value)} required /></label>
                <label style={{ gridColumn: "1/-1" }}>Justificativa<input value={fJustif} onChange={(e) => setFJustif(e.target.value)} /></label>
                <div style={{ display: "flex", gap: 8, gridColumn: "1/-1" }}>
                  <button className="btn" type="submit" style={{ background: "#17a2b8", color: "white" }}>Criar Rascunho</button>
                  <button className="btn" type="button" onClick={() => setCreating(false)}>Cancelar</button>
                </div>
              </form>
            </div>
          )}

          <table>
            <thead>
              <tr><th>ID</th><th>Item</th><th>Dept</th><th>Qtd Sug.</th><th>Alerta</th><th>Processo</th><th>Status</th><th>Ações</th></tr>
            </thead>
            <tbody>
              {reqs?.items.length ? reqs.items.map((req) => (
                <tr key={req.id}>
                  <td>{req.id}</td>
                  <td>{req.item_id}</td>
                  <td>{req.departamento_id || "—"}</td>
                  <td>{req.quantidade_sugerida}</td>
                  <td>{req.alerta_id || "—"}</td>
                  <td>{req.processo_id || "—"}</td>
                  <td><span className={`chip ${REQ_STATUS_CHIP[req.status] || "pendente"}`}>{req.status}</span></td>
                  <td style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                    {canWrite && req.status === "rascunho" && (
                      <button className="btn" style={{ background: "#28a745", color: "white", fontSize: 12 }}
                        onClick={() => handleAprovar(req.id)}>✓ Aprovar</button>
                    )}
                    {canWrite && req.status !== "cancelada" && req.status !== "vinculada" && (
                      <button className="btn" style={{ background: "#dc3545", color: "white", fontSize: 12 }}
                        onClick={() => handleCancelar(req.id)}>✗ Cancelar</button>
                    )}
                    {canWrite && (req.status === "rascunho" || req.status === "aprovada") && (
                      linkingReqId === req.id ? (
                        <span style={{ display: "flex", gap: 4 }}>
                          <input placeholder="ID Processo" value={fProcId} style={{ width: 110 }}
                            onChange={(e) => setFProcId(e.target.value)} />
                          <button className="btn" style={{ background: "#17a2b8", color: "white", fontSize: 12 }}
                            onClick={() => handleVincular(req.id)}>OK</button>
                          <button className="btn" style={{ fontSize: 12 }}
                            onClick={() => { setLinkingReqId(null); setFProcId(""); }}>×</button>
                        </span>
                      ) : (
                        <button className="btn" style={{ fontSize: 12 }}
                          onClick={() => setLinkingReqId(req.id)}>🔗 Vincular</button>
                      )
                    )}
                  </td>
                </tr>
              )) : <tr><td colSpan={8} className="empty-state">Nenhuma requisição encontrada.</td></tr>}
            </tbody>
          </table>
          <div className="pagination">
            <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
            <span>Pág {page} · Total: {reqs?.total || 0}</span>
            <button className="btn" disabled={(reqs?.items?.length || 0) < 20} onClick={() => setPage((p) => p + 1)}>Próxima</button>
          </div>
        </div>
      )}
    </section>
  );
}
