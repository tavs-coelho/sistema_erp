# PR #10 — bootstrap PostgreSQL do zero e auditoria da cadeia Alembic

## Escopo e resultado

Revisão da instalação inicial do ERP Público, partindo de PostgreSQL 16 **vazio e descartável**. A sequência `0001_initial → 0020_device_sessions` é executada integralmente na CI sem realizar um `stamp` prévio, ao contrário do ensaio incremental do PR #9.

Arquivos:
- `apps/backend/alembic/versions/0001_initial.py`: migração inicial limitada a tabelas e colunas históricas; tabela `alembic_version` ampliada de 32 para 128 caracteres no PostgreSQL para revisões antigas mais longas; lista de colunas explicitamente delimitada para impedir que futuras adições ao ORM sejam introduzidas silenciosamente na revisão 0001.
- `apps/backend/alembic/versions/0002_budget_planning.py`: padrões booleanos PostgreSQL portáveis com `sa.true()` para `active`.
- `apps/backend/scripts/verify_fresh_postgres_schema.py`: valida a revisão 0020, todas as tabelas e colunas declaradas no ORM.
- `apps/backend/tests/test_initial_migration.py`: regressão da lista histórica de tabelas/colunas.
- `.github/workflows/ci.yml`: novo job que sobe PostgreSQL 16, aplica `alembic upgrade head` a partir do vazio, compara o esquema com o ORM e importa o app FastAPI.

## Achados confirmados e correções

| Achado por execução | Evidência | Medida |
| --- | --- | --- |
| `0001` utilizava `Base.metadata.create_all()` do ORM atual, criando antecipadamente as tabelas que deveriam surgir nas revisões seguintes | Revisão de código | Migração inicial agora monta só as tabelas históricas, com lista de colunas explícita |
| `0002` especificava `server_default=1` para `Boolean` em PostgreSQL, causando `DatatypeMismatch` | CI com PostgreSQL e migration 0002 | Uso de `sa.true()` |
| `alembic_version.version_num VARCHAR(32)` era insuficiente para identificadores de revisão históricos longos, causando `StringDataRightTruncation` | CI ao gravar a revisão 0007 | Ampliação para `VARCHAR(128)` em instalações PostgreSQL novas |
| Faltava verificação de instalação integral desde banco vazio | Testes incrementais anteriores só verificavam 0019→0020 | CI com `alembic upgrade head` e comparação com modelos |

### Evidência de banco de dados

- <https://github.com/tavs-coelho/sistema_erp/actions/runs/41738215651> — PostgreSQL 16: execução das revisões 0001→0020, 71 tabelas/colunas do ORM verificadas, 284 rotas FastAPI importadas e consulta `SELECT 1` bem-sucedida.
- A execução acima antecede a fixação explícita da lista de colunas. Consultar a CI do commit de revisão final antes de aprovar/mesclar.

## Instruções de reprodução

Em banco **novo e vazio**, definido por `DATABASE_URL`, sem credenciais demonstrativas em produção:

```bash
cd apps/backend
pip install -r requirements.txt
alembic upgrade head
python -m scripts.verify_fresh_postgres_schema
```

Não apontar a verificação acima para banco com dados reais: ela valida a instalação, não efetua backup nem reversão segura.

## Riscos residuais

1. A revisão 0001 usa tipos SQLAlchemy do ORM atual para as colunas históricas listadas. Embora a lista de colunas esteja congelada, **alterações futuras de tipo** exigem cuidado para não mudar implicitamente a revisão histórica. Aumentar a cobertura de comparação de tipos/constraints numa próxima entrega.
2. O teste atual não faz upgrade de bases existentes em produção nem garante downgrade completo da cadeia. Preparar ensaio de migração com backup de homologação e dados sintéticos representativos.
3. A equivalência de tabelas e colunas ainda não comprova índices, constraints, triggers, desempenho, isolamento de entidades em todos os módulos ou conformidade normativa.
4. O ambiente de CI é PostgreSQL descartável; credenciais usadas nele são exclusivas desse ambiente e não devem ser copiadas para produção.
5. Cookies HttpOnly, CSRF, renovação segura de sessão no navegador, gestão de segredos e rotinas de backup/restauração seguem pendentes.
6. Nenhum item do TR de Dois Córregos foi contabilizado como demonstrável nesta entrega sem cruzamento com a matriz oficial e evidências individualizadas.
