"use client";

import { useCallback, useEffect, useState } from "react";
import { RegistryEditor, RegistryField } from "@/components/nucleo/registry-editor";
import { authJson, apiFetch, authDownload } from "@/lib/auth";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";

type Document = { id: number; code: string; title: string; latest_version: number; classification: string; status: string };
type Version = { id: number; version: number; original_name: string; size_bytes: number; content_sha256: string };

const fields: RegistryField[] = [
  { key: "code", label: "Código do documento", required: true, readonlyOnEdit: true },
  { key: "title", label: "Título", required: true },
  { key: "classification", label: "Classificação", kind: "select", required: true, readonlyOnEdit: true,
    options: [
      { value: "interno", label: "Interno — servidores autorizados" },
      { value: "restrito", label: "Restrito — criador ou administrador" },
      { value: "publico", label: "Público na entidade" },
    ] },
  { key: "protocol_id", label: "ID de protocolo vinculado (opcional)", kind: "number", readonlyOnEdit: true },
  { key: "status", label: "Situação", kind: "select",
    options: [{ value: "ativo", label: "Ativo" }, { value: "arquivado", label: "Arquivado" }] },
];

export default function DocumentsPage() {
  const { toast } = useToast();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [versions, setVersions] = useState<Version[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const docs = await authJson("/nucleo/documentos") as Document[];
      setDocuments(docs);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao listar documentos", "error");
    }
  }, [toast]);

  const loadVersions = useCallback(async (id: string) => {
    if (!id) { setVersions([]); return; }
    try { setVersions(await authJson(`/nucleo/documentos/${id}/versions`) as Version[]); }
    catch (error) { toast(error instanceof Error ? error.message : "Falha ao consultar versões", "error"); }
  }, [toast]);

  useEffect(() => {
    const task = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(task);
  }, [load]);

  const upload = async () => {
    if (!selectedId || !file || busy) return;
    setBusy(true);
    try {
      const body = new FormData();
      body.set("file", file);
      const response = await apiFetch(`/nucleo/documentos/${selectedId}/versions`, {
        method: "POST", body,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Falha no envio");
      toast(`Versão ${data.version} registrada e auditada`, "success");
      setFile(null);
      await Promise.all([load(), loadVersions(selectedId)]);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Erro no envio", "error");
    } finally { setBusy(false); }
  };

  return <main className="module-page section-stack">
    <RegistryEditor title="Documentos institucionais"
      description="Crie registros e mantenha versões imutáveis. Arquivos são protegidos por entidade, classificação e permissão."
      endpoint="/nucleo/documentos" fields={fields} />
    <section className="card section-stack" style={{ padding: 20, margin: 24 }}>
      <h2>Versões e arquivos</h2>
      <Button type="button" onClick={() => { void load(); }}>Atualizar lista de documentos</Button>
      <label className="field-group">Documento
        <select value={selectedId} onChange={e => {
          setSelectedId(e.target.value);
          void loadVersions(e.target.value);
        }}>
          <option value="">Selecione</option>
          {documents.map(d => <option key={d.id} value={d.id}>
            {d.code} — {d.title} (v{d.latest_version})
          </option>)}
        </select>
      </label>
      {selectedId ? <>
        <label className="field-group">Nova revisão (PDF, PNG, JPG ou texto; até 8 MB)
          <input type="file" accept=".pdf,.png,.jpg,.jpeg,.txt"
            onChange={e => setFile(e.target.files?.[0] || null)} />
        </label>
        <Button type="button" variant="primary" disabled={!file || busy}
          onClick={() => { void upload(); }}>
          {busy ? "Enviando..." : "Registrar nova versão"}
        </Button>
        {versions.length === 0 ? <p>Não há versões.</p> : (
          <ul className="section-stack">
            {versions.map(v => <li key={v.id}>
              Versão {v.version}: {v.original_name} ({v.size_bytes} bytes)
              <Button type="button" onClick={() => {
                void authDownload(`/nucleo/documentos/${selectedId}/versions/${v.id}/download`, v.original_name)
                  .catch(err => toast(err instanceof Error ? err.message : "Falha no download", "error"));
              }}>Baixar</Button>
            </li>)}
          </ul>
        )}
      </> : <p>Escolha um documento para consultar ou enviar versões.</p>}
    </section>
  </main>;
}
