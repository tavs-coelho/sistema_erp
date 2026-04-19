"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

type Dashboard = {
  total_empenhado: number;
  total_pago: number;
  total_receita: number;
};

function readCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const entry = document.cookie.split(";").find((item) => item.trim().startsWith(`${name}=`));
  if (!entry) return "";
  return decodeURIComponent(entry.trim().slice(name.length + 1));
}

export default function Home() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [message, setMessage] = useState<string>("");
  const [token] = useState(() => readCookie("access_token"));
  const [role] = useState(() => readCookie("role"));

  useEffect(() => {
    if (!token) return;
    fetch(`${API_URL}/accounting/dashboard`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => res.json())
      .then(setDashboard)
      .catch(() => setMessage("Não foi possível carregar o dashboard."));
  }, [token]);

  const logout = async () => {
    await fetch(`${API_URL}/auth/logout`, { method: "POST" });
    document.cookie = "access_token=; Max-Age=0; path=/";
    document.cookie = "role=; Max-Age=0; path=/";
    window.location.href = "/login";
  };

  return (
    <main style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
      <h1>Sistema ERP Municipal</h1>
      <p>
        Perfil logado: <strong>{role || "desconhecido"}</strong>
      </p>
      <nav style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <a href="/fase-2">Fluxo Fase 2 (Admin)</a>
        <a href="/public">Portal da Transparência</a>
        <button onClick={logout}>Sair</button>
      </nav>
      {message && <p>{message}</p>}
      <section>
        <h2>Dashboard Contábil</h2>
        <ul>
          <li>Total empenhado: R$ {dashboard?.total_empenhado?.toFixed(2) ?? "..."}</li>
          <li>Total pago: R$ {dashboard?.total_pago?.toFixed(2) ?? "..."}</li>
          <li>Total receita: R$ {dashboard?.total_receita?.toFixed(2) ?? "..."}</li>
        </ul>
      </section>
    </main>
  );
}
