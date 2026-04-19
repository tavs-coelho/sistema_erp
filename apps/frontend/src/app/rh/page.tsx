"use client";

import { FormEvent, useEffect, useState } from "react";

import { authDownload, authJson, readCookie } from "@/lib/auth";

type Department = { id: number; name: string };
type Employee = { id: number; name: string; cpf: string; job_title: string; employment_type: string; base_salary: number; department_id: number };
type PayrollEvent = { id: number; employee_id: number; month: string; kind: string; description: string; value: number };
type Payslip = { id: number; employee_id: number; month: string; gross_amount: number; deductions: number; net_amount: number };
type ListResponse<T> = { total: number; page: number; size: number; items: T[] };

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "Falha na operação";
}

export default function RhPage() {
  const [role] = useState(() => readCookie("role"));
  const [status, setStatus] = useState("");
  const [departments, setDepartments] = useState<Department[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [events, setEvents] = useState<ListResponse<PayrollEvent> | null>(null);
  const [payslips, setPayslips] = useState<ListResponse<Payslip> | null>(null);

  const [employeeName, setEmployeeName] = useState("Servidor RH Demo");
  const [employeeCpf, setEmployeeCpf] = useState("999.888.777-66");
  const [employeeJobTitle, setEmployeeJobTitle] = useState("Analista Administrativo");
  const [employeeType, setEmployeeType] = useState("Efetivo");
  const [employeeSalary, setEmployeeSalary] = useState(4200);
  const [employeeDepartment, setEmployeeDepartment] = useState(1);

  const [eventEmployeeId, setEventEmployeeId] = useState(1);
  const [eventMonth, setEventMonth] = useState("2026-04");
  const [eventKind, setEventKind] = useState("provento");
  const [eventDescription, setEventDescription] = useState("Gratificação");
  const [eventValue, setEventValue] = useState(350);

  const [eventFilterMonth, setEventFilterMonth] = useState("2026-04");
  const [eventPage, setEventPage] = useState(1);
  const [payslipFilterMonth, setPayslipFilterMonth] = useState("2026-04");
  const [payslipPage, setPayslipPage] = useState(1);
  const [employeeSearch, setEmployeeSearch] = useState("");
  const [employeePage, setEmployeePage] = useState(1);

  const loadDepartments = async () => {
    const data = await authJson("/core/departments");
    setDepartments(data || []);
    if (data?.[0]?.id) setEmployeeDepartment((prev) => prev || data[0].id);
  };

  const loadEmployees = async () => {
    const qs = new URLSearchParams({ page: String(employeePage), size: "10", search: employeeSearch });
    const data = await authJson(`/hr/employees?${qs.toString()}`);
    setEmployees(data || []);
    if ((data || [])[0]?.id) setEventEmployeeId((prev) => prev || data[0].id);
  };

  const loadEvents = async () => {
    const qs = new URLSearchParams({ page: String(eventPage), size: "10" });
    if (eventFilterMonth) qs.set("month", eventFilterMonth);
    const data = await authJson(`/hr/payroll-events?${qs.toString()}`);
    setEvents(data);
  };

  const loadPayslips = async () => {
    const qs = new URLSearchParams({ page: String(payslipPage), size: "10" });
    if (payslipFilterMonth) qs.set("month", payslipFilterMonth);
    const data = await authJson(`/hr/payslips?${qs.toString()}`);
    setPayslips(data);
  };

  const refreshAll = async () => {
    try {
      await Promise.all([loadDepartments(), loadEmployees(), loadEvents(), loadPayslips()]);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Falha ao carregar dados de RH");
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
      loadEmployees().catch((e) => setStatus(messageFrom(e)));
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employeePage]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadEvents().catch((e) => setStatus(messageFrom(e)));
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventPage]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadPayslips().catch((e) => setStatus(messageFrom(e)));
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [payslipPage]);

  const createEmployee = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await authJson("/hr/employees", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: employeeName,
          cpf: employeeCpf,
          job_title: employeeJobTitle,
          employment_type: employeeType,
          base_salary: Number(employeeSalary),
          department_id: Number(employeeDepartment),
        }),
      });
      setStatus("Servidor cadastrado com sucesso.");
      await loadEmployees();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Erro ao cadastrar servidor");
    }
  };

  const createEvent = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await authJson("/hr/payroll-events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          employee_id: Number(eventEmployeeId),
          month: eventMonth,
          kind: eventKind,
          description: eventDescription,
          value: Number(eventValue),
        }),
      });
      setStatus("Evento de folha criado.");
      await loadEvents();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Erro ao criar evento");
    }
  };

  const calculatePayroll = async () => {
    try {
      const data = await authJson("/hr/payroll/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ month: eventMonth }),
      });
      setStatus(`${data.message}. Holerites criados: ${data.created}`);
      setPayslipFilterMonth(eventMonth);
      await loadPayslips();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Erro ao calcular folha");
    }
  };

  return (
    <main className="module-page">
      <h1>Módulo RH e Folha</h1>
      <p className="muted">Perfil atual: <strong suppressHydrationWarning>{role || "não identificado"}</strong> | <a href="/portal-servidor">Portal do servidor</a></p>
      {status && <p className={status.toLowerCase().includes("erro") || status.toLowerCase().includes("falha") ? "notice error" : "notice"}><strong>{status}</strong></p>}
      <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
        <section className="card">
          <h2>1) Cadastrar servidor</h2>
          <form onSubmit={createEmployee} style={{ display: "grid", gap: 8 }}>
            <label className="field-group">Nome completo<input value={employeeName} onChange={(e) => setEmployeeName(e.target.value)} placeholder="Nome completo" required /></label>
            <label className="field-group">CPF<input value={employeeCpf} onChange={(e) => setEmployeeCpf(e.target.value)} placeholder="CPF" required /></label>
            <label className="field-group">Cargo<input value={employeeJobTitle} onChange={(e) => setEmployeeJobTitle(e.target.value)} placeholder="Cargo" required /></label>
            <label className="field-group">Tipo de vínculo<input value={employeeType} onChange={(e) => setEmployeeType(e.target.value)} placeholder="Tipo vínculo" required /></label>
            <label className="field-group">Salário base<input type="number" value={employeeSalary} onChange={(e) => setEmployeeSalary(Number(e.target.value))} placeholder="Salário base" required /></label>
            <label className="field-group">Departamento<select value={employeeDepartment} onChange={(e) => setEmployeeDepartment(Number(e.target.value))}>
              {departments.map((dep) => <option key={dep.id} value={dep.id}>{dep.name}</option>)}
            </select></label>
            <button type="submit">Salvar servidor</button>
          </form>
        </section>

        <section className="card">
          <h2>2) Criar evento de folha</h2>
          <form onSubmit={createEvent} style={{ display: "grid", gap: 8 }}>
            <label className="field-group">Servidor<select value={eventEmployeeId} onChange={(e) => setEventEmployeeId(Number(e.target.value))}>
              {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.name}</option>)}
            </select></label>
            <label className="field-group">Mês de referência<input value={eventMonth} onChange={(e) => setEventMonth(e.target.value)} placeholder="Mês (YYYY-MM)" required /></label>
            <label className="field-group">Tipo do evento<select value={eventKind} onChange={(e) => setEventKind(e.target.value)}>
              <option value="provento">Provento</option>
              <option value="desconto">Desconto</option>
            </select></label>
            <label className="field-group">Descrição<input value={eventDescription} onChange={(e) => setEventDescription(e.target.value)} placeholder="Descrição" required /></label>
            <label className="field-group">Valor<input type="number" value={eventValue} onChange={(e) => setEventValue(Number(e.target.value))} placeholder="Valor" required /></label>
            <button type="submit">Salvar evento</button>
          </form>
          <button style={{ marginTop: 8 }} onClick={calculatePayroll}>3) Calcular folha mensal</button>
        </section>
      </div>

      <section className="card">
        <h2>Servidores (busca e paginação)</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input
            value={employeeSearch}
            onChange={(e) => setEmployeeSearch(e.target.value)}
            placeholder="Buscar por nome"
          />
          <button onClick={() => { setEmployeePage(1); loadEmployees().catch((e) => setStatus(messageFrom(e))); }}>Buscar</button>
        </div>
        <table border={1} cellPadding={6}>
          <thead><tr><th>Nome</th><th>CPF</th><th>Cargo</th><th>Salário</th></tr></thead>
          <tbody>
            {employees.length > 0 ? (
              employees.map((emp) => (
                <tr key={emp.id}><td>{emp.name}</td><td>{emp.cpf}</td><td>{emp.job_title}</td><td>R$ {emp.base_salary.toFixed(2)}</td></tr>
              ))
            ) : (
              <tr><td colSpan={4} className="empty-state">Nenhum servidor encontrado para os filtros informados.</td></tr>
            )}
          </tbody>
        </table>
        <button disabled={employeePage <= 1} onClick={() => setEmployeePage((p) => p - 1)}>Anterior</button>
        <span> Página {employeePage} </span>
        <button disabled={employees.length < 10} onClick={() => setEmployeePage((p) => p + 1)}>Próxima</button>
      </section>

      <section className="card">
        <h2>Eventos de folha (filtro e paginação)</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input value={eventFilterMonth} onChange={(e) => setEventFilterMonth(e.target.value)} placeholder="Mês (YYYY-MM)" />
          <button onClick={() => { setEventPage(1); loadEvents().catch((e) => setStatus(messageFrom(e))); }}>Filtrar</button>
        </div>
        <table border={1} cellPadding={6}>
          <thead><tr><th>ID</th><th>Servidor</th><th>Mês</th><th>Tipo</th><th>Descrição</th><th>Valor</th></tr></thead>
          <tbody>
            {(events?.items || []).length > 0 ? (
              (events?.items || []).map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td><td>{row.employee_id}</td><td>{row.month}</td><td>{row.kind}</td><td>{row.description}</td><td>R$ {row.value.toFixed(2)}</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={6} className="empty-state">Sem eventos de folha para o mês informado.</td></tr>
            )}
          </tbody>
        </table>
        <button disabled={(events?.page || 1) <= 1} onClick={() => setEventPage((p) => p - 1)}>Anterior</button>
        <span> Página {events?.page || 1} </span>
        <button disabled={(events?.items?.length || 0) < 10} onClick={() => setEventPage((p) => p + 1)}>Próxima</button>
      </section>

      <section className="card">
        <h2>Resultados de folha (holerites gerados)</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input value={payslipFilterMonth} onChange={(e) => setPayslipFilterMonth(e.target.value)} placeholder="Mês (YYYY-MM)" />
          <button onClick={() => { setPayslipPage(1); loadPayslips().catch((e) => setStatus(messageFrom(e))); }}>Filtrar</button>
        </div>
        <table border={1} cellPadding={6}>
          <thead><tr><th>ID</th><th>Servidor</th><th>Mês</th><th>Bruto</th><th>Descontos</th><th>Líquido</th><th>Ação</th></tr></thead>
          <tbody>
            {(payslips?.items || []).length > 0 ? (
              (payslips?.items || []).map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td><td>{row.employee_id}</td><td>{row.month}</td>
                  <td>R$ {row.gross_amount.toFixed(2)}</td><td>R$ {row.deductions.toFixed(2)}</td><td>R$ {row.net_amount.toFixed(2)}</td>
                  <td><button onClick={() => authDownload(`/hr/payslips/${row.id}/pdf`, `holerite-${row.id}.pdf`).catch((e) => setStatus(messageFrom(e)))}>Baixar PDF</button></td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={7} className="empty-state">Nenhum holerite encontrado para o período selecionado.</td></tr>
            )}
          </tbody>
        </table>
        <button disabled={(payslips?.page || 1) <= 1} onClick={() => setPayslipPage((p) => p - 1)}>Anterior</button>
        <span> Página {payslips?.page || 1} </span>
        <button disabled={(payslips?.items?.length || 0) < 10} onClick={() => setPayslipPage((p) => p + 1)}>Próxima</button>
      </section>
    </main>
  );
}
