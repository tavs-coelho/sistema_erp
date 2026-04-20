"use client";

import { FormEvent, useEffect, useState } from "react";

import { useTheme } from "@/components/theme-provider";
import { authToken } from "@/lib/auth";
import {
  BrandingTheme,
  contrastRatio,
  ContrastLevel,
  saveBrandingToApi,
  wcagLevel,
} from "@/lib/theme";

// ── Contrast badge ────────────────────────────────────────────────────────────

function ContrastBadge({ ratio, level }: { ratio: number; level: ContrastLevel }) {
  const label = level === "fail" ? "Falha" : level;
  const cls =
    level === "AAA" || level === "AA"
      ? "chip pago"
      : level === "AA-large"
        ? "chip empenhado"
        : "chip baixado";
  return (
    <span className={cls} title={`Razão de contraste: ${ratio.toFixed(2)}:1`}>
      {label} · {ratio.toFixed(2)}:1
    </span>
  );
}

// ── Color field with contrast check ──────────────────────────────────────────

function ColorField({
  label,
  id,
  value,
  onChange,
  contrastAgainst,
  contrastLabel,
}: {
  label: string;
  id: string;
  value: string;
  onChange: (v: string) => void;
  contrastAgainst?: string;
  contrastLabel?: string;
}) {
  const isValid = /^#[0-9a-fA-F]{6}$/.test(value);
  const ratio = isValid && contrastAgainst ? contrastRatio(value, contrastAgainst) : null;
  const level: ContrastLevel | null = ratio !== null ? wcagLevel(ratio) : null;

  return (
    <div className="field-group">
      <label htmlFor={id}>{label}</label>
      <div className="toolbar" style={{ gap: 8, marginTop: 4 }}>
        <input
          id={id}
          type="color"
          value={isValid ? value : "#1d4ed8"}
          onChange={(e) => onChange(e.target.value)}
          style={{ width: 48, height: 38, padding: 2, cursor: "pointer", borderRadius: 8, border: "1px solid var(--border)" }}
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="#rrggbb"
          maxLength={7}
          className={`input-narrow${isValid ? "" : " error"}`}
          style={{ width: 110 }}
        />
        {ratio !== null && level !== null && contrastLabel && (
          <span className="text-sm muted">
            vs {contrastLabel}: <ContrastBadge ratio={ratio} level={level} />
          </span>
        )}
      </div>
      {!isValid && <p className="text-xs" style={{ color: "#e53e3e", marginTop: 2 }}>Cor inválida — use formato #rrggbb</p>}
    </div>
  );
}

// ── Preview panel ─────────────────────────────────────────────────────────────

function BrandPreview({ draft }: { draft: BrandingTheme }) {
  const isValidHex = (c: string) => /^#[0-9a-fA-F]{6}$/.test(c);
  const primary = isValidHex(draft.primary_color) ? draft.primary_color : "#1d4ed8";
  const secondary = isValidHex(draft.secondary_color) ? draft.secondary_color : "#0f172a";
  const accent = isValidHex(draft.accent_color) ? draft.accent_color : "#0ea5e9";

  const initials = draft.org_name
    .split(" ")
    .filter(Boolean)
    .map((t) => t[0])
    .join("")
    .slice(0, 3)
    .toUpperCase();

  return (
    <aside
      className="card"
      style={{
        padding: 0,
        overflow: "hidden",
        border: "2px solid var(--border)",
      }}
    >
      {/* Sidebar strip */}
      <div
        style={{
          background: `linear-gradient(180deg, ${secondary} 0%, color-mix(in srgb, ${primary} 70%, #000) 100%)`,
          padding: "16px 12px",
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {draft.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={draft.logo_url}
              alt={draft.org_name}
              style={{ width: 32, height: 32, objectFit: "contain", borderRadius: 6 }}
            />
          ) : (
            <span
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: `linear-gradient(135deg, ${primary}, ${accent})`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: 11,
                color: "#fff",
              }}
            >
              {initials}
            </span>
          )}
          <div>
            <div style={{ color: "#fff", fontWeight: 700, fontSize: 13 }}>{draft.org_name}</div>
            <div style={{ color: "rgba(255,255,255,0.55)", fontSize: 11 }}>ERP institucional</div>
          </div>
        </div>
        {/* Fake nav items */}
        {["Painel", "Contábil", "RH", "Tributário"].map((item) => (
          <div
            key={item}
            style={{
              padding: "6px 10px",
              borderRadius: 8,
              color: item === "Painel" ? "#fff" : "rgba(255,255,255,0.65)",
              fontSize: 13,
              background: item === "Painel" ? `rgba(255,255,255,0.14)` : "transparent",
            }}
          >
            {item}
          </div>
        ))}
      </div>

      {/* Top-bar strip */}
      <div
        style={{
          borderBottom: "1px solid var(--border)",
          background: "rgba(255,255,255,0.92)",
          padding: "8px 14px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <strong style={{ fontSize: 13 }}>{draft.app_title}</strong>
        <span
          style={{
            fontSize: 11,
            borderRadius: 999,
            padding: "3px 8px",
            border: "1px solid var(--border)",
            color: "var(--muted)",
          }}
        >
          admin
        </span>
      </div>

      {/* Fake content */}
      <div style={{ padding: 14 }}>
        <div
          style={{
            height: 36,
            borderRadius: 8,
            background: `linear-gradient(135deg, ${primary}, ${accent})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontWeight: 600,
            fontSize: 13,
            marginBottom: 10,
          }}
        >
          Botão primário
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {["KPI 1", "KPI 2", "KPI 3"].map((k) => (
            <div
              key={k}
              style={{
                flex: 1,
                background: `color-mix(in srgb, ${primary} 8%, #fff)`,
                border: `1px solid color-mix(in srgb, ${primary} 18%, var(--border))`,
                borderRadius: 10,
                padding: "8px 6px",
                textAlign: "center",
                fontSize: 11,
                color: "var(--muted)",
              }}
            >
              {k}
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function BrandingPage() {
  const { theme, updateTheme } = useTheme();
  const [draft, setDraft] = useState<BrandingTheme>(theme);
  const [status, setStatus] = useState("");
  const isError = status.toLowerCase().includes("erro") || status.toLowerCase().includes("falha");

  // Keep draft in sync if the theme is hydrated from API after mount.
  useEffect(() => {
    setDraft(theme);
  }, [theme]);

  const updateDraft = (partial: Partial<BrandingTheme>) =>
    setDraft((prev) => ({ ...prev, ...partial }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setStatus("Salvando…");
    try {
      const token = authToken();
      const saved = await saveBrandingToApi(draft, token);
      updateTheme(saved);
      setDraft(saved);
      setStatus("Configurações de identidade visual salvas com sucesso.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Erro ao salvar branding");
    }
  };

  const handleReset = () => {
    setDraft(theme);
    setStatus("");
  };

  // Contrast summaries
  const primaryVsWhite = /^#[0-9a-fA-F]{6}$/.test(draft.primary_color)
    ? contrastRatio(draft.primary_color, "#ffffff")
    : null;
  const secondaryVsWhite = /^#[0-9a-fA-F]{6}$/.test(draft.secondary_color)
    ? contrastRatio(draft.secondary_color, "#ffffff")
    : null;
  const accentVsWhite = /^#[0-9a-fA-F]{6}$/.test(draft.accent_color)
    ? contrastRatio(draft.accent_color, "#ffffff")
    : null;
  const anyFail = [primaryVsWhite, secondaryVsWhite, accentVsWhite].some(
    (r) => r !== null && wcagLevel(r) === "fail",
  );

  return (
    <main className="module-page">
      <h1>Identidade Visual (White-label)</h1>
      <p className="muted">
        Configure cores, logotipo e textos institucionais. As alterações são persistidas no banco de
        dados e aplicadas a todos os usuários do tenant.
      </p>

      {status && (
        <p className={isError ? "notice error" : "notice"}>
          <strong>{status}</strong>
        </p>
      )}

      {anyFail && (
        <p className="notice error">
          ⚠ Uma ou mais cores selecionadas não passam na verificação de contraste WCAG AA com texto
          branco. Considere usar um tom mais escuro para garantir acessibilidade.
        </p>
      )}

      <div className="auto-grid-lg section-top">
        {/* ── Form ── */}
        <form onSubmit={handleSubmit} className="card section-stack">
          <h2>Configurações de marca</h2>

          <div className="field-group">
            <label htmlFor="org_name">Nome da organização</label>
            <input
              id="org_name"
              value={draft.org_name}
              onChange={(e) => updateDraft({ org_name: e.target.value })}
              placeholder="Prefeitura Municipal de …"
              required
            />
          </div>

          <div className="field-group">
            <label htmlFor="app_title">Título do sistema</label>
            <input
              id="app_title"
              value={draft.app_title}
              onChange={(e) => updateDraft({ app_title: e.target.value })}
              placeholder="Sistema ERP Municipal"
              required
            />
          </div>

          <div className="field-group">
            <label htmlFor="logo_url">URL do logotipo</label>
            <input
              id="logo_url"
              type="url"
              value={draft.logo_url}
              onChange={(e) => updateDraft({ logo_url: e.target.value })}
              placeholder="https://…/logo.png (deixe vazio para usar iniciais)"
            />
          </div>

          <div className="field-group">
            <label htmlFor="favicon_url">URL do favicon</label>
            <input
              id="favicon_url"
              type="url"
              value={draft.favicon_url}
              onChange={(e) => updateDraft({ favicon_url: e.target.value })}
              placeholder="/favicon.ico"
            />
          </div>

          <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "4px 0" }} />
          <p className="text-sm muted">
            As verificações de contraste abaixo seguem o padrão WCAG 2.1 — texto branco sobre a cor
            selecionada. <strong>AA</strong> exige 4.5:1, <strong>AA-large</strong> exige 3:1.
          </p>

          <ColorField
            label="Cor primária"
            id="primary_color"
            value={draft.primary_color}
            onChange={(v) => updateDraft({ primary_color: v })}
            contrastAgainst="#ffffff"
            contrastLabel="branco"
          />

          <ColorField
            label="Cor secundária"
            id="secondary_color"
            value={draft.secondary_color}
            onChange={(v) => updateDraft({ secondary_color: v })}
            contrastAgainst="#ffffff"
            contrastLabel="branco"
          />

          <ColorField
            label="Cor de destaque (accent)"
            id="accent_color"
            value={draft.accent_color}
            onChange={(v) => updateDraft({ accent_color: v })}
            contrastAgainst="#ffffff"
            contrastLabel="branco"
          />

          {/* Summary table */}
          <table className="mt-2">
            <thead>
              <tr>
                <th>Cor</th>
                <th>Hex</th>
                <th>Contraste vs branco</th>
              </tr>
            </thead>
            <tbody>
              {[
                { label: "Primária", color: draft.primary_color, ratio: primaryVsWhite },
                { label: "Secundária", color: draft.secondary_color, ratio: secondaryVsWhite },
                { label: "Destaque", color: draft.accent_color, ratio: accentVsWhite },
              ].map(({ label, color, ratio }) => (
                <tr key={label}>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        width: 16,
                        height: 16,
                        borderRadius: 4,
                        background: /^#[0-9a-fA-F]{6}$/.test(color) ? color : "#ccc",
                        border: "1px solid var(--border)",
                        verticalAlign: "middle",
                        marginRight: 6,
                      }}
                    />
                    {label}
                  </td>
                  <td className="td-code">{color}</td>
                  <td>
                    {ratio !== null ? (
                      <ContrastBadge ratio={ratio} level={wcagLevel(ratio)} />
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="toolbar mt-2">
            <button className="btn btn-primary" type="submit">
              Salvar configurações
            </button>
            <button className="btn" type="button" onClick={handleReset}>
              Descartar alterações
            </button>
          </div>
        </form>

        {/* ── Preview ── */}
        <div className="section-stack">
          <h2 style={{ marginBottom: 8 }}>Pré-visualização</h2>
          <p className="text-sm muted">
            Prévia em tempo real do tema. A barra lateral e o topbar refletem as cores e o logotipo
            configurados.
          </p>
          <BrandPreview draft={draft} />
        </div>
      </div>
    </main>
  );
}
