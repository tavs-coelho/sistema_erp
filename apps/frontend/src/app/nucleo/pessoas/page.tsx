"use client";
import { RegistryEditor, RegistryField } from "@/components/nucleo/registry-editor";

const fields: RegistryField[] = [
  { key: "kind", label: "Tipo de cadastro", kind: "select", required: true, readonlyOnEdit: true,
    options: [{ value: "pessoa", label: "Pessoa" }, { value: "fornecedor", label: "Fornecedor" }] },
  { key: "name", label: "Nome/Razão social", required: true },
  { key: "document", label: "CPF/CNPJ (uso institucional)", readonlyOnEdit: true },
  { key: "email", label: "E-mail", kind: "email" },
  { key: "phone", label: "Telefone" },
  { key: "active", label: "Cadastro ativo", kind: "checkbox" },
];

export default function PartiesPage() {
  return <RegistryEditor title="Pessoas e fornecedores"
    description="Diretório por entidade. CPF/CNPJ não deve ser reproduzido em auditorias ou relatórios públicos; acesso limitado aos perfis autorizados."
    endpoint="/nucleo/pessoas" fields={fields} />;
}
