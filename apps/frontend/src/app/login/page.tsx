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
    <main style={{ maxWidth: 420, margin: "64px auto", fontFamily: "Arial, sans-serif" }}>
      <h1>Login - ERP Municipal</h1>
      <form onSubmit={submit} style={{ display: "grid", gap: 12 }}>
        <label>
          Usuário
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <label>
          Senha
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button type="submit">Entrar</button>
      </form>
      <p>{message}</p>
      <small>Usuário demo: admin1 / demo123</small>
    </main>
  );
}
