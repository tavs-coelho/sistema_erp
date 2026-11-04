"use client";
import { useEffect, useState } from "react";
import { RegistryEditor, RegistryField } from "@/components/nucleo/registry-editor";
import { authJson } from "@/lib/auth";

export default function UnitsPage() {
  const [departments, setDepartments] = useState<{ id: number; name: string }[]>([]);
  useEffect(() => {
    const task = setTimeout(() => {
      void authJson("/core/departments").then(setDepartments).catch(() => setDepartments([]));
    }, 0);
    return () => clearTimeout(task);
  }, []);
  const fields: RegistryField[] = [
    { key: "code", label: "Código da unidade", required: true, readonlyOnEdit: true },
    { key: "name", label: "Nome da unidade", required: true },
    { key: "department_id", label: "Secretaria/departamento", kind: "select", required: true,
      options: departments.map(d => ({ value: String(d.id), label: d.name })) },
    { key: "address", label: "Endereço administrativo" },
    { key: "active", label: "Unidade ativa", kind: "checkbox", readonlyOnEdit: false },
  ];
  return <RegistryEditor title="Unidades municipais"
    description="Cadastre e mantenha unidades por município. Códigos são únicos por entidade; a unidade deve pertencer a uma secretaria da mesma entidade."
    endpoint="/nucleo/unidades" fields={fields} />;
}
