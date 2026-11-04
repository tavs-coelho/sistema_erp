"use client";

import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { authJson, clearBrowserCookies, logoutBrowser } from "@/lib/auth";

export default function TrocarSenhaPage() {
  const { toast } = useToast();
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Cookie validity is checked by the server, not by inspecting JS storage.
    const task = setTimeout(() => {
      void authJson("/auth/me").catch(() => window.location.replace("/login?expired=1"));
    }, 0);
    return () => clearTimeout(task);
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
      await authJson("/employee-portal/change-password", {
        method: "POST", body: JSON.stringify({ new_password: novaSenha }),
      });
      await clearBrowserCookies();
      toast("Senha alterada. Entre novamente com a nova senha.", "success");
      window.location.replace("/login");
    } catch {
      toast("Erro de comunicação com o servidor.", "error");
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    await logoutBrowser();
    window.location.replace("/login");
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
