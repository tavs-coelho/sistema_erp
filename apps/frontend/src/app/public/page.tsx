"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

type Commitment = { id: number; number: string; description: string; amount: number; status: string };

export default function PublicPage() {
  const [items, setItems] = useState<Commitment[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/public/commitments?page=1&size=10`)
      .then((r) => r.json())
      .then((d) => setItems(d.items || []));
  }, []);

  return (
    <main style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
      <h1>Portal da Transparência</h1>
      <p>Consulta pública de empenhos sem autenticação.</p>
      <a href={`${API_URL}/public/commitments?export=csv`} target="_blank">Exportar CSV</a>
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
    </main>
  );
}
