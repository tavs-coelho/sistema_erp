# PR 16 — Cadastro integrado de pessoas e fornecedores

Diretório institucional próprio por entidade, com pessoas e contatos de fornecedores, CRUD com busca, CPF/CNPJ normalizado, e-mail/telefone, desativação e auditoria sem dados documentais. Operadores autorizados: administração, compras e contabilidade.

**Uso:** Núcleo → Pessoas/Fornecedores; selecione tipo, nome, CPF/CNPJ quando necessário, salve, consulte e atualize. Não forneça dados pessoais reais em ambiente demonstrativo. Execute `pytest tests/test_nucleo_pessoas.py -q`.

**Limitação intencional:** não migra nem altera a tabela legada `vendors`, que é global. Até que compras/contratos/contabilidade estejam segregados por tenant, a sincronização automática seria insegura. Este diretório não equivale ainda à integração financeira de fornecedores.

**POC:** status implementado em branch, verificação item-a-item do TR pendente.
