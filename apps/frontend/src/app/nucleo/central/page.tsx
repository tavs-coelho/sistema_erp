"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { authJson, readCookie } from "@/lib/auth";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";

type Notice = { id: number; kind: string; title: string; message: string; read_at: string | null };
type Ticket = { id: number; subject: string; description: string; priority: string; status: string; created_by: number };
type Reply = { id: number; message: string; author_id: number; created_at: string };
type Faq = { topic: string; question: string; answer: string };

export default function SupportPage() {
  const { toast } = useToast();
  const [notices, setNotices] = useState<Notice[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [faq, setFaq] = useState<Faq[]>([]);
  const [faqSearch, setFaqSearch] = useState("");
  const [selected, setSelected] = useState<Ticket | null>(null);
  const [replies, setReplies] = useState<Reply[]>([]);
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("normal");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const isAdmin = readCookie("role") === "admin";

  const load = useCallback(async () => {
    try {
      const [messages, cases, entries] = await Promise.all([
        authJson("/nucleo/central/notificacoes"),
        authJson("/nucleo/central/tickets"),
        authJson("/nucleo/central/faq"),
      ]);
      setNotices(messages as Notice[]); setTickets(cases as Ticket[]); setFaq(entries as Faq[]);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao carregar central", "error");
    }
  }, [toast]);

  const loadReplies = useCallback(async (id: number) => {
    try { setReplies(await authJson(`/nucleo/central/tickets/${id}/respostas`) as Reply[]); }
    catch (error) { toast(error instanceof Error ? error.message : "Falha ao consultar respostas", "error"); }
  }, [toast]);

  useEffect(() => {
    const task = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(task);
  }, [load]);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      await authJson("/nucleo/central/tickets", { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, description, priority }),
      });
      setSubject(""); setDescription("");
      toast("Chamado aberto", "success");
      await load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao abrir chamado", "error");
    } finally { setBusy(false); }
  };

  const markRead = async (id: number) => {
    try {
      await authJson(`/nucleo/central/notificacoes/${id}/ler`, { method: "PATCH" });
      await load();
    } catch (error) { toast(error instanceof Error ? error.message : "Falha ao confirmar leitura", "error"); }
  };

  const sendReply = async (event: FormEvent) => {
    event.preventDefault();
    if (busy || !selected) return;
    setBusy(true);
    try {
      await authJson(`/nucleo/central/tickets/${selected.id}/respostas`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: reply }),
      });
      setReply("");
      await Promise.all([loadReplies(selected.id), load()]);
      toast("Resposta registrada", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao responder", "error");
    } finally { setBusy(false); }
  };

  const updateStatus = async (status: string) => {
    if (!selected || busy) return;
    setBusy(true);
    try {
      const updated = await authJson(`/nucleo/central/tickets/${selected.id}/status`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      }) as Ticket;
      setSelected(updated);
      toast("Situação atualizada", "success");
      await load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Operação não autorizada", "error");
    } finally { setBusy(false); }
  };

  const filteredFaq = faq.filter(entry =>
    `${entry.topic} ${entry.question} ${entry.answer}`.toLowerCase().includes(faqSearch.toLowerCase()));

  return <main className="module-page section-stack" style={{ padding: 24 }}>
    <h1>Central de ajuda e suporte</h1>
    <p className="muted">Notificações pessoais, acompanhamento de chamados e instruções de uso do ERP.</p>
    <section className="card section-stack">
      <h2>Notificações ({notices.filter(n => !n.read_at).length} não lidas)</h2>
      {notices.length === 0 ? <p>Sem notificações.</p> : (
        <ul className="section-stack">{notices.map(n => <li key={n.id}>
          <strong>{n.title}</strong> — {n.message}
          {!n.read_at && <Button type="button" onClick={() => { void markRead(n.id); }}>Marcar como lida</Button>}
        </li>)}</ul>
      )}
    </section>
    <section className="card section-stack">
      <h2>Abrir chamado</h2>
      <form className="section-stack" onSubmit={(event) => { void create(event); }}>
        <label className="field-group">Assunto
          <input required minLength={5} value={subject} onChange={e => setSubject(e.target.value)} />
        </label>
        <label className="field-group">Descrição do problema
          <textarea required minLength={10} value={description} onChange={e => setDescription(e.target.value)} />
        </label>
        <label className="field-group">Prioridade
          <select value={priority} onChange={e => setPriority(e.target.value)}>
            <option value="normal">Normal</option><option value="alta">Alta</option><option value="critica">Crítica</option>
          </select>
        </label>
        <Button type="submit" variant="primary" disabled={busy}>Registrar chamado</Button>
      </form>
    </section>
    <section className="card section-stack">
      <h2>Meus chamados {isAdmin ? "e chamados da entidade" : ""}</h2>
      {tickets.length === 0 ? <p>Sem chamados.</p> : (
        <ul className="section-stack">
          {tickets.map(t => <li key={t.id}>
            <Button type="button" onClick={() => {
              setSelected(t);
              void loadReplies(t.id);
            }}>#{t.id} — {t.subject} ({t.status})</Button>
          </li>)}
        </ul>
      )}
      {selected && <div className="section-stack">
        <h3>Chamado #{selected.id}: {selected.subject}</h3>
        <p>{selected.description}</p>
        <p>Prioridade: {selected.priority} • Situação: {selected.status}</p>
        {isAdmin && selected.status !== "fechado" &&
          <div style={{ display: "flex", gap: 8 }}>
            <Button type="button" disabled={busy} onClick={() => { void updateStatus("em_atendimento"); }}>Em atendimento</Button>
            <Button type="button" disabled={busy} onClick={() => { void updateStatus("resolvido"); }}>Resolver</Button>
            <Button type="button" disabled={busy} onClick={() => { void updateStatus("fechado"); }}>Fechar</Button>
          </div>}
        <h4>Histórico de respostas</h4>
        {replies.length === 0 ? <p>Sem respostas.</p> : (
          <ul>{replies.map(r => <li key={r.id}>{r.message} — {new Date(r.created_at).toLocaleString("pt-BR")}</li>)}</ul>
        )}
        {selected.status !== "fechado" && <form className="section-stack" onSubmit={(e) => { void sendReply(e); }}>
          <label className="field-group">Nova resposta
            <textarea value={reply} minLength={2} required onChange={e => setReply(e.target.value)} />
          </label>
          <Button type="submit" variant="primary" disabled={busy}>Enviar resposta</Button>
        </form>}
      </div>}
    </section>
    <section className="card section-stack">
      <h2>Perguntas frequentes (FAQ)</h2>
      <input aria-label="Pesquisar ajuda" placeholder="Buscar por assunto"
        value={faqSearch} onChange={e => setFaqSearch(e.target.value)} />
      {filteredFaq.map(entry => <details key={entry.question}>
        <summary><strong>{entry.topic}:</strong> {entry.question}</summary>
        <p>{entry.answer}</p>
      </details>)}
      {filteredFaq.length === 0 && <p>Nenhuma orientação encontrada para a pesquisa.</p>}
    </section>
  </main>;
}
