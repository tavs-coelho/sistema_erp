"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { authJson } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";

type Task = { id: number; protocol_id: number; title: string; priority: string; status: string; due_date: string | null; assigned_user_id: number | null };
type User = { id: number; full_name: string };
type Protocol = { id: number; numero: string; assunto: string };

export default function TasksPage() {
  const { toast } = useToast();
  const [items, setItems] = useState<Task[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [protocolId, setProtocolId] = useState("");
  const [assignee, setAssignee] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("normal");
  const [due, setDue] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
      const result = await authJson(`/nucleo/tarefas${query}`);
      setItems(result as Task[]);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao consultar tarefas", "error");
    }
  }, [toast, statusFilter]);

  useEffect(() => {
    const task = setTimeout(() => {
      void load();
      void authJson("/nucleo/tarefas/usuarios").then(setUsers).catch(() => setUsers([]));
      void authJson("/protocolo/protocolos?size=100").then(data => setProtocols(data.items || []))
        .catch(() => setProtocols([]));
    }, 0);
    return () => clearTimeout(task);
  }, [load]);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      await authJson("/nucleo/tarefas", { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          protocol_id: Number(protocolId), title, description, priority,
          assigned_user_id: assignee ? Number(assignee) : null, due_date: due || null,
        }),
      });
      setTitle(""); setDescription(""); setDue("");
      toast("Tarefa registrada", "success");
      await load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao registrar tarefa", "error");
    } finally { setBusy(false); }
  };

  const advance = async (id: number, status: string) => {
    if (busy) return;
    setBusy(true);
    try {
      await authJson(`/nucleo/tarefas/${id}/status`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      toast("Situação atualizada", "success");
      await load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Transição não autorizada", "error");
    } finally { setBusy(false); }
  };

  return <main className="module-page section-stack" style={{ padding: 24 }}>
    <h1>Tarefas e tramitação</h1>
    <p className="muted">Crie tarefas vinculadas a processos, distribua responsabilidades e acompanhe prazos e conclusão.</p>
    <section className="card section-stack">
      <h2>Nova tarefa</h2>
      <form className="section-stack" onSubmit={(event) => { void create(event); }}>
        <label className="field-group">Protocolo
          <select value={protocolId} required onChange={e => setProtocolId(e.target.value)}>
            <option value="">Selecione</option>
            {protocols.map(p => <option key={p.id} value={p.id}>{p.numero} — {p.assunto}</option>)}
          </select>
        </label>
        <label className="field-group">Título
          <input required value={title} onChange={e => setTitle(e.target.value)} />
        </label>
        <label className="field-group">Descrição
          <textarea value={description} onChange={e => setDescription(e.target.value)} />
        </label>
        <label className="field-group">Responsável
          <select value={assignee} onChange={e => setAssignee(e.target.value)}>
            <option value="">Sem responsável</option>
            {users.map(u => <option key={u.id} value={u.id}>{u.full_name}</option>)}
          </select>
        </label>
        <label className="field-group">Prioridade
          <select value={priority} onChange={e => setPriority(e.target.value)}>
            <option value="normal">Normal</option>
            <option value="alta">Alta</option>
            <option value="urgente">Urgente</option>
          </select>
        </label>
        <label className="field-group">Prazo
          <input type="date" value={due} onChange={e => setDue(e.target.value)} />
        </label>
        <Button type="submit" variant="primary" disabled={busy}>Criar tarefa</Button>
      </form>
    </section>
    <section className="card section-stack">
      <h2>Acompanhamento</h2>
      <label className="field-group">Situação
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">Todas</option>
          <option value="aberta">Aberta</option>
          <option value="em_andamento">Em andamento</option>
          <option value="concluida">Concluída</option>
          <option value="cancelada">Cancelada</option>
        </select>
      </label>
      {items.length === 0 ? <p>Não há tarefas para o filtro escolhido.</p> : (
        <table><thead><tr><th>Protocolo</th><th>Tarefa</th><th>Prioridade</th><th>Prazo</th><th>Status</th><th>Ações</th></tr></thead>
          <tbody>{items.map(item => <tr key={item.id}>
            <td>{item.protocol_id}</td><td>{item.title}</td><td>{item.priority}</td>
            <td>{item.due_date || "—"}</td><td>{item.status}</td>
            <td>
              {item.status === "aberta" && <Button type="button" disabled={busy} onClick={() => { void advance(item.id, "em_andamento"); }}>Iniciar</Button>}
              {["aberta", "em_andamento"].includes(item.status) && <>
                <Button type="button" disabled={busy} onClick={() => { void advance(item.id, "concluida"); }}>Concluir</Button>
                <Button type="button" disabled={busy} onClick={() => { void advance(item.id, "cancelada"); }}>Cancelar</Button>
              </>}
            </td>
          </tr>)}</tbody>
        </table>
      )}
    </section>
  </main>;
}
