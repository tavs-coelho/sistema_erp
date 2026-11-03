"use client";

import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { authJson, clearSessionCookies } from "@/lib/auth";

type MfaStatus = { enabled: boolean; recovery_codes_remaining: number };
type SetupDetails = { secret: string; provisioning_uri: string; expires_in: number };
type SetupConfirmed = { enabled: boolean; recovery_codes: string[] };

function exitToLogin() {
  window.localStorage.removeItem("access_token");
  window.localStorage.removeItem("role");
  window.localStorage.removeItem("username");
  clearSessionCookies();
  window.location.href = "/login";
}

export default function SecurityPage() {
  const { toast } = useToast();
  const [status, setStatus] = useState<MfaStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [setup, setSetup] = useState<SetupDetails | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);

  useEffect(() => {
    const task = setTimeout(() => {
      void authJson("/auth/mfa/status")
        .then((data: MfaStatus) => setStatus(data))
        .catch(() => toast("Não foi possível consultar o MFA", "error"));
    }, 0);
    return () => clearTimeout(task);
  }, []);

  const startSetup = async (event: FormEvent) => {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    try {
      const result = await authJson("/auth/mfa/setup", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: password }),
      }) as SetupDetails;
      setSetup(result);
      setPassword("");
      setCode("");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Não foi possível iniciar o MFA", "error");
    } finally { setLoading(false); }
  };

  const confirmSetup = async (event: FormEvent) => {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    try {
      const result = await authJson("/auth/mfa/confirm", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code.trim() }),
      }) as SetupConfirmed;
      setRecoveryCodes(result.recovery_codes);
      setSetup(null);
      setCode("");
      setStatus({ enabled: true, recovery_codes_remaining: result.recovery_codes.length });
      toast("MFA ativado. Guarde os códigos de recuperação antes de sair.", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Código inválido", "error");
    } finally { setLoading(false); }
  };

  const disableMfa = async (event: FormEvent) => {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    try {
      await authJson("/auth/mfa/disable", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: password, code: code.trim() }),
      });
      exitToLogin();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Não foi possível desativar", "error");
      setLoading(false);
    }
  };

  return (
    <main className="module-page section-stack" style={{ padding: 24, maxWidth: 740 }}>
      <h1>Segurança da conta</h1>
      <p className="muted">Proteja o acesso com Google Authenticator ou outro aplicativo compatível com TOTP.</p>
      {status === null ? (
        <p>Carregando configurações...</p>
      ) : recoveryCodes.length ? (
        <Card>
          <h2>Códigos de recuperação — exibição única</h2>
          <p>Salve estes códigos em local seguro. Cada código só pode ser utilizado uma vez. Eles não serão exibidos novamente.</p>
          <ul>{recoveryCodes.map((value) => <li key={value}><code>{value}</code></li>)}</ul>
          <Button variant="primary" onClick={exitToLogin}>Salvei os códigos. Entrar novamente</Button>
        </Card>
      ) : status.enabled ? (
        <Card>
          <h2>Autenticação em duas etapas ativada</h2>
          <p>Há {status.recovery_codes_remaining} códigos de recuperação disponíveis.</p>
          <p>Desativar o MFA revoga todas as sessões e exige a senha atual e um código válido.</p>
          <form onSubmit={disableMfa} className="section-stack">
            <label className="field-group">Senha atual
              <Input type="password" autoComplete="current-password" value={password}
                onChange={(event) => setPassword(event.target.value)} required />
            </label>
            <label className="field-group">Código TOTP ou de recuperação
              <Input autoComplete="one-time-code" value={code}
                onChange={(event) => setCode(event.target.value)} required />
            </label>
            <Button type="submit" variant="danger" disabled={loading}>
              {loading ? "Validando..." : "Desativar autenticação em duas etapas"}
            </Button>
          </form>
        </Card>
      ) : setup ? (
        <Card>
          <h2>Conectar aplicativo autenticador</h2>
          <p>Adicione manualmente a conta no Google Authenticator usando esta chave. Não compartilhe a chave.</p>
          <p><strong>Chave de configuração:</strong> <code>{setup.secret}</code></p>
          <p className="muted">Tipo: TOTP • 6 dígitos • período de 30 segundos.</p>
          <form onSubmit={confirmSetup} className="section-stack">
            <label className="field-group">Código de 6 dígitos
              <Input value={code} onChange={(event) => setCode(event.target.value)}
                autoComplete="one-time-code" inputMode="numeric" maxLength={6} required />
            </label>
            <Button type="submit" variant="primary" disabled={loading}>
              {loading ? "Validando..." : "Confirmar e ativar MFA"}
            </Button>
          </form>
        </Card>
      ) : (
        <Card>
          <h2>Ativar autenticação em duas etapas</h2>
          <p>Confirme sua senha para gerar uma chave individual de configuração.</p>
          <form onSubmit={startSetup} className="section-stack">
            <label className="field-group">Senha atual
              <Input type="password" autoComplete="current-password" value={password}
                onChange={(event) => setPassword(event.target.value)} required />
            </label>
            <Button type="submit" variant="primary" disabled={loading}>
              {loading ? "Preparando..." : "Iniciar configuração"}
            </Button>
          </form>
        </Card>
      )}
    </main>
  );
}
