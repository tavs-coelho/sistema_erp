"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

type Commitment = { id: number; number: string; description: string; amount: number; status: string };

export default function PublicPage() {
  const [items, setItems] = useState<Commitment[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetch(`${API_URL}/public/commitments?search=${encodeURIComponent(search)}&page=${page}&size=10`)
      .then((r) => r.json())
      .then((d) => setItems(d.items || []));
  }, [search, page]);

  return (
    <main style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
      <h1>Portal da Transparência</h1>
      <p>Consulta pública de empenhos sem autenticação.</p>
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
    </main>
  );
}
