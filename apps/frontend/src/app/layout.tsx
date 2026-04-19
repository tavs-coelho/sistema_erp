import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ERP Municipal Demo",
  description: "MVP de gestão pública municipal",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
