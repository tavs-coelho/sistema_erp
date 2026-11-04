"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { authJson } from "@/lib/auth";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";

type User = { id: number; username: string; full_name: string; role: string };
type Unit = { id: number; code: string; name: string };
type Assignment = { id: number; user_id: number; unit_id: number; active: boolean };

export default function AssignmentsPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [userId, setUserId] = useState("");
  const [unitId, setUnitId] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      const [people, places, memberships] = await Promise.all([
        authJson("/nucleo/lotacoes/usuarios"), authJson("/nucleo/unidades"),
        authJson("/nucleo/lotacoes"),
      ]);
      setUsers(people);
      setUnits(places);
      setAssignments(memberships);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao consultar lotações", "error");
    }
  }, [toast]);
  useEffect(() => {
    const task = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(task);
  }, [load]);
  const assign = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      await authJson("/nucleo/lotacoes", { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: Number(userId), unit_id: Number(unitId) }) });
      toast("Lotação registrada", "success");
      await load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao registrar lotação", "error");
    } finally { setBusy(false); }
  };
  const revoke = async (id: number) => {
    if (busy) return;
    setBusy(true);
    try {
      await authJson(`/nucleo/lotacoes/${id}`, { method: "DELETE" });
      toast("Lotação encerrada", "success");
      await load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao encerrar lotação", "error");
    } finally { setBusy(false); }
  };
  const userName = (id: number) => users.find(u => u.id === id)?.full_name || String(id);
  const unitName = (id: number) => units.find(u => u.id === id)?.name || String(id);
  return <main className="module-page section-stack" style={{ padding: 24 }}>
    <h1>Lotação de usuários</h1>
    <p className="muted">Vincule usuários às unidades da mesma entidade. Isso registra lotação e não altera o papel global de acesso.</p>
    <section className="card section-stack">
      <h2>Nova lotação</h2>
      <form className="section-stack" onSubmit={(e) => { void assign(e); }}>
        <label className="field-group">Usuário
          <select value={userId} onChange={e => setUserId(e.target.value)} required>
            <option value="">Selecione</option>
            {users.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>)}
          </select>
        </label>
        <label className="field-group">Unidade
          <select value={unitId} onChange={e => setUnitId(e.target.value)} required>
            <option value="">Selecione</option>
            {units.filter(u => u.id).map(u => <option key={u.id} value={u.id}>{u.name} — {u.code}</option>)}
          </select>
        </label>
        <Button type="submit" variant="primary" disabled={busy}>Vincular usuário</Button>
      </form>
    </section>
    <section className="card section-stack">
      <h2>Lotações ativas</h2>
      {assignments.length === 0 ? <p>Sem lotações registradas.</p> : (
        <table><thead><tr><th>Usuário</th><th>Unidade</th><th>Ação</th></tr></thead>
          <tbody>{assignments.map(a => <tr key={a.id}>
            <td>{userName(a.user_id)}</td><td>{unitName(a.unit_id)}</td>
            <td><Button type="button" disabled={busy} onClick={() => { void revoke(a.id); }}>Encerrar lotação</Button></td>
          </tr>)}</tbody></table>
      )}
    </section>
  </main>;
}
