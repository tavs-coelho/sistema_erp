"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { authJson } from "@/lib/auth";

type PPA = { id: number; period_start: number; period_end: number; description: string; status: string };
type PPAProgram = { id: number; ppa_id: number; code: string; name: string; objective: string; estimated_amount: number };
type LDO = { id: number; fiscal_year_id: number; description: string; status: string };
type LDOGoal = { id: number; ldo_id: number; code: string; description: string; category: string };
type LOA = { id: number; fiscal_year_id: number; ldo_id: number | null; description: string; total_revenue: number; total_expenditure: number; status: string };
type LOAItem = { id: number; loa_id: number; function_code: string; subfunction_code: string; program_code: string; action_code: string; description: string; category: string; authorized_amount: number; executed_amount: number };
type ExecutionSummary = { loa_id: number; description: string; status: string; total_authorized: number; total_executed: number; execution_rate: number; by_function: { function_code: string; authorized: number; executed: number }[] };
type FiscalYear = { id: number; year: number; active: boolean };

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "Falha na operação";
}

export default function OrcamentoPage() {
  const { toast } = useToast();

  const [activeTab, setActiveTab] = useState<"ppa" | "ldo" | "loa">("ppa");
  const [fiscalYears, setFiscalYears] = useState<FiscalYear[]>([]);

  // PPA
  const [ppas, setPpas] = useState<PPA[]>([]);
  const [selectedPpa, setSelectedPpa] = useState<number | "">("");
  const [ppaPrograms, setPpaPrograms] = useState<PPAProgram[]>([]);
  const [ppaStart, setPpaStart] = useState(2026);
  const [ppaEnd, setPpaEnd] = useState(2029);
  const [ppaDesc, setPpaDesc] = useState("PPA 2026–2029");

  const [progCode, setProgCode] = useState("PROG-01");
  const [progName, setProgName] = useState("Saúde e Bem-Estar");
  const [progObjective, setProgObjective] = useState("Ampliar cobertura de saúde pública");
  const [progAmount, setProgAmount] = useState(1500000);

  // LDO
  const [ldos, setLdos] = useState<LDO[]>([]);
  const [selectedLdo, setSelectedLdo] = useState<number | "">("");
  const [ldoGoals, setLdoGoals] = useState<LDOGoal[]>([]);
  const [ldoFyId, setLdoFyId] = useState(1);
  const [ldoDesc, setLdoDesc] = useState("LDO 2026");

  const [goalCode, setGoalCode] = useState("META-01");
  const [goalDesc, setGoalDesc] = useState("Manter resultado primário positivo");
  const [goalCategory, setGoalCategory] = useState("meta_fiscal");

  // LOA
  const [loas, setLoas] = useState<LOA[]>([]);
  const [selectedLoa, setSelectedLoa] = useState<number | "">("");
  const [loaItems, setLoaItems] = useState<LOAItem[]>([]);
  const [loaSummary, setLoaSummary] = useState<ExecutionSummary | null>(null);
  const [loaFyId, setLoaFyId] = useState(1);
  const [loaLdoId, setLoaLdoId] = useState<number | "">("");
  const [loaDesc, setLoaDesc] = useState("LOA 2026");
  const [loaRevenue, setLoaRevenue] = useState(8000000);

  const [itemFuncCode, setItemFuncCode] = useState("10");
  const [itemSubfuncCode, setItemSubfuncCode] = useState("301");
  const [itemProgCode, setItemProgCode] = useState("0015");
  const [itemActionCode, setItemActionCode] = useState("2001");
  const [itemDesc, setItemDesc] = useState("Atenção básica à saúde");
  const [itemCategory, setItemCategory] = useState("despesa");
  const [itemAmount, setItemAmount] = useState(800000);

  const loadFiscalYears = async () => {
    const data = await authJson("/core/fiscal-years");
    setFiscalYears(data || []);
    if ((data || [])[0]?.id) setLdoFyId(data[0].id);
  };

  const loadPPAs = async () => {
    const data = await authJson("/budget/ppas?page=1&size=20");
    setPpas(data?.items || []);
  };

  const loadPPAPrograms = async (ppaId: number) => {
    const data = await authJson(`/budget/ppas/${ppaId}/programs`);
    setPpaPrograms(Array.isArray(data) ? data : []);
  };

  const loadLDOs = async () => {
    const data = await authJson("/budget/ldos?page=1&size=20");
    setLdos(data?.items || []);
  };

  const loadLDOGoals = async (ldoId: number) => {
    const data = await authJson(`/budget/ldos/${ldoId}/goals`);
    setLdoGoals(Array.isArray(data) ? data : []);
  };

  const loadLOAs = async () => {
    const data = await authJson("/budget/loas?page=1&size=20");
    setLoas(data?.items || []);
  };

  const loadLOAItems = async (loaId: number) => {
    const data = await authJson(`/budget/loas/${loaId}/items`);
    setLoaItems(Array.isArray(data) ? data : []);
  };

  const loadLOASummary = async (loaId: number) => {
    try {
      const data = await authJson(`/budget/loas/${loaId}/execution-summary`);
      setLoaSummary(data);
    } catch { setLoaSummary(null); }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      Promise.all([loadFiscalYears(), loadPPAs(), loadLDOs(), loadLOAs()]).catch((e) => toast(messageFrom(e), "error"));
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  const handleSelectPpa = async (id: number | "") => {
    setSelectedPpa(id);
    if (id) await loadPPAPrograms(Number(id));
    else setPpaPrograms([]);
  };

  const handleSelectLdo = async (id: number | "") => {
    setSelectedLdo(id);
    if (id) await loadLDOGoals(Number(id));
    else setLdoGoals([]);
  };

  const handleSelectLoa = async (id: number | "") => {
    setSelectedLoa(id);
    if (id) { await loadLOAItems(Number(id)); await loadLOASummary(Number(id)); }
    else { setLoaItems([]); setLoaSummary(null); }
  };

  // PPA actions
  const createPPA = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const data = await authJson("/budget/ppas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ period_start: Number(ppaStart), period_end: Number(ppaEnd), description: ppaDesc }),
      });
      toast("PPA criado.");
      await loadPPAs();
      setSelectedPpa(data.id);
      setPpaPrograms([]);
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const createProgram = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedPpa) toast("Selecione um PPA.", "error"); return;
    try {
      await authJson(`/budget/ppas/${selectedPpa}/programs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: progCode, name: progName, objective: progObjective, estimated_amount: Number(progAmount) }),
      });
      toast("Programa adicionado ao PPA.");
      await loadPPAPrograms(Number(selectedPpa));
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const approvePPA = async (id: number) => {
    try {
      await authJson(`/budget/ppas/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "aprovado" }),
      });
      toast("PPA aprovado.");
      await loadPPAs();
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  // LDO actions
  const createLDO = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const data = await authJson("/budget/ldos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fiscal_year_id: Number(ldoFyId), description: ldoDesc }),
      });
      toast("LDO criada.");
      await loadLDOs();
      setSelectedLdo(data.id);
      setLdoGoals([]);
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const createGoal = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedLdo) toast("Selecione uma LDO.", "error"); return;
    try {
      await authJson(`/budget/ldos/${selectedLdo}/goals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: goalCode, description: goalDesc, category: goalCategory }),
      });
      toast("Meta/diretriz adicionada.");
      await loadLDOGoals(Number(selectedLdo));
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const approveLDO = async (id: number) => {
    try {
      await authJson(`/budget/ldos/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "aprovado" }),
      });
      toast("LDO aprovada.");
      await loadLDOs();
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  // LOA actions
  const createLOA = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const data = await authJson("/budget/loas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fiscal_year_id: Number(loaFyId),
          ldo_id: loaLdoId ? Number(loaLdoId) : null,
          description: loaDesc,
          total_revenue: Number(loaRevenue),
        }),
      });
      toast("LOA criada.");
      await loadLOAs();
      setSelectedLoa(data.id);
      setLoaItems([]); setLoaSummary(null);
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const createItem = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedLoa) toast("Selecione uma LOA.", "error"); return;
    try {
      await authJson(`/budget/loas/${selectedLoa}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          function_code: itemFuncCode,
          subfunction_code: itemSubfuncCode,
          program_code: itemProgCode,
          action_code: itemActionCode,
          description: itemDesc,
          category: itemCategory,
          authorized_amount: Number(itemAmount),
        }),
      });
      toast("Dotação adicionada à LOA.");
      await loadLOAItems(Number(selectedLoa));
      await loadLOASummary(Number(selectedLoa));
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const approveLOA = async (id: number) => {
    try {
      await authJson(`/budget/loas/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "aprovado" }),
      });
      toast("LOA aprovada.");
      await loadLOAs();
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Planejamento Orçamentário</h1>
      <p className="muted">PPA · LDO · LOA — ciclo integrado de planejamento e execução orçamentária.</p>


      <div className="toolbar">
        <Link className="btn" href="/">Painel</Link>
        <Link className="btn" href="/compras">Compras</Link>
        <Link className="btn" href="/fase-2">Contábil</Link>
      </div>

      {/* Tabs */}
      <div className="toolbar" style={{ borderBottom: "2px solid var(--border)", paddingBottom: 0, gap: 0 }}>
        {(["ppa", "ldo", "loa"] as const).map((tab) => (
          <button
            key={tab}
            className="btn"
            style={{
              borderBottomLeftRadius: 0, borderBottomRightRadius: 0,
              borderBottom: activeTab === tab ? "3px solid var(--primary)" : "3px solid transparent",
              background: activeTab === tab ? "var(--primary-soft)" : "#fff",
              fontWeight: activeTab === tab ? 700 : 400,
            }}
            onClick={() => setActiveTab(tab)}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      {/* ─── PPA ─── */}
      {activeTab === "ppa" && (
        <div style={{ display: "grid", gap: 12 }}>
          <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))" }}>
            <section className="card">
              <h2>Criar PPA</h2>
              <form onSubmit={createPPA} className="section-stack">
                <label className="field-group">Período inicial (ano)<input type="number" value={ppaStart} onChange={(e) => setPpaStart(Number(e.target.value))} required /></label>
                <label className="field-group">Período final (ano)<input type="number" value={ppaEnd} onChange={(e) => setPpaEnd(Number(e.target.value))} required /></label>
                <label className="field-group">Descrição<input value={ppaDesc} onChange={(e) => setPpaDesc(e.target.value)} required /></label>
                <button className="btn btn-primary" type="submit">Salvar PPA</button>
              </form>
            </section>

            <section className="card">
              <h2>Adicionar programa ao PPA</h2>
              <label className="field-group" style={{ marginBottom: 8 }}>
                PPA selecionado
                <select value={selectedPpa} onChange={(e) => handleSelectPpa(e.target.value ? Number(e.target.value) : "")}>
                  <option value="">Selecione o PPA</option>
                  {ppas.map((p) => <option key={p.id} value={p.id}>{p.period_start}–{p.period_end}: {p.description}</option>)}
                </select>
              </label>
              <form onSubmit={createProgram} className="section-stack">
                <label className="field-group">Código<input value={progCode} onChange={(e) => setProgCode(e.target.value)} required /></label>
                <label className="field-group">Nome do programa<input value={progName} onChange={(e) => setProgName(e.target.value)} required /></label>
                <label className="field-group">Objetivo<input value={progObjective} onChange={(e) => setProgObjective(e.target.value)} /></label>
                <label className="field-group">Valor estimado<input type="number" value={progAmount} onChange={(e) => setProgAmount(Number(e.target.value))} /></label>
                <button className="btn btn-primary" type="submit">Adicionar programa</button>
              </form>
            </section>
          </div>

          <section className="card section-stack">
            <h2>PPAs cadastrados</h2>
            <table>
              <thead><tr><th>Período</th><th>Descrição</th><th>Status</th><th>Ações</th></tr></thead>
              <tbody>
                {ppas.length > 0 ? ppas.map((p) => (
                  <tr key={p.id}>
                    <td>{p.period_start}–{p.period_end}</td>
                    <td>{p.description}</td>
                    <td><span className={`chip ${p.status === "aprovado" ? "pago" : "empenhado"}`}>{p.status}</span></td>
                    <td className="toolbar" style={{ gap: 4 }}>
                      <button className="btn btn-inline" onClick={() => handleSelectPpa(p.id)}>Ver programas</button>
                      {p.status !== "aprovado" && <button className="btn btn-inline btn-primary" onClick={() => approvePPA(p.id)}>Aprovar</button>}
                    </td>
                  </tr>
                )) : <tr><td colSpan={4} className="empty-state">Nenhum PPA cadastrado.</td></tr>}
              </tbody>
            </table>
            {ppaPrograms.length > 0 && selectedPpa && (
              <div>
                <p className="muted" style={{ marginTop: 8 }}>Programas do PPA {selectedPpa}:</p>
                <table>
                  <thead><tr><th>Código</th><th>Nome</th><th>Objetivo</th><th>Valor estimado</th></tr></thead>
                  <tbody>
                    {ppaPrograms.map((prog) => (
                      <tr key={prog.id}>
                        <td>{prog.code}</td><td>{prog.name}</td><td>{prog.objective}</td><td>R$ {prog.estimated_amount.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}

      {/* ─── LDO ─── */}
      {activeTab === "ldo" && (
        <div style={{ display: "grid", gap: 12 }}>
          <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))" }}>
            <section className="card">
              <h2>Criar LDO</h2>
              <form onSubmit={createLDO} className="section-stack">
                <label className="field-group">
                  Exercício
                  <select value={ldoFyId} onChange={(e) => setLdoFyId(Number(e.target.value))}>
                    {fiscalYears.map((fy) => <option key={fy.id} value={fy.id}>{fy.year}</option>)}
                  </select>
                </label>
                <label className="field-group">Descrição<input value={ldoDesc} onChange={(e) => setLdoDesc(e.target.value)} required /></label>
                <button className="btn btn-primary" type="submit">Salvar LDO</button>
              </form>
            </section>

            <section className="card">
              <h2>Adicionar meta / diretriz</h2>
              <label className="field-group" style={{ marginBottom: 8 }}>
                LDO selecionada
                <select value={selectedLdo} onChange={(e) => handleSelectLdo(e.target.value ? Number(e.target.value) : "")}>
                  <option value="">Selecione a LDO</option>
                  {ldos.map((l) => <option key={l.id} value={l.id}>{l.description} ({l.status})</option>)}
                </select>
              </label>
              <form onSubmit={createGoal} className="section-stack">
                <label className="field-group">Código<input value={goalCode} onChange={(e) => setGoalCode(e.target.value)} required /></label>
                <label className="field-group">Descrição<input value={goalDesc} onChange={(e) => setGoalDesc(e.target.value)} required /></label>
                <label className="field-group">
                  Categoria
                  <select value={goalCategory} onChange={(e) => setGoalCategory(e.target.value)}>
                    <option value="meta_fiscal">Meta fiscal</option>
                    <option value="prioridade">Prioridade</option>
                    <option value="diretriz">Diretriz</option>
                  </select>
                </label>
                <button className="btn btn-primary" type="submit">Adicionar meta</button>
              </form>
            </section>
          </div>

          <section className="card section-stack">
            <h2>LDOs cadastradas</h2>
            <table>
              <thead><tr><th>Exercício ID</th><th>Descrição</th><th>Status</th><th>Ações</th></tr></thead>
              <tbody>
                {ldos.length > 0 ? ldos.map((l) => (
                  <tr key={l.id}>
                    <td>{l.fiscal_year_id}</td>
                    <td>{l.description}</td>
                    <td><span className={`chip ${l.status === "aprovado" ? "pago" : "empenhado"}`}>{l.status}</span></td>
                    <td className="toolbar" style={{ gap: 4 }}>
                      <button className="btn btn-inline" onClick={() => handleSelectLdo(l.id)}>Ver metas</button>
                      {l.status !== "aprovado" && <button className="btn btn-inline btn-primary" onClick={() => approveLDO(l.id)}>Aprovar</button>}
                    </td>
                  </tr>
                )) : <tr><td colSpan={4} className="empty-state">Nenhuma LDO cadastrada.</td></tr>}
              </tbody>
            </table>
            {ldoGoals.length > 0 && selectedLdo && (
              <div>
                <p className="muted" style={{ marginTop: 8 }}>Metas da LDO {selectedLdo}:</p>
                <table>
                  <thead><tr><th>Código</th><th>Descrição</th><th>Categoria</th></tr></thead>
                  <tbody>
                    {ldoGoals.map((g) => (
                      <tr key={g.id}><td>{g.code}</td><td>{g.description}</td><td>{g.category}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}

      {/* ─── LOA ─── */}
      {activeTab === "loa" && (
        <div style={{ display: "grid", gap: 12 }}>
          <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))" }}>
            <section className="card">
              <h2>Criar LOA</h2>
              <form onSubmit={createLOA} className="section-stack">
                <label className="field-group">
                  Exercício
                  <select value={loaFyId} onChange={(e) => setLoaFyId(Number(e.target.value))}>
                    {fiscalYears.map((fy) => <option key={fy.id} value={fy.id}>{fy.year}</option>)}
                  </select>
                </label>
                <label className="field-group">
                  LDO de referência
                  <select value={loaLdoId} onChange={(e) => setLoaLdoId(e.target.value ? Number(e.target.value) : "")}>
                    <option value="">Sem LDO vinculada</option>
                    {ldos.map((l) => <option key={l.id} value={l.id}>{l.description}</option>)}
                  </select>
                </label>
                <label className="field-group">Descrição<input value={loaDesc} onChange={(e) => setLoaDesc(e.target.value)} required /></label>
                <label className="field-group">Receita total prevista (R$)<input type="number" value={loaRevenue} onChange={(e) => setLoaRevenue(Number(e.target.value))} /></label>
                <button className="btn btn-primary" type="submit">Salvar LOA</button>
              </form>
            </section>

            <section className="card">
              <h2>Adicionar dotação (item LOA)</h2>
              <label className="field-group" style={{ marginBottom: 8 }}>
                LOA selecionada
                <select value={selectedLoa} onChange={(e) => handleSelectLoa(e.target.value ? Number(e.target.value) : "")}>
                  <option value="">Selecione a LOA</option>
                  {loas.map((l) => <option key={l.id} value={l.id}>{l.description} ({l.status})</option>)}
                </select>
              </label>
              <form onSubmit={createItem} className="section-stack">
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <label className="field-group">Função<input value={itemFuncCode} onChange={(e) => setItemFuncCode(e.target.value)} placeholder="10" required /></label>
                  <label className="field-group">Subfunção<input value={itemSubfuncCode} onChange={(e) => setItemSubfuncCode(e.target.value)} placeholder="301" required /></label>
                  <label className="field-group">Programa<input value={itemProgCode} onChange={(e) => setItemProgCode(e.target.value)} placeholder="0015" required /></label>
                  <label className="field-group">Ação<input value={itemActionCode} onChange={(e) => setItemActionCode(e.target.value)} placeholder="2001" required /></label>
                </div>
                <label className="field-group">Descrição<input value={itemDesc} onChange={(e) => setItemDesc(e.target.value)} required /></label>
                <label className="field-group">
                  Categoria
                  <select value={itemCategory} onChange={(e) => setItemCategory(e.target.value)}>
                    <option value="despesa">Despesa</option>
                    <option value="receita">Receita</option>
                  </select>
                </label>
                <label className="field-group">Valor autorizado (R$)<input type="number" value={itemAmount} onChange={(e) => setItemAmount(Number(e.target.value))} required /></label>
                <button className="btn btn-primary" type="submit">Adicionar dotação</button>
              </form>
            </section>
          </div>

          {/* Resumo de execução */}
          {loaSummary && (
            <div className="card" style={{ borderLeft: "4px solid var(--primary)", background: "var(--primary-soft)" }}>
              <h2>Resumo de execução — {loaSummary.description}</h2>
              <div className="kpi-grid" style={{ marginTop: 8 }}>
                <div>
                  <p className="muted">Autorizado</p>
                  <p className="kpi-value">R$ {loaSummary.total_authorized.toFixed(2)}</p>
                </div>
                <div>
                  <p className="muted">Executado</p>
                  <p className="kpi-value">R$ {loaSummary.total_executed.toFixed(2)}</p>
                </div>
                <div>
                  <p className="muted">Taxa de execução</p>
                  <p className="kpi-value">{loaSummary.execution_rate}%</p>
                </div>
              </div>
              {loaSummary.by_function.length > 0 && (
                <table style={{ marginTop: 12 }}>
                  <thead><tr><th>Função</th><th>Autorizado</th><th>Executado</th></tr></thead>
                  <tbody>
                    {loaSummary.by_function.map((f) => (
                      <tr key={f.function_code}>
                        <td>{f.function_code}</td>
                        <td>R$ {f.authorized.toFixed(2)}</td>
                        <td>R$ {f.executed.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          <section className="card section-stack">
            <h2>LOAs cadastradas</h2>
            <table>
              <thead><tr><th>Descrição</th><th>Receita prevista</th><th>Despesa autorizada</th><th>Status</th><th>Ações</th></tr></thead>
              <tbody>
                {loas.length > 0 ? loas.map((l) => (
                  <tr key={l.id}>
                    <td>{l.description}</td>
                    <td>R$ {l.total_revenue.toFixed(2)}</td>
                    <td>R$ {l.total_expenditure.toFixed(2)}</td>
                    <td><span className={`chip ${l.status === "aprovado" ? "pago" : "empenhado"}`}>{l.status}</span></td>
                    <td className="toolbar" style={{ gap: 4 }}>
                      <button className="btn btn-inline" onClick={() => handleSelectLoa(l.id)}>Ver dotações</button>
                      {l.status !== "aprovado" && <button className="btn btn-inline btn-primary" onClick={() => approveLOA(l.id)}>Aprovar</button>}
                    </td>
                  </tr>
                )) : <tr><td colSpan={5} className="empty-state">Nenhuma LOA cadastrada.</td></tr>}
              </tbody>
            </table>

            {loaItems.length > 0 && selectedLoa && (
              <div>
                <p className="muted" style={{ marginTop: 8 }}>Dotações da LOA {selectedLoa}:</p>
                <table>
                  <thead><tr><th>Func.</th><th>Subfunc.</th><th>Programa</th><th>Ação</th><th>Descrição</th><th>Autorizado</th><th>Executado</th></tr></thead>
                  <tbody>
                    {loaItems.map((item) => (
                      <tr key={item.id}>
                        <td>{item.function_code}</td>
                        <td>{item.subfunction_code}</td>
                        <td>{item.program_code}</td>
                        <td>{item.action_code}</td>
                        <td>{item.description}</td>
                        <td>R$ {item.authorized_amount.toFixed(2)}</td>
                        <td>R$ {item.executed_amount.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
