"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

export type ToastVariant = "info" | "success" | "error";

type ToastItem = { id: string; message: string; variant: ToastVariant };

type ToastContextValue = { toast: (message: string, variant?: ToastVariant) => void };

const ToastContext = createContext<ToastContextValue | null>(null);

const DISMISS_MS = 4000;

function detectVariant(msg: string): ToastVariant {
  const l = msg.toLowerCase();
  if (l.includes("erro") || l.includes("falha") || l.includes("inválid")) return "error";
  return "success";
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
    const t = timers.current.get(id);
    if (t !== undefined) { clearTimeout(t); timers.current.delete(id); }
  }, []);

  const toast = useCallback((message: string, variant?: ToastVariant) => {
    if (!message) return;
    const id = `${Date.now()}-${Math.random()}`;
    setItems((prev) => [...prev, { id, message, variant: variant ?? detectVariant(message) }]);
    timers.current.set(id, setTimeout(() => dismiss(id), DISMISS_MS));
  }, [dismiss]);

  useEffect(() => {
    const map = timers.current;
    return () => { map.forEach((t) => clearTimeout(t)); map.clear(); };
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {items.length > 0 && (
        <div className="toast-stack" role="region" aria-label="Notificações" aria-live="polite">
          {items.map((item) => (
            <div key={item.id} className={`toast-stack-item${item.variant !== "info" ? ` ${item.variant}` : ""}`} role="status">
              <span>{item.message}</span>
              <button type="button" className="toast-dismiss" onClick={() => dismiss(item.id)} aria-label="Fechar">×</button>
            </div>
          ))}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

