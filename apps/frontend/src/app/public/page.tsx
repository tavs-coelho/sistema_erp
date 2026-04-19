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

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/public/commitments?search=${encodeURIComponent(search)}&page=${page}&size=10`).then((r) => r.json()),
      fetch(`${API_URL}/public/payments?page=${page}&size=10`).then((r) => r.json()),
    ]).then(([commitmentsData, paymentsData]) => {
      setItems(commitmentsData.items || []);
      setPayments(paymentsData.items || []);
    });
  }, [search, page]);

  return (
    <main style={{ padding: 24, fontFamily: "Arial, sans-serif", display: "grid", gap: 12 }}>
      <h1>Portal da Transparência</h1>
      <p>Consulta pública de empenhos e pagamentos sem autenticação. Registros criados internamente ficam visíveis aqui.</p>
      <input placeholder="Buscar descrição" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
      <a href={`${API_URL}/public/commitments?search=${encodeURIComponent(search)}&export=csv`} target="_blank"> Exportar CSV</a>
      <table border={1} cellPadding={6} style={{ marginTop: 12 }}>
        <thead>
          <tr>
            <th>Número</th>
            <th>Descrição</th>
            <th>Valor</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.number}</td>
              <td>{item.description}</td>
              <td>R$ {item.amount.toFixed(2)}</td>
              <td>{item.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
      <span> Página {page} </span>
      <button disabled={items.length < 10} onClick={() => setPage((p) => p + 1)}>Próxima</button>

      <section className="card">
        <h2>Pagamentos publicados</h2>
        <table border={1} cellPadding={6}>
          <thead><tr><th>ID</th><th>Empenho</th><th>Valor</th><th>Data</th></tr></thead>
          <tbody>
            {payments.map((row) => (
              <tr key={row.id}>
                <td>{row.id}</td><td>{row.commitment_id}</td><td>R$ {row.amount.toFixed(2)}</td><td>{row.payment_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
