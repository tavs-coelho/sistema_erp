"use client";

import { FormEvent, useState } from "react";

import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Toast } from "@/components/ui/toast";
import { API_URL, clearSessionCookies, setSessionCookies } from "@/lib/auth";

export default function LoginPage() {
  const { theme } = useTheme();
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
    <main className="login-page">
      <section className="login-hero">
        {theme.logo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={theme.logo_url} alt={theme.org_name} className="brand-logo login-brand" />
        ) : null}
        <p className="badge badge-soft">White-label institucional</p>
        <h1>{theme.org_name}</h1>
        <p>Gestão pública integrada com experiência moderna, segura e orientada a produtividade.</p>
      </section>

      <Card className="login-card">
        <h2>Acesso ao sistema</h2>
        <p className="muted">Use as credenciais de demonstração para navegar pelos módulos.</p>
        <form onSubmit={submit} className="section-stack">
          <label className="field-group">
            Usuário
            <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          </label>
          <label className="field-group">
            Senha
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          </label>
          <Button type="submit" variant="primary">
            Entrar
          </Button>
        </form>
        {message ? <Toast variant={message.toLowerCase().includes("falha") ? "error" : "success"}>{message}</Toast> : null}
        <small className="muted">Usuário demo: admin1 / demo123</small>
      </Card>
    </main>
  );
}
