"use client";

import { FormEvent, useState } from "react";

import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { browserAuthJson, clearLegacyTokens, setSessionCookies } from "@/lib/auth";

export default function LoginPage() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [challengeToken, setChallengeToken] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    try {
      const endpoint = challengeToken ? "/mfa/verify-login" : "/login";
      const body = challengeToken
        ? { challenge_token: challengeToken, code: mfaCode }
        : { username, password };
      const data = await browserAuthJson(endpoint, {
        method: "POST", body: JSON.stringify(body),
      });
      if (data.mfa_required) {
        setChallengeToken(data.challenge_token);
        setMfaCode("");
        setPassword("");
        toast("Informe o código do aplicativo autenticador ou de recuperação.", "success");
        return;
      }
      // Only the server sets the HttpOnly auth cookies. Never store JWTs here.
      clearLegacyTokens();
      setSessionCookies(String(data.role || ""), username);
      toast("Login realizado com sucesso", "success");
      window.location.replace(data.must_change_password ? "/trocar-senha" : "/");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha na autenticação", "error");
    } finally {
      setLoading(false);
    }
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
        <p className="muted">{challengeToken ? "Verificação em duas etapas" : "Informe as credenciais da sua entidade."}</p>
        <form onSubmit={submit} className="section-stack">
          {challengeToken ? (
            <>
              <label className="field-group">
                Código TOTP (6 dígitos) ou código de recuperação
                <Input value={mfaCode} onChange={(e) => setMfaCode(e.target.value.trim())}
                  autoComplete="one-time-code" inputMode="text" required />
              </label>
              <Button type="button" variant="secondary" onClick={() => {
                setChallengeToken("");
                setMfaCode("");
              }}>Voltar ao login</Button>
            </>
          ) : (
            <>
              <label className="field-group">
                Usuário
                <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
              </label>
              <label className="field-group">
                Senha
                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
              </label>
            </>
          )}
          <Button type="submit" variant="primary" disabled={loading}>
            {loading ? "Validando..." : challengeToken ? "Validar código" : "Entrar"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
