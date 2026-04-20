"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Props = {
  empenhado: number;
  pago: number;
  receita: number;
};

const BRL = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v);

export function DashboardChart({ empenhado, pago, receita }: Props) {
  const data = [
    { label: "Empenhado", value: empenhado, fill: "var(--theme-primary)" },
    { label: "Pago", value: pago, fill: "var(--theme-accent)" },
    { label: "Receita", value: receita, fill: "#10b981" },
  ];

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }} barSize={48}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 13, fill: "var(--muted)" }} axisLine={false} tickLine={false} />
        <YAxis
          tickFormatter={(v: number) => BRL(v)}
          tick={{ fontSize: 11, fill: "var(--muted)" }}
          axisLine={false}
          tickLine={false}
          width={90}
        />
        <Tooltip
          formatter={(v: unknown) => [BRL(v as number), "Valor"]}
          contentStyle={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            fontSize: 13,
          }}
          cursor={{ fill: "color-mix(in srgb, var(--theme-primary) 8%, transparent)" }}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry.label} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
