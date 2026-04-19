"use client";

import { FormEvent, useEffect, useState } from "react";

import { authDownload, authJson, readCookie } from "@/lib/auth";

type Department = { id: number; name: string };
type Employee = { id: number; name: string };
type Asset = {
  id: number;
  tag: string;
  description: string;
  classification: string;
  location: string;
  department_id: number;
  responsible_employee_id: number | null;
  value: number;
  status: string;
};
type Movement = { id: number; asset_id: number; from_department_id: number | null; to_department_id: number | null; movement_type: string; moved_at: string };
type ListResponse<T> = { total: number; page: number; size: number; items: T[] };
type Inventory = { total: number; ativos: number };

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "Falha na operação";
}

export default function PatrimonioPage() {
  const [role] = useState(() => readCookie("role"));
  const [statusMsg, setStatusMsg] = useState("");

  const [departments, setDepartments] = useState<Department[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [inventory, setInventory] = useState<Inventory | null>(null);

  const [assets, setAssets] = useState<ListResponse<Asset> | null>(null);
  const [movements, setMovements] = useState<ListResponse<Movement> | null>(null);
  const [report, setReport] = useState<Record<string, string[]> | null>(null);

  const [tag, setTag] = useState("PAT-UI-001");
  const [description, setDescription] = useState("Bem criado pela interface de patrimônio");
  const [classification, setClassification] = useState("Informática");
  const [location, setLocation] = useState("Sala 201");
  const [departmentId, setDepartmentId] = useState(1);
  const [responsibleEmployeeId, setResponsibleEmployeeId] = useState<number | "">("");
  const [value, setValue] = useState(3800);

  const [assetSearch, setAssetSearch] = useState("");
  const [assetClassification, setAssetClassification] = useState("");
  const [assetStatus, setAssetStatus] = useState("");
  const [assetDepartmentFilter, setAssetDepartmentFilter] = useState<number | "">("");
  const [assetPage, setAssetPage] = useState(1);

  const [transferAssetId, setTransferAssetId] = useState<number | "">("");
  const [transferDepartmentId, setTransferDepartmentId] = useState<number>(1);
  const [transferLocation, setTransferLocation] = useState("Sala 305");
  const [transferResponsibleEmployeeId, setTransferResponsibleEmployeeId] = useState<number | "">("");

  const [movementAssetId, setMovementAssetId] = useState<number | "">("");
  const [movementPage, setMovementPage] = useState(1);
  const [reportDepartmentId, setReportDepartmentId] = useState<number | "">("");

  const loadCoreData = async () => {
    const [deps, emps, inv] = await Promise.all([
      authJson("/core/departments"),
      authJson("/hr/employees?page=1&size=200"),
      authJson("/patrimony/inventory"),
    ]);
    setDepartments(deps || []);
    setEmployees(emps || []);
    setInventory(inv);
    if (deps?.[0]?.id) {
      setDepartmentId((prev) => prev || deps[0].id);
      setTransferDepartmentId((prev) => prev || deps[0].id);
    }
  };

  const loadAssets = async () => {
    const qs = new URLSearchParams({ page: String(assetPage), size: "10" });
    if (assetSearch) qs.set("search", assetSearch);
    if (assetClassification) qs.set("classification", assetClassification);
    if (assetStatus) qs.set("status", assetStatus);
    if (assetDepartmentFilter) qs.set("department_id", String(assetDepartmentFilter));
    const data = await authJson(`/patrimony/assets?${qs.toString()}`);
    setAssets(data);
    if (data?.items?.[0]?.id) {
      setTransferAssetId((prev) => prev || data.items[0].id);
    }
  };

  const loadMovements = async () => {
    const qs = new URLSearchParams({ page: String(movementPage), size: "10" });
    if (movementAssetId) qs.set("asset_id", String(movementAssetId));
    const data = await authJson(`/patrimony/movements?${qs.toString()}`);
    setMovements(data);
  };

  const loadReport = async () => {
    const query = reportDepartmentId ? `?department_id=${reportDepartmentId}` : "";
    const data = await authJson(`/patrimony/reports/by-department${query}`);
    setReport(data);
  };

  const refreshAll = async () => {
    try {
      await Promise.all([loadCoreData(), loadAssets(), loadMovements(), loadReport()]);
    } catch (error) {
      setStatusMsg(error instanceof Error ? error.message : "Falha ao carregar módulo de patrimônio");
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      refreshAll();
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadAssets().catch((e) => setStatusMsg(messageFrom(e)));
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetPage]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadMovements().catch((e) => setStatusMsg(messageFrom(e)));
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [movementPage]);

  const createAsset = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await authJson("/patrimony/assets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tag,
          description,
          classification,
          location,
          department_id: Number(departmentId),
          responsible_employee_id: responsibleEmployeeId === "" ? null : Number(responsibleEmployeeId),
          value: Number(value),
          status: "ativo",
        }),
      });
      setStatusMsg("Bem cadastrado com sucesso.");
      await Promise.all([loadAssets(), loadReport(), loadCoreData()]);
    } catch (error) {
      setStatusMsg(error instanceof Error ? error.message : "Erro ao cadastrar bem");
    }
  };

  const transferAsset = async (e: FormEvent) => {
    e.preventDefault();
    if (!transferAssetId) return setStatusMsg("Selecione um bem para transferência.");
    try {
      await authJson(`/patrimony/assets/${transferAssetId}/transfer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to_department_id: Number(transferDepartmentId),
          new_location: transferLocation,
          new_responsible_employee_id: transferResponsibleEmployeeId === "" ? null : Number(transferResponsibleEmployeeId),
        }),
      });
      setStatusMsg("Transferência registrada.");
      await Promise.all([loadAssets(), loadMovements(), loadReport()]);
    } catch (error) {
      setStatusMsg(error instanceof Error ? error.message : "Erro ao transferir bem");
    }
  };

  const writeOffAsset = async (assetId: number) => {
    try {
      const data = await authJson(`/patrimony/assets/${assetId}/write-off`, { method: "POST" });
      setStatusMsg(data.message || "Bem baixado.");
      await Promise.all([loadAssets(), loadMovements(), loadReport(), loadCoreData()]);
    } catch (error) {
      setStatusMsg(error instanceof Error ? error.message : "Erro ao baixar bem");
    }
  };

  const exportAssetsCsv = async () => {
    const qs = new URLSearchParams();
    if (assetSearch) qs.set("search", assetSearch);
    if (assetClassification) qs.set("classification", assetClassification);
    if (assetStatus) qs.set("status", assetStatus);
    if (assetDepartmentFilter) qs.set("department_id", String(assetDepartmentFilter));
    qs.set("export", "csv");
    authDownload(`/patrimony/assets?${qs.toString()}`, "bens-patrimonio.csv").catch((e) => setStatusMsg(messageFrom(e)));
  };

  return (
    <main className="module-page">
      <h1>Módulo de Patrimônio</h1>
      <p className="muted">Perfil atual: <strong suppressHydrationWarning>{role || "não identificado"}</strong></p>
      {statusMsg && <p className={statusMsg.toLowerCase().includes("erro") || statusMsg.toLowerCase().includes("falha") ? "notice error" : "notice"}><strong>{statusMsg}</strong></p>}

      <section className="kpi-grid">
        <div className="card">
          <h2>Resumo</h2>
          <p className="kpi-value">{inventory?.total ?? 0}</p>
          <p className="muted">Total de bens cadastrados</p>
          <p>Bens ativos: <strong>{inventory?.ativos ?? 0}</strong></p>
        </div>
        <div className="card">
          <h2>Navegação rápida</h2>
          <div className="toolbar">
            <a className="btn" href="/rh">Ir para RH</a>
            <a className="btn" href="/public">Ver transparência</a>
          </div>
          <p className="muted">Busca rápida de demo: descrição contém <strong>Demo Integrado</strong> ou tombamento <strong>PAT-DEMO-001</strong>.</p>
        </div>
      </section>

      <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))" }}>
        <section className="card">
          <h2>1) Cadastrar bem</h2>
          <form onSubmit={createAsset} className="section-stack">
            <label className="field-group">Tombamento<input value={tag} onChange={(e) => setTag(e.target.value)} placeholder="Tombamento" required /></label>
            <label className="field-group">Descrição<input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Descrição" required /></label>
            <label className="field-group">Classificação<input value={classification} onChange={(e) => setClassification(e.target.value)} placeholder="Classificação" required /></label>
            <label className="field-group">Localização<input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Localização" required /></label>
            <label className="field-group">Departamento<select value={departmentId} onChange={(e) => setDepartmentId(Number(e.target.value))}>
              {departments.map((dep) => <option key={dep.id} value={dep.id}>{dep.name}</option>)}
            </select></label>
            <label className="field-group">Responsável<select value={responsibleEmployeeId} onChange={(e) => setResponsibleEmployeeId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">Sem responsável</option>
              {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.name}</option>)}
            </select></label>
            <label className="field-group">Valor<input type="number" value={value} onChange={(e) => setValue(Number(e.target.value))} placeholder="Valor" required /></label>
            <button className="btn btn-primary" type="submit">Salvar bem</button>
          </form>
        </section>

        <section className="card">
          <h2>2) Transferir bem</h2>
          <form onSubmit={transferAsset} className="section-stack">
            <label className="field-group">Bem<select value={transferAssetId} onChange={(e) => setTransferAssetId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">Selecione o bem</option>
              {(assets?.items || []).map((item) => <option key={item.id} value={item.id}>{item.tag} - {item.description}</option>)}
            </select></label>
            <label className="field-group">Novo departamento<select value={transferDepartmentId} onChange={(e) => setTransferDepartmentId(Number(e.target.value))}>
              {departments.map((dep) => <option key={dep.id} value={dep.id}>{dep.name}</option>)}
            </select></label>
            <label className="field-group">Nova localização<input value={transferLocation} onChange={(e) => setTransferLocation(e.target.value)} placeholder="Nova localização" /></label>
            <label className="field-group">Novo responsável<select value={transferResponsibleEmployeeId} onChange={(e) => setTransferResponsibleEmployeeId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">Sem responsável</option>
              {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.name}</option>)}
            </select></label>
            <button className="btn btn-primary" type="submit">Confirmar transferência</button>
          </form>
        </section>
      </div>

      <section className="card">
        <h2>Bens patrimoniais (filtros, paginação e CSV)</h2>
        <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", marginBottom: 8 }}>
          <input value={assetSearch} onChange={(e) => setAssetSearch(e.target.value)} placeholder="Buscar descrição" />
          <input value={assetClassification} onChange={(e) => setAssetClassification(e.target.value)} placeholder="Classificação" />
          <select value={assetStatus} onChange={(e) => setAssetStatus(e.target.value)}>
            <option value="">Todos os status</option>
            <option value="ativo">Ativo</option>
            <option value="baixado">Baixado</option>
          </select>
          <select value={assetDepartmentFilter} onChange={(e) => setAssetDepartmentFilter(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Todos os departamentos</option>
            {departments.map((dep) => <option key={dep.id} value={dep.id}>{dep.name}</option>)}
          </select>
          <button className="btn" onClick={() => { setAssetPage(1); loadAssets().catch((e) => setStatusMsg(messageFrom(e))); }}>Aplicar filtros</button>
          <button className="btn" onClick={exportAssetsCsv}>Exportar CSV</button>
        </div>
        <table>
          <thead>
            <tr><th>Tombamento</th><th>Descrição</th><th>Classificação</th><th>Departamento</th><th>Status</th><th>Ações</th></tr>
          </thead>
          <tbody>
            {(assets?.items || []).length > 0 ? (
              (assets?.items || []).map((asset) => (
                <tr key={asset.id}>
                  <td>{asset.tag}</td><td>{asset.description}</td><td>{asset.classification}</td><td>{asset.department_id}</td><td><span className={`chip ${asset.status}`}>{asset.status}</span></td>
                  <td>{asset.status !== "baixado" ? <button className="btn" onClick={() => writeOffAsset(asset.id)}>Baixar bem</button> : "-"}</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={6} className="empty-state">Nenhum bem encontrado para os filtros selecionados.</td></tr>
            )}
          </tbody>
        </table>
        <div className="pagination">
          <button className="btn" disabled={(assets?.page || 1) <= 1} onClick={() => setAssetPage((p) => p - 1)}>Anterior</button>
          <span> Página {assets?.page || 1} </span>
          <button className="btn" disabled={(assets?.items?.length || 0) < 10} onClick={() => setAssetPage((p) => p + 1)}>Próxima</button>
        </div>
      </section>

      <section className="card">
        <h2>Histórico de movimentações</h2>
        <div className="toolbar">
          <select value={movementAssetId} onChange={(e) => setMovementAssetId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Todos os bens</option>
            {(assets?.items || []).map((item) => <option key={item.id} value={item.id}>{item.tag}</option>)}
          </select>
          <button className="btn" onClick={() => { setMovementPage(1); loadMovements().catch((e) => setStatusMsg(messageFrom(e))); }}>Filtrar</button>
        </div>
        <table>
          <thead><tr><th>ID</th><th>Bem</th><th>De</th><th>Para</th><th>Tipo</th><th>Data</th></tr></thead>
          <tbody>
            {(movements?.items || []).length > 0 ? (
              (movements?.items || []).map((m) => (
                <tr key={m.id}>
                  <td>{m.id}</td><td>{m.asset_id}</td><td>{m.from_department_id ?? "-"}</td><td>{m.to_department_id ?? "-"}</td><td><span className={`chip ${m.movement_type}`}>{m.movement_type}</span></td><td>{new Date(m.moved_at).toLocaleString("pt-BR")}</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={6} className="empty-state">Sem movimentações para os filtros informados.</td></tr>
            )}
          </tbody>
        </table>
        <div className="pagination">
          <button className="btn" disabled={(movements?.page || 1) <= 1} onClick={() => setMovementPage((p) => p - 1)}>Anterior</button>
          <span> Página {movements?.page || 1} </span>
          <button className="btn" disabled={(movements?.items?.length || 0) < 10} onClick={() => setMovementPage((p) => p + 1)}>Próxima</button>
        </div>
      </section>

      <section className="card">
        <h2>Relatório por departamento</h2>
        <div className="toolbar">
          <select value={reportDepartmentId} onChange={(e) => setReportDepartmentId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Todos os departamentos</option>
            {departments.map((dep) => <option key={dep.id} value={dep.id}>{dep.name}</option>)}
          </select>
          <button className="btn" onClick={() => loadReport().catch((e) => setStatusMsg(messageFrom(e)))}>Gerar relatório</button>
        </div>
        <ul>
          {Object.entries(report || {}).length > 0 ? (
            Object.entries(report || {}).map(([dep, tags]) => (
              <li key={dep}>Departamento {dep}: {tags.length} bens ({tags.join(", ")})</li>
            ))
          ) : (
            <li className="empty-state">Nenhum item para o relatório solicitado.</li>
          )}
        </ul>
      </section>
    </main>
  );
}
