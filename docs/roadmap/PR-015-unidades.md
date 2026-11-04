# PR 15 — Entidades e unidades municipais

Implementado: cadastro, pesquisa, edição e desativação de unidades administrativas, com vínculo obrigatório a departamento da entidade, código único por município, registros de auditoria, interface e teste de IDOR com duas entidades.

**Como testar:** faça login como administrador em ambiente de homologação; abra **Núcleo Municipal → Unidades**; selecione uma secretaria, informe código e nome, salve, filtre e edite. Administradores de uma entidade não devem ver ou editar os registros de outra. Testes API: `pytest tests/test_nucleo_unidades.py -q`.

**Limites:** não substitui CNES/CNPJ oficial de estabelecimento, não importa bases externas e não valida legislação municipal específica. Usuários de leitura só consultam; integração com alocação de servidores ocorre na próxima etapa.

**TR:** sem correspondência item-a-item conferida; status: implementado em branch, demonstração contratual pendente.
