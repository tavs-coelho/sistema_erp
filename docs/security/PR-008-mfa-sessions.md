# PR #8 — MFA TOTP e revogação de sessões

Escopo: autenticação e segurança da conta. Referência: Issue #5. **Não é comprovação da POC de Dois Córregos.**

## Implementação
- `app/mfa.py`: TOTP compatível com RFC 6238 (SHA-1, 6 dígitos/30s, tolerância de ±1 janela), comparação resistente a timing e contador para impedir reutilização. Segredo TOTP cifrado com Fernet e chave separada em `MFA_ENCRYPTION_KEY`; sem chave ou com chave inválida, a operação falha fechada (503).
- `app/models.py`: `UserMfa` guarda segredo ativo/pendente cifrado, expiração, contador do último uso e hash do desafio; `MfaRecoveryCode` armazena somente hashes SHA-256 de códigos com 128 bits de entropia.
- `app/routers/auth.py`: ativação mediante senha e código TOTP, login em duas etapas, desafio de 3 minutos com nonce de uso único, recuperação one-time, desativação mediante senha e segundo fator. Verifica conta ativa e tenant. Tenta bloquear a linha de MFA durante o resgate de códigos para evitar corridas em PostgreSQL.
- `app/security.py` / `app/deps.py`: versão de sessão `ver` nos access/refresh JWT; qualquer discrepância invalida tokens existentes. Logout, reset de senha, ativação e desativação do MFA revogam os tokens anteriores **de toda a conta**.
- `app/routers/auth.py`: desafios MFA não podem ser usados como tokens de acesso nem de refresh.
- `apps/frontend/src/app/login/page.tsx`: fluxo de segundo fator no login e remoção das credenciais demo pré-preenchidas.
- `apps/frontend/src/app/seguranca/page.tsx`: autogestão de MFA, chave para cadastro manual no aplicativo autenticador, confirmação, exibição única de backup codes, desativação e novo login.
- Migração `0019_user_mfa_sessions` e configurações `.env.example`.

## Segurança e riscos residuais
| ID | Situação | Severidade preliminar | Validação |
| --- | --- | --- | --- |
| AUTH-11 | Login sem segundo fator em conta com MFA habilitado | Alta | Teste de desafio e segundo fator |
| AUTH-12 | Tokens antigos aceitos após logout/reset | Alta | Testes de versionamento de sessão |
| AUTH-13 | Reuso de TOTP, backup ou desafio | Alta | Testes de uso único |
| AUTH-14 | Segredo TOTP armazenado em texto puro | Alta | Cipher Fernet, teste de criptografia |
| AUTH-15 | Recuperação de MFA de outra entidade | Alta | Teste de separação por tenant |
| AUTH-16 | Tela de login sugeria credenciais demonstrativas | Média | UI sem preenchimento automático |

Severidade classificada por análise de código; estes achados não constituem provas de exploração.

**Pendências importantes:**
- MFA está disponível, mas não é obrigatório por perfil/entidade.
- Revogação é **global por conta**, não por dispositivo; não há catálogo de sessões nem refresh token rotativo.
- JWT do frontend ainda é armazenado em `localStorage` e precisa de migração para sessões com cookies HttpOnly gerenciados no servidor.
- O login sem MFA ainda é permitido para contas que não ativaram o mecanismo.
- A revogação de challenge e consumo TOTP usa controle de estado persistente; garantir transações e bloqueios em PostgreSQL e testar concorrência sob carga.
- A chave de MFA depende de backup, rotação planejada e gerenciamento seguro. Sem a chave, contas habilitadas não conseguem concluir o login; não existe recuperação por e-mail administrativo.
- Revisar expiração, rate limits e logs sob proxy/ambiente multi-worker.
- Corrigir cadeia de migrações histórica: `0001_initial` usa `Base.metadata.create_all()`, potencialmente conflitante com migrações posteriores; não declarar migração inicial validada antes de teste PostgreSQL.
- Não há conformidade comprovada com requisitos tecnológicos específicos do TR sem cruzamento item a item.

## Testes

`tests/test_mfa_sessions.py` abrange RFC 6238, configuração de chave, ativação/código, desafio único, login, recuperação, tenant, desativação, logout e reset de senha.

CI: `.github/workflows/ci.yml`, testes isolados de segurança, backend, lint/build e Docker Compose. **Registrar SHA de commit e resultado da CI antes de marcar como testado.** Nenhum deploy ou merge automático.
