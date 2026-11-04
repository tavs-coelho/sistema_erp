"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type FaqItem = { group: string; question: string; answer: string; href?: string };

const FAQ: FaqItem[] = [
  { group: "Primeiro acesso", question: "Como entrar no ERP?", answer: "Acesse o endereço institucional de sua entidade, informe usuário e senha. Se a autenticação em duas etapas estiver ativada, informe o código TOTP ou um código de recuperação." },
  { group: "Primeiro acesso", question: "É necessário criar um administrador antes de utilizar o sistema?", answer: "Em uma instalação real sem dados demonstrativos, sim. O administrador inicial é criado offline pelo responsável de infraestrutura, em banco vazio, por meio do comando documentado no manual." },
  { group: "Primeiro acesso", question: "Por que fui solicitado a trocar a senha?", answer: "A senha inicial pode ser marcada como temporária. Informe uma nova senha e entre novamente. A troca revoga sessões anteriores por segurança.", href: "/trocar-senha" },
  { group: "Primeiro acesso", question: "Como escolher o município ou entidade?", answer: "O ambiente identifica a entidade pelo endereço institucional. Órgãos reais diferentes precisam de subdomínios e configurações independentes. Não compartilhe dados entre entidades." },
  { group: "Segurança", question: "Como ativar o Google Authenticator?", answer: "Acesse Segurança da Conta, confirme a senha, cadastre a chave no aplicativo autenticador e valide um código de seis dígitos. Guarde os códigos de recuperação exibidos.", href: "/seguranca" },
  { group: "Segurança", question: "Os códigos de recuperação podem ser reutilizados?", answer: "Não. Cada código é de uso único. Depois de utilizar todos os códigos, procure o administrador responsável antes de perder o acesso." },
  { group: "Segurança", question: "Como encerrar uma sessão de outro computador?", answer: "Acesse Segurança da Conta e a seção Dispositivos e sessões. Revogue apenas aquele dispositivo ou encerre todos. A saída atual também invalida a sessão do backend.", href: "/seguranca" },
  { group: "Segurança", question: "A senha e os tokens ficam guardados no navegador?", answer: "O modo de sessão web utiliza cookies HttpOnly para tokens de acesso e renovação. O navegador não precisa armazenar JWT em localStorage. Nunca envie códigos MFA ou credenciais por e-mail ou chat." },
  { group: "Segurança", question: "O que fazer se a sessão expirar?", answer: "Uma sessão válida pode ser renovada automaticamente. Caso a renovação falhe ou a conta tenha sido revogada, entre novamente no endereço institucional." },
  { group: "Contabilidade", question: "Como começar o exercício financeiro?", answer: "Acesse Contábil, cadastre o ano do exercício e depois a unidade administrativa e o fornecedor, conforme o perfil autorizado.", href: "/fase-2" },
  { group: "Contabilidade", question: "Qual é o fluxo de uma despesa?", answer: "Cadastre dotação orçamentária e empenho vinculados ao exercício, à unidade e ao fornecedor; faça a liquidação e depois registre o pagamento. Confira os registros e os relatórios.", href: "/fase-2" },
  { group: "Contabilidade", question: "Posso registrar pagamento de um empenho inexistente?", answer: "Não. O backend valida a existência do empenho referenciado. As regras de execução orçamentária ainda precisam de homologação normativa antes de uso oficial." },
  { group: "Contabilidade", question: "Como exportar a lista de empenhos?", answer: "Na tela Contábil, utilize Exportar CSV. O download usa a sessão atual sem exibir token no endereço nem em armazenamento JavaScript.", href: "/fase-2" },
  { group: "Compras", question: "Onde consultar processos e contratos?", answer: "Acesse Compras e Contratos no menu para consultar os registros disponíveis. Cada fluxo de contratação deve ser validado pelo responsável antes do uso oficial.", href: "/compras" },
  { group: "Patrimônio", question: "Onde consultar os bens cadastrados?", answer: "No módulo Patrimônio é possível consultar inventário e movimentações conforme permissões. O inventário completo e a integração contábil exigem homologação.", href: "/patrimonio" },
  { group: "Almoxarifado", question: "Como registrar entradas e saídas?", answer: "No módulo Almoxarifado utilize os cadastros, recebimentos, movimentações e requisições disponíveis. A administração deve definir previamente os responsáveis e permissões.", href: "/almoxarifado" },
  { group: "Recursos humanos", question: "Onde consultar folha e contracheques?", answer: "O módulo RH apresenta dados e eventos da folha; o Portal do Servidor concentra informações individuais autorizadas. Cálculos devem passar por homologação antes da adoção.", href: "/rh" },
  { group: "Transparência", question: "É necessário login para o Portal da Transparência?", answer: "Não. A consulta pública é separada da administração. Revise os dados antes da publicação para evitar exposição indevida de informações pessoais.", href: "/public" },
  { group: "Transparência", question: "Um registro interno aparece automaticamente no portal?", answer: "Alguns indicadores e listas públicas são derivados de registros internos. A visibilidade deve ser conferida com os critérios legais e de proteção de dados antes de disponibilização oficial.", href: "/public" },
  { group: "Protocolo", question: "Onde acompanhar processos e tramitações?", answer: "Abra Protocolo e consulte as tramitações e estatísticas. É necessário verificar as permissões e a configuração de unidades antes de registrar documentos oficiais.", href: "/protocolo" },
  { group: "Administração", question: "Onde encontrar histórico de operações?", answer: "O módulo Auditoria apresenta ações registradas pelo backend. Os acessos são sujeitos a permissões e a políticas de retenção.", href: "/auditoria" },
  { group: "Administração", question: "Posso alterar cores e logotipo da entidade?", answer: "O administrador pode configurar a Identidade Visual; o sistema verifica contraste e salva os ajustes institucionais no banco.", href: "/branding" },
  { group: "Suporte", question: "A tela não carrega dados. Como diagnosticar?", answer: "Confirme se a sessão é válida, atualize a página e verifique se os serviços backend e banco estão disponíveis. No Docker, use docker compose ps e docker compose logs backend. Não repita operações financeiras sem verificar se já foram registradas." },
  { group: "Suporte", question: "Posso utilizar a demonstração com dados reais?", answer: "Não. O ambiente de demonstração possui usuários e informações fictícias e não substitui uma implantação homologada com TLS, segredos, backup, segregação entre entidades e LGPD." },
  { group: "Suporte", question: "Como saber se uma funcionalidade atende ao edital?", answer: "Cada requisito do Termo de Referência deve possuir rastreabilidade para código, teste executado e evidência de demonstração. O número de telas ou testes não comprova automaticamente a cobertura exigida." },
];

export default function HelpPage() {
  const [query, setQuery] = useState("");
  const groups = useMemo(() => {
    const term = query.trim().toLocaleLowerCase("pt-BR");
    const entries = FAQ.filter((item) =>
      !term || [item.group, item.question, item.answer].join(" ").toLocaleLowerCase("pt-BR").includes(term)
    );
    return Array.from(new Set(entries.map((item) => item.group))).map((group) => ({
      group, entries: entries.filter((item) => item.group === group),
    }));
  }, [query]);

  return (
    <main className="module-page section-stack">
      <header>
        <h1>Central de Ajuda</h1>
        <p className="muted">Orientações para operar a plataforma e esclarecer os fluxos disponíveis.</p>
      </header>
      <label className="field-group" htmlFor="faq-search">
        Buscar uma dúvida
        <Input id="faq-search" value={query} onChange={(event) => setQuery(event.target.value)}
          placeholder="Ex.: pagamento, autenticação, fornecedor, exportação" />
      </label>
      {groups.length ? groups.map(({ group, entries }) => (
        <Card key={group}>
          <h2>{group}</h2>
          <div className="section-stack">
            {entries.map(({ question, answer, href }) => (
              <details key={question}>
                <summary style={{ cursor: "pointer", fontWeight: 600 }}>{question}</summary>
                <p>{answer}</p>
                {href ? <Link href={href}>Abrir módulo relacionado</Link> : null}
              </details>
            ))}
          </div>
        </Card>
      )) : <p>Não encontramos perguntas com esse termo.</p>}
      <p className="muted">Esta central documenta as funcionalidades já existentes. Regras fiscais,
        contábeis e de saúde exigem homologação específica antes de operação real.</p>
    </main>
  );
}
