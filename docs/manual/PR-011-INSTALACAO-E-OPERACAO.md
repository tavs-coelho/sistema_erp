# ERP Público — implantação local verificável e manual de operação (PR #11)

Este roteiro descreve o sistema existente, não a conformidade jurídica ou
a aptidão para o edital de Dois Córregos. A demonstração usa dados fictícios.

## 1. Executar localmente com Docker

Pré-requisitos: Docker Engine/Compose atualizados, portas 80, 3000 e 8000
livres no computador, Git, recursos suficientes para PostgreSQL, Python e Next.js.

```bash
git clone https://github.com/tavs-coelho/sistema_erp.git
cd sistema_erp
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Na branch deste PR, o Docker Compose habilita apenas para demonstração local:
`DEMO_MODE=true`, `BROWSER_COOKIE_AUTH_ENABLED=true` e
`BROWSER_COOKIE_SECURE=false` (somente HTTP local). A interface é servida
em **http://localhost/login** pelo Nginx; acesso direto ao Next.js em
**http://127.0.0.1:3000/login** também usa proxy interno.

Em modo **exclusivamente demonstrativo**, é possível autenticar como
`admin2` com a senha de exemplo definida em `app/seed.py`.
O usuário `admin1` exige troca de senha no primeiro acesso. Essas contas
nunca devem existir em produção; o backend não as cria com `DEMO_MODE=false`.

## 2. Primeira utilização: operação contábil

1. Entrar e abrir **Contábil** no menu; a tela deve carregar os registros
   existentes sem exigir que o usuário clique em "atualizar".
2. Cadastrar um **exercício financeiro** pela seção 0, se necessário.
3. Criar a unidade administrativa/departamento e um fornecedor.
4. Cadastrar dotação e empenho com número, exercício, unidade, fornecedor e valor.
5. Na lista, selecionar um empenho e **liquidar**.
6. Registrar o pagamento com data e valor.
7. Consultar o empenho como pago na lista e verificar dados publicados em
   **Transparência**.
8. Exportar CSV pelos botões (requisição autenticada, sem expor tokens).

Os passos acima integram interface, API FastAPI e PostgreSQL. A publicação
de dados no portal público deve observar regras locais e revisão de LGPD
antes de uso oficial. Não cadastrar pessoas reais no modo de demonstração.

## 3. Segurança da conta

- **Segurança da Conta** permite ativar o segundo fator TOTP e obter códigos
  de recuperação exibidos uma vez. Definir `MFA_ENCRYPTION_KEY` fora do
  repositório antes da configuração.
- O login no navegador usa JWTs **somente em cookies HttpOnly**; o frontend
  não guarda `access_token` em `localStorage`.
- Requisições com alterações passam por CSRF assinado e checagem de
  origem; refresh é rotativo e sessões podem ser encerradas individualmente.
- Quando ocorre troca de senha, MFA ou logout, o backend revoga tokens e o
  frontend volta ao login. Contas com MFA não completam login sem segundo fator.
- O middleware Next.js só oferece redirecionamento visual; **autorização real
  é feita pelo backend**.

## 4. Uma entidade real, sem dados de demonstração

**Não publicar diretamente esta configuração HTTP em produção.**
Antes de homologar: TLS no proxy de borda, segredos em cofre,
`DEMO_MODE=false`, `BROWSER_COOKIE_AUTH_ENABLED=true`,
`BROWSER_COOKIE_SECURE=true`, credenciais únicas de PostgreSQL, banco
migrado e backup verificável.

Com o banco **vazio, já migrado**, existe um comando administrativo offline
para criar o primeiro usuário de uma entidade. No contêiner backend, com
as variáveis seguras provenientes de cofre, executar:

```bash
python -m scripts.bootstrap_admin
```

Variáveis obrigatórias: `ERP_BOOTSTRAP_ADMIN_USERNAME`,
`ERP_BOOTSTRAP_ADMIN_EMAIL`, `ERP_BOOTSTRAP_ADMIN_PASSWORD` (mínimo de
16 caracteres), `ERP_BOOTSTRAP_ORGANIZATION`.
Ele recusa bancos que já possuem usuários, exige `DEMO_MODE=false`, guarda
apenas hash da senha e obriga troca no primeiro login. Não imprimir senha
em logs ou colocar em comandos versionados. Administradores adicionais
devem ser criados pelo fluxo autorizado do ERP.

## 5. Diagnóstico

```bash
docker compose ps
docker compose logs --tail=150 backend
docker compose logs --tail=150 frontend
docker compose logs --tail=150 nginx
curl -i http://127.0.0.1:8000/
curl -i http://127.0.0.1/api/auth/browser/csrf
```

Se a autenticação falhar, conferir se o backend completou `alembic upgrade
head`, se o banco foi inicializado no modo escolhido, se o domínio/porta
de `Origin` coincide com `Host`, e se os cookies HttpOnly e CSRF estão
sendo definidos no mesmo host. Não compartilhar segredos nem tokens.

O teste de integração em CI sobe Docker, Nginx, PostgreSQL e navegador
Chromium, verifica login, CSRF, refresh, cadastro financeiro, visibilidade
na transparência e logout. Consultar a execução do SHA atual do PR;
não alegar "E2E aprovado" sem o job verde.

## 6. Limitações relevantes

- Migração de autenticação não equivale à implementação de todos os módulos.
  Há funcionalidades parciais e fluxos que dependem de integrações externas.
- O isolamento completo dos dados de 21 módulos entre municípios ainda está
  pendente. A versão atual **não deve atender múltiplos órgãos reais** antes
  de migrações transversais e testes IDOR.
- Ainda faltam homologações de sistemas legais/contábeis, testes de carga,
  política de backup e restauração, e evidências individuais da POC.
- Não manter dados pessoais ou contratos reais no ambiente demonstrativo.
- O frontend tem uma página de ajuda inicial; o FAQ por módulo será expandido
  durante a implementação das regras de negócio.
