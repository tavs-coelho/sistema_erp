# ERP — Backup e restauração (PR #13)

Os scripts realizam backup lógico do PostgreSQL por pg_dump custom, cifrado por GnuPG AES-256, e restauração por pg_restore. O dump puro não é gravado no host. Backup e SHA-256 têm permissões 0600.

## Como usar
Pré-requisitos: Docker Compose v2, GnuPG e um arquivo de senha privado com permissões 0600. Use secrets manager para gerenciar a senha fora do GitHub.

Defina ERP_COMPOSE_PROJECT=erp-homologacao e BACKUP_GPG_PASSPHRASE_FILE=/caminho/privado/passphrase.

Execute: bash scripts/backup_erp.sh /diretorio/seguro/erp-data.gpg

Restauração destrutiva APENAS em destino autorizado: ERP_ALLOW_DESTRUCTIVE_RESTORE=SIM bash scripts/restore_erp.sh /diretorio/seguro/erp-data.gpg

O script confere integridade e autenticação/descriptografia antes do pg_restore. A restauração não é transação única: falhas podem deixar o banco incompleto. Fazer cópia do destino antes de qualquer restauração.

## Teste automatizado
O workflow cria uma base PostgreSQL descartável, grava registro sintético, gera backup criptografado, apaga a tabela, restaura e verifica o valor. Adultera o backup depois e exige recusa da restauração. Elimina o volume e o arquivo de senha ao terminar.

## Pendências de produção
É necessário implementar backup consistente dos anexos físicos (em /data/uploads), agendamento, retenção, teste offsite, verificação de restauração periódica, rotação de chaves e proteção do armazenamento. Nenhum dado real deve ir à CI. Isso NÃO comprova recuperação completa de desastre.
