"use client";

import { useEffect, useMemo, useState } from "react";

import { useToast } from "@/components/ui/toast";
import { authJson } from "@/lib/auth";

type AuditItem = {
  id: number;
  user_id: number | null;
  action: string;
  entity: string;
  entity_id: string;
  created_at: string;
};

type UserItem = { id: number; username: string; role: string };

export default function AuditoriaPage() {
  const { toast } = useToast();
  const [items, setItems] = useState<AuditItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<{ username: string; role: string }>({
    username: "",
    role: "",
  });

  const userMap = useMemo(() => new Map(users.map((u) => [u.id, u])), [users]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        setLoading(true);
        const [me, audit, allUsers] = await Promise.all([
          authJson("/auth/me"),
          authJson(`/core/audit-logs?page=${page}&size=20`),
          authJson("/core/users"),
        ]);
        if (!active) return;
        const meData = me as { username: string; role: string };
        const logs = (audit || { total: 0, items: [] }) as { total: number; items: AuditItem[] };
        const parsedUsers = (allUsers || []) as UserItem[];
        setProfile({ username: meData.username || "", role: meData.role || "" });
        const localUserMap = new Map(parsedUsers.map((u) => [u.id, u]));
        setTotal(logs.total || 0);
        setUsers(parsedUsers);
        const filtered = (logs.items || []).filter((item: AuditItem) => {
          if (actionFilter && item.action !== actionFilter) return false;
          if (entityFilter && !item.entity.toLowerCase().includes(entityFilter.toLowerCase())) return false;
          if (userFilter) {
            const u = item.user_id ? localUserMap.get(item.user_id) : null;
            if (!u?.username?.toLowerCase().includes(userFilter.toLowerCase())) return false;
          }
          return true;
        });
        setItems(filtered);
      } catch (error) {
        if (!active) return;
        setItems([]);
        toast(error instanceof Error ? error.message : "Falha ao carregar auditoria", "error");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [page, actionFilter, entityFilter, userFilter]);

  return (
    <main className="module-page">
      <h1>Auditoria</h1>
      <p className="muted">Perfil atual: <strong suppressHydrationWarning>{profile.role || "carregando..."}</strong> · Usuário: <strong suppressHydrationWarning>{profile.username || "carregando..."}</strong></p>

      {loading ? <p className="notice">Carregando eventos de auditoria...</p> : null}

      <section className="card section-stack">
        <h2>Filtros</h2>
        <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          <label className="field-group">
            Ação
            <select value={actionFilter} onChange={(e) => { setPage(1); setActionFilter(e.target.value); }}>
              <option value="">Todas</option>
              <option value="create">create</option>
              <option value="update">update</option>
              <option value="delete">delete</option>
            </select>
          </label>
          <label className="field-group">
            Módulo/entidade
            <input value={entityFilter} onChange={(e) => { setPage(1); setEntityFilter(e.target.value); }} placeholder="Ex.: commitments" />
          </label>
          <label className="field-group">
            Usuário
            <input value={userFilter} onChange={(e) => { setPage(1); setUserFilter(e.target.value); }} placeholder="Ex.: admin1" />
          </label>
        </div>
      </section>

      <section className="card section-stack">
        <h2>Eventos recentes</h2>
        <table>
          <thead>
            <tr>
              <th>Data/hora</th>
              <th>Usuário</th>
              <th>Papel</th>
              <th>Módulo/entidade</th>
              <th>Ação</th>
              <th>Registro</th>
            </tr>
          </thead>
          <tbody>
            {items.length > 0 ? (
              items.map((row) => {
                const user = row.user_id ? userMap.get(row.user_id) : null;
                return (
                  <tr key={row.id}>
                    <td>{new Date(row.created_at).toLocaleString("pt-BR")}</td>
                    <td>{user?.username || "-"}</td>
                    <td>{user?.role || "-"}</td>
                    <td>{row.entity}</td>
                    <td><span className={`chip ${row.action}`}>{row.action}</span></td>
                    <td>{row.entity_id}</td>
                  </tr>
                );
              })
            ) : (
              <tr><td colSpan={6} className="empty-state">Nenhum evento de auditoria para os filtros informados.</td></tr>
            )}
          </tbody>
        </table>
        <div className="pagination">
          <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
          <span>Página {page} · Total aproximado: {total}</span>
          <button className="btn" disabled={items.length < 20} onClick={() => setPage((p) => p + 1)}>Próxima</button>
        </div>
      </section>
    </main>
  );
}
