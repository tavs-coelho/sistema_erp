# Como executar e usar o ERP Público em ambiente de demonstração

Este procedimento é **local e de homologação**, não uma publicação em produção.
Requer Docker Engine e Docker Compose v2.

## Iniciar os quatro serviços

No diretório raiz do repositório:

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Aguarde os serviços informarem disponibilidade. O backend executa as
migrações Alembic e, com `DEMO_MODE=true`, carrega dados **fictícios**.
O frontend e a API ficam disponíveis por um único endereço:

- **ERP:** http://localhost
- **Documentação OpenAPI:** http://localhost/api/docs
- **Status da API:** http://localhost/api/

Apenas no modo demonstrativo, pode-se utilizar o usuário `admin2` e a
senha `demo123` para percorrer os fluxos. **Nunca** utilize essas
credenciais numa instalação real. A tela de login não vem pré-preenchida.

## Primeiro fluxo operacional — Protocolo

1. Entre com o usuário de demonstração.
2. Abra **Protocolo** no menu lateral.
3. Acesse **Novo protocolo**. Informe tipo, assunto, interessado, data e
   departamentos; deixe o número vazio para geração automática.
4. Salve. O backend atribui um identificador como
   `PROT-2026-00000042` e persiste o registro em PostgreSQL.
5. Abra **Tramitar**, selecione o protocolo, informe o departamento e
   registre o despacho com ação *encaminhado*.
6. Confira o histórico da tramitação, o status e os indicadores da lista.
7. Acesse **Segurança da Conta** para consultar suas sessões e encerrar
   o acesso. O logout revoga a sessão no backend.

O teste automatizado `scripts/smoke_browser_erp.py` verifica esses passos
pela API real através do Nginx (inclui proteção CSRF, cookies HttpOnly,
renovação da sessão e rejeição de token revogado).

## Verificar logs e encerrar

```bash
docker compose logs -f backend frontend nginx
docker compose down
```

Para descartar **apenas os dados da demonstração**, após confirmar que são
descartáveis, utilize `docker compose down -v`. **Nunca** faça isso em um
volume de produção: a opção `-v` exclui o banco armazenado no volume.

## Requisitos mínimos antes de qualquer homologação externa

- `DEMO_MODE=false`, contas de usuários reais e provisionamento seguro.
- `SECRET_KEY` e `MFA_ENCRYPTION_KEY` aleatórios, separados e gerenciados
  fora do Git; banco com senha forte e credenciais individuais.
- `BROWSER_COOKIE_AUTH_ENABLED=true` e `BROWSER_COOKIE_SECURE=true`
  **somente com HTTPS e proxy TLS corretamente configurados**.
- Não expor portas internas PostgreSQL e FastAPI para a Internet.
- Testar backup/restauração, segregação multi-entidade e papéis, políticas
  de autenticação e autorização, e configurações de domínio.
- Validar normas financeiras, contábeis, de RH, saúde e educação para
  cada módulo antes de qualquer alegação de conformidade.

**Limites atuais:** o ERP ainda não está homologado para produção,
a segregação entre entidades permanece parcial nos módulos legados e a
cobertura oficial da prova de conceito de Dois Córregos ainda não foi aferida.
Uma CI verde comprova os fluxos exercitados, não todos os requisitos.
