"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

type Commitment = { id: number; number: string; description: string; amount: number; status: string };
type Payment = { id: number; commitment_id: number; amount: number; payment_date: string };

export default function PublicPage() {
  const [items, setItems] = useState<Commitment[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/public/commitments?search=${encodeURIComponent(search)}&page=${page}&size=10`).then((r) => r.json()),
      fetch(`${API_URL}/public/payments?page=${page}&size=10`).then((r) => r.json()),
    ]).then(([commitmentsData, paymentsData]) => {
      setItems(commitmentsData.items || []);
      setPayments(paymentsData.items || []);
    }).finally(() => setLoading(false));
  }, [search, page]);

  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Portal da Transparência</h1>
      <p>Consulta pública de empenhos e pagamentos sem autenticação. Registros criados internamente ficam visíveis aqui.</p>
      <p className="muted">Dica de demo: buscar por <strong>Demo Integrado</strong> ou número <strong>EMP-DEMO-001</strong>.</p>
      <div className="toolbar">
        <input placeholder="Buscar descrição" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        <a className="btn" href={`${API_URL}/public/commitments?search=${encodeURIComponent(search)}&export=csv`} target="_blank">Exportar CSV</a>
      </div>
      {loading ? <p className="notice">Carregando dados públicos...</p> : null}
      <table style={{ marginTop: 12 }}>
        <thead>
          <tr>
            <th>Número</th>
            <th>Descrição</th>
            <th>Valor</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.length > 0 ? (
            items.map((item) => (
              <tr key={item.id}>
                <td>{item.number}</td>
                <td>{item.description}</td>
                <td>R$ {item.amount.toFixed(2)}</td>
                <td><span className={`chip ${item.status}`}>{item.status}</span></td>
              </tr>
            ))
          ) : (
            <tr><td colSpan={4} className="empty-state">Nenhum empenho encontrado para os filtros informados.</td></tr>
          )}
        </tbody>
      </table>
      <div className="pagination">
        <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
        <span> Página {page} </span>
        <button className="btn" disabled={items.length < 10} onClick={() => setPage((p) => p + 1)}>Próxima</button>
      </div>

      <section className="card">
        <h2>Pagamentos publicados</h2>
        <table>
          <thead><tr><th>ID</th><th>Empenho</th><th>Valor</th><th>Data</th></tr></thead>
          <tbody>
            {payments.length > 0 ? (
              payments.map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td><td>{row.commitment_id}</td><td>R$ {row.amount.toFixed(2)}</td><td>{row.payment_date}</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={4} className="empty-state">Nenhum pagamento público encontrado.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
