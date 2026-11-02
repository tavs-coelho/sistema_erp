# PR #7 — Segurança de autenticação e segregação multi-entidade

Referência: Issue #5; Pregão Eletrônico nº 66/2026 de Dois Córregos/SP.
Documento técnico do código efetivamente alterado. Não constitui declaração de aderência à prova de conceito.

## Achados confirmados por inspeção do código

| ID | Risco observado antes das alterações | Severidade preliminar | Mitigação nesta branch |
| --- | --- | --- | --- |
| AUTH-01 | Tokens de acesso não verificavam o tenant do usuário | Alta | `app/deps.py` agora valida tenant e situação ativa |
| AUTH-02 | Refresh não verificava tenant nem situação ativa | Alta | `app/routers/auth.py` exige mesmo tenant e usuário ativo |
| AUTH-03 | Confirmação de reset aceitava token de usuário de outra entidade | Alta | `app/routers/auth.py` valida tenant antes de alterar a senha |
| AUTH-04 | Login não rejeitava explicitamente conta desativada | Alta | Login rejeita conta inativa |
| TENANT-01 | Subdomínio não cadastrado era associado ao tenant padrão | Alta | `app/middleware.py` retorna HTTP 404 |
| TENANT-02 | Cadastro e listagem de usuários não filtravam o tenant | Alta | `app/routers/core.py` limita listagem, criação e edição |
| TENANT-03 | Consulta de auditoria podia exibir eventos de outros tenants | Alta | Consulta restrita aos IDs de usuários pertencentes à entidade |
| CONFIG-01 | Singleton `settings` ausente impedia importação do backend | Bloqueante | `app/config.py` restaurado |
| CORE-01 | Referência a `Query` sem importação impedia carregar o router | Bloqueante | Importação corrigida em `app/routers/core.py` |

A análise registra achados de revisão estática; não houve teste ofensivo de exploração contra implantação real.

## Regras de compatibilidade

- Usuários antigos com `tenant_id = NULL` continuam associados **somente** à entidade 1.
- Hosts locais e domínio-base continuam resolvendo para entidade 1; subdomínios desconhecidos não fazem fallback.
- Erros de refresh e reset não informam se outra entidade contém o usuário.
- A expiração de reset aceita data com ou sem informação explícita de fuso retornada pelo banco (interpreta o valor legado sem fuso como UTC).

## Testes e critérios de aceite

Arquivos:
- `apps/backend/tests/test_auth_tenant_boundaries.py`: acesso e refresh cruzados, conta desativada, reset expirado, reset de uso único, usuário legado, isolamento do CRUD de usuários e auditoria.
- `apps/backend/tests/test_password_reset_tenant.py`: solicitação de reset por tenant.
- `apps/backend/tests/test_tenant_middleware_security.py`: host conhecido/desconhecido e localhost.
- `apps/backend/tests/test_production_config.py`: rejeição de configurações padrão no modo produção.

Executar a partir de `apps/backend`:

```bash
pip install -r requirements.txt
DATABASE_URL=sqlite:///./test.db pytest tests/test_auth_tenant_boundaries.py tests/test_password_reset_tenant.py tests/test_tenant_middleware_security.py tests/test_production_config.py -v
DATABASE_URL=sqlite:///./test.db pytest tests/ -v --tb=short
```

O workflow GitHub Actions `.github/workflows/ci.yml` executa suíte backend, lint/build frontend e validação de Docker Compose em PRs. Consultar o resultado do commit atual antes de marcar os testes como aprovados.

## Riscos residuais / trabalhos ainda necessários

1. Modelos de negócio (orçamento, patrimônio, RH, protocolo, etc.) ainda precisam de `tenant_id`, migrações e testes IDOR completos; esta entrega **não** garante isolamento global do ERP.
2. Tokens JWT ainda não possuem revogação persistente, identificação de sessão ou rotação rastreável; logout apenas registra auditoria.
3. Tokens de recuperação ainda são armazenados em formato bruto e não existe entrega transacional de e-mail de recuperação para produção.
4. A consulta de auditoria omite eventos sem `user_id` porque seu modelo ainda não armazena `tenant_id`; adicionar o campo e migrar registros com critério verificável.
5. Limitar tentativas de reset, estabelecer políticas de senha e criar MFA TOTP com códigos de recuperação.
6. Revisar a confiança no cabeçalho `Host` e a configuração do proxy para ambientes de produção.
7. O frontend apresenta erros de lint anteriores a este escopo; corrigir e exigir pipeline completo verde.
8. Rever os defaults de configuração e a instalação dos dados de demonstração antes de publicação externa.

## Rastreabilidade do Termo de Referência

IDs oficiais e percentuais de cobertura não foram preenchidos sem confrontação individual da matriz técnica. **Nenhum requisito deve ser considerado demonstrável apenas por este documento**. Vincular código, teste, resultado de execução e demonstração ao item oficial antes de alterar seu status.
