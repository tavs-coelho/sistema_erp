"use client";

import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { API_URL, authToken, clearSessionCookies } from "@/lib/auth";

export default function TrocarSenhaPage() {
  const { toast } = useToast();
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [loading, setLoading] = useState(false);

  // Redirect to /login if not authenticated
  useEffect(() => {
    if (!authToken()) {
      window.location.href = "/login";
    }
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (novaSenha.length < 6) {
      toast("A senha deve ter no mínimo 6 caracteres.", "error");
      return;
    }
    if (novaSenha !== confirmacao) {
      toast("As senhas não coincidem.", "error");
      return;
    }
    setLoading(true);
    try {
      const token = authToken();
      const res = await fetch(`${API_URL}/employee-portal/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ new_password: novaSenha }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast(data.detail || "Falha ao trocar a senha.", "error");
        return;
      }
      toast("Senha alterada com sucesso!", "success");
      window.location.href = "/";
    } catch {
      toast("Erro de comunicação com o servidor.", "error");
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    window.localStorage.removeItem("access_token");
    window.localStorage.removeItem("role");
    window.localStorage.removeItem("username");
    clearSessionCookies();
    window.location.href = "/login";
  };

  return (
    <main className="login-page">
      <section className="login-hero">
        <h1>Troca de senha obrigatória</h1>
        <p>Por segurança, você precisa definir uma nova senha antes de continuar.</p>
      </section>

      <Card className="login-card">
        <h2>Nova senha</h2>
        <p className="muted">Escolha uma senha forte com pelo menos 6 caracteres.</p>
        <form onSubmit={submit} className="section-stack">
          <label className="field-group">
            Nova senha
            <Input
              type="password"
              value={novaSenha}
              onChange={(e) => setNovaSenha(e.target.value)}
              autoComplete="new-password"
              required
              minLength={6}
              disabled={loading}
            />
          </label>
          <label className="field-group">
            Confirmar nova senha
            <Input
              type="password"
              value={confirmacao}
              onChange={(e) => setConfirmacao(e.target.value)}
              autoComplete="new-password"
              required
              minLength={6}
              disabled={loading}
            />
          </label>
          <Button type="submit" variant="primary" disabled={loading}>
            {loading ? "Salvando…" : "Salvar nova senha"}
          </Button>
        </form>

        <button type="button" className="btn btn-ghost btn-sm" onClick={logout} style={{ marginTop: 8 }}>
          Cancelar e sair
        </button>
      </Card>
    </main>
  );
}
