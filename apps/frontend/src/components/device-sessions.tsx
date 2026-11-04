"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { authJson, logoutBrowser } from "@/lib/auth";

type DeviceSession = {
  id: string;
  user_agent: string;
  created_at: string;
  last_used_at: string;
  expires_at: string;
  current: boolean;
};



export function DeviceSessions() {
  const { toast } = useToast();
  const [sessions, setSessions] = useState<DeviceSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function loadSessions() {
    try {
      const data = await authJson("/auth/sessions") as DeviceSession[];
      setSessions(data);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao carregar sessões", "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const task = setTimeout(() => { void loadSessions(); }, 0);
    return () => clearTimeout(task);
  }, []);

  async function closeSession(session: DeviceSession) {
    if (busy) return;
    setBusy(true);
    try {
      if (session.current) {
        await logoutBrowser();
        window.location.replace("/login");
        return;
      }
      await authJson(`/auth/sessions/${encodeURIComponent(session.id)}`, { method: "DELETE" });
      await loadSessions();
      toast("Sessão encerrada", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Não foi possível encerrar a sessão", "error");
    } finally {
      setBusy(false);
    }
  }

  async function closeAll() {
    if (busy) return;
    if (!window.confirm("Encerrar todas as sessões, inclusive a atual?")) return;
    setBusy(true);
    try {
      await logoutBrowser(true);
      window.location.replace("/login");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao encerrar sessões", "error");
      setBusy(false);
    }
  }

  return (
    <Card>
      <h2>Dispositivos e sessões</h2>
      <p className="muted">
        Controle os dispositivos conectados à sua conta. A exclusão de uma
        sessão bloqueia seus tokens de acesso e renovação.
      </p>
      {loading ? <p>Carregando sessões...</p> : sessions.length === 0 ? (
        <p>Não há sessões ativas identificadas.</p>
      ) : (
        <ul className="section-stack" style={{ listStyle: "none", padding: 0 }}>
          {sessions.map((session) => (
            <li key={session.id} style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <strong>{session.user_agent || "Dispositivo não identificado"}</strong>
                {session.current ? <span> · Sessão atual</span> : null}
                <div className="muted" style={{ fontSize: 12 }}>
                  Última atividade: {new Date(session.last_used_at).toLocaleString("pt-BR")}
                </div>
              </div>
              <Button type="button" variant="secondary" disabled={busy}
                onClick={() => { void closeSession(session); }}>
                Encerrar
              </Button>
            </li>
          ))}
        </ul>
      )}
      <Button type="button" variant="danger" disabled={loading || busy}
        onClick={() => { void closeAll(); }}>
        Encerrar sessões de todos os dispositivos
      </Button>
    </Card>
  );
}
