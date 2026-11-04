# PR #13 — Isolamento de entidades no núcleo administrativo

Escopo de código: `departments`, `protocolos` e `attachments`. **Não** representa segregação de todos os módulos do ERP.

## Mudanças implementadas
- `tenant_id` obrigatório e indexado nos três modelos, ligado a `tenant_branding`, com backfill histórico de registros legados para a entidade 1 via migração 0021.
- Unicidade de nomes de departamentos por entidade (não mais global).
- CRUD de departamentos com filtros por entidade e 404 ao tentar modificar ID de outra entidade.
- CRUD de protocolos com ownership em listagem, consulta, alteração, tramitação, estatísticas e anexos.
- Validação de pertencimento do departamento de origem/destino e da unidade de tramitação.
- Download e exclusão de anexos exigem vínculo ao protocolo e à entidade atual; anexos de outras entidades retornam 404.
- Operações de mutação restritas a perfis administrativo, contabilidade ou compras; leitura de protocolos para usuários autenticados.
- Cadastro global de entidades bloqueado para administradores de organizações secundárias; mensagens SSE legadas globais não são enviadas a entidades secundárias.
- Upload genérico não pode se passar por anexo de protocolo e evita sobrescrita de arquivos por nomes fornecidos pelo cliente.

## Evidências de validação
- `apps/backend/tests/test_platform_tenant.py` verifica isolamento e negação IDOR de consulta, edição, tramitação, anexos, departamentos e permissões read_only, utilizando banco em memória com duas entidades.
- CI do backend, security job e instalação limpa PostgreSQL com migração 0021, em branch separada.
- Em instalação histórica, o índice/constraint de unicidade de nome pode existir ou não; a migração verifica antes de remover.

## Riscos residuais
- Não há ainda ownership transversal em todas as tabelas de contabilidade, folha, compras, BI e demais módulos.
- CPF de servidores, exercícios e diversas tabelas legadas ainda usam unicidade global. Não presumir multi-tenancy integral.
- Protocolo ainda utiliza unicidade global de número; remodelagem por tenant requer migração adicional e revisão de emissão de números existentes.
- Upload de tipos genéricos de outras entidades requer validação por tipo de recurso para impedir IDOR em cada domínio.
- A gestão de entidades está temporariamente limitada à entidade 1; precisa evoluir para perfil administrativo da plataforma distinto dos administradores municipais.
- Não executar migração em dados reais sem backup/ensaio e sem CI verde.
- Status da POC de Dois Córregos ainda não comprovado por matriz individual.
