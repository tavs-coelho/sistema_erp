"use client";

import { FormEvent, useState } from "react";

import { API_URL, clearSessionCookies, setSessionCookies } from "@/lib/auth";

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
    window.localStorage.setItem("access_token", data.access_token);
    window.localStorage.setItem("role", data.role);
    window.localStorage.setItem("username", username);
    clearSessionCookies();
    setSessionCookies(data.role, username);
    setMessage("Login realizado com sucesso");
    window.location.href = "/";
  };

  return (
    <main className="card" style={{ maxWidth: 460, margin: "40px auto", fontFamily: "Arial, sans-serif", display: "grid", gap: 12 }}>
      <h1>Acesso ao ERP Municipal</h1>
      <p className="muted">Entre com um usuário de demonstração para navegar pelos módulos.</p>
      <form onSubmit={submit} className="section-stack">
        <label className="field-group">
          Usuário
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </label>
        <label className="field-group">
          Senha
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </label>
        <button type="submit" className="btn btn-primary">
          Entrar
        </button>
      </form>
      {message ? <p className={message.toLowerCase().includes("falha") ? "notice error" : "notice"}>{message}</p> : null}
      <small className="muted">Usuário demo: admin1 / demo123</small>
    </main>
  );
}
