"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { authJson } from "@/lib/auth";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";

export type RegistryField = {
  key: string;
  label: string;
  kind?: "text" | "number" | "date" | "email" | "textarea" | "select" | "checkbox";
  options?: { value: string; label: string }[];
  required?: boolean;
  readonlyOnEdit?: boolean;
};

type Entry = Record<string, unknown> & { id: number };

type Props = {
  title: string;
  description: string;
  endpoint: string;
  fields: RegistryField[];
};

function printable(value: unknown) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Sim" : "Não";
  return String(value);
}

export function RegistryEditor({ title, description, endpoint, fields }: Props) {
  const { toast } = useToast();
  const [items, setItems] = useState<Entry[]>([]);
  const [form, setForm] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState<number | null>(null);
  const [filter, setFilter] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const result = await authJson(endpoint);
      setItems(Array.isArray(result) ? result as Entry[] : (result.items || []) as Entry[]);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao carregar dados", "error");
    } finally {
      setLoading(false);
    }
  }, [endpoint, toast]);

  useEffect(() => {
    const task = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(task);
  }, [load]);

  const reset = () => { setEditing(null); setForm({}); };

  const edit = (item: Entry) => {
    setEditing(item.id);
    const values: Record<string, string> = {};
    for (const field of fields) values[field.key] = printable(item[field.key]) === "—"
      ? "" : typeof item[field.key] === "boolean" ? String(item[field.key]) : String(item[field.key]);
    setForm(values);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    try {
      const body: Record<string, unknown> = {};
      for (const field of fields) {
        if (editing !== null && field.readonlyOnEdit) continue;
        const raw = form[field.key] ?? "";
        body[field.key] = field.kind === "number" ? (raw.trim() === "" ? null : Number(raw))
          : field.kind === "checkbox" ? raw === "true"
          : raw.trim();
      }
      await authJson(editing === null ? endpoint : `${endpoint}/${editing}`, {
        method: editing === null ? "POST" : "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      toast(editing === null ? "Cadastro registrado" : "Cadastro atualizado", "success");
      reset();
      await load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao salvar", "error");
    } finally {
      setSaving(false);
    }
  };

  const visible = items.filter(item => !filter || fields.some(field =>
    printable(item[field.key]).toLowerCase().includes(filter.toLowerCase())));

  return (
    <main className="module-page section-stack" style={{ padding: 24 }}>
      <h1>{title}</h1>
      <p className="muted">{description}</p>
      <section className="card section-stack" aria-label="Formulário de cadastro">
        <h2>{editing === null ? "Novo cadastro" : `Editar registro #${editing}`}</h2>
        <form className="section-stack" onSubmit={(e) => { void save(e); }}>
          {fields.map(field => (
            <label key={field.key} className="field-group">
              {field.label}
              {field.kind === "textarea" ? (
                <textarea value={form[field.key] ?? ""}
                  onChange={e => setForm(prev => ({ ...prev, [field.key]: e.target.value }))}
                  required={field.required} rows={3} />
              ) : field.kind === "select" ? (
                <select value={form[field.key] ?? ""}
                  onChange={e => setForm(prev => ({ ...prev, [field.key]: e.target.value }))}
                  required={field.required}>
                  <option value="">Selecione</option>
                  {(field.options || []).map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                </select>
              ) : field.kind === "checkbox" ? (
                <input type="checkbox" checked={(form[field.key] ?? "false") === "true"}
                  onChange={e => setForm(prev => ({ ...prev, [field.key]: String(e.target.checked) }))} />
              ) : (
                <input type={field.kind || "text"} value={form[field.key] ?? ""}
                  onChange={e => setForm(prev => ({ ...prev, [field.key]: e.target.value }))}
                  required={field.required}
                  disabled={editing !== null && field.readonlyOnEdit} />
              )}
            </label>
          ))}
          <div style={{ display: "flex", gap: 8 }}>
            <Button type="submit" variant="primary" disabled={saving}>{saving ? "Salvando..." : "Salvar"}</Button>
            <Button type="button" onClick={reset}>Limpar</Button>
          </div>
        </form>
      </section>
      <section className="card section-stack" aria-label="Registros existentes">
        <h2>Registros</h2>
        <input aria-label="Buscar registros" placeholder="Buscar na lista"
          value={filter} onChange={e => setFilter(e.target.value)} />
        {loading ? <p>Carregando...</p> : visible.length === 0 ? <p>Nenhum registro encontrado.</p> : (
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead><tr>{fields.slice(0, 4).map(f => <th key={f.key}>{f.label}</th>)}<th>Ação</th></tr></thead>
              <tbody>{visible.map(item => (
                <tr key={item.id}>
                  {fields.slice(0, 4).map(f => <td key={f.key}>{printable(item[f.key])}</td>)}
                  <td><Button type="button" onClick={() => edit(item)}>Editar</Button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
