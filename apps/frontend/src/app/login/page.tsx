"use client";

import { FormEvent, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

export default function LoginPage() {
  const [username, setUsername] = useState("admin1");
  const [password, setPassword] = useState("demo123");
  const [message, setMessage] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.detail || "Falha no login");
      return;
    }
    const cookieFlags = `path=/; SameSite=Lax${window.location.protocol === "https:" ? "; Secure" : ""}`;
    document.cookie = `access_token=${encodeURIComponent(data.access_token)}; ${cookieFlags}`;
    document.cookie = `role=${encodeURIComponent(data.role)}; ${cookieFlags}`;
    setMessage("Login realizado com sucesso");
    window.location.href = "/";
  };

  return (
    <main className="card" style={{ maxWidth: 460, margin: "40px auto", fontFamily: "Arial, sans-serif", display: "grid", gap: 12 }}>
      <h1>Acesso ao ERP Municipal</h1>
      <p className="muted">Entre com um usuário de demonstração para navegar pelos módulos.</p>
      <form onSubmit={submit} style={{ display: "grid", gap: 12 }}>
        <label>
          Usuário
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </label>
        <label>
          Senha
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </label>
        <button type="submit" style={{ background: "#124e9c", color: "#fff", border: 0, borderRadius: 6, padding: "10px 14px", cursor: "pointer" }}>
          Entrar
        </button>
      </form>
      <p>{message}</p>
      <small className="muted">Usuário demo: admin1 / demo123</small>
    </main>
  );
}
