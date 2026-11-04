# PR 17 — Lotação e gestão organizacional de usuários

A administração municipal pode vincular usuários ativos a unidades da própria entidade, consultar lotações ativas, remover e reativar vínculos, além de o usuário consultar suas próprias unidades. API com controle de acesso administrativo, auditoria e UI em **Núcleo → Lotações**.

O vínculo não altera papéis globais (admin, hr, etc.), não concede acesso a documentos de outra secretaria e não substitui RBAC granular. **A autorização dos demais módulos ainda não usa esta tabela de lotação**; a implementação transversal ocorrerá posteriormente.

Teste: `pytest tests/test_nucleo_lotacoes.py -q` com duas entidades e perfis. Não usar dados reais na demonstração.
