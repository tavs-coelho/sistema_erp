#!/usr/bin/env bash
# Stream encrypted PostgreSQL logical backup: no plaintext host file.
set -Eeuo pipefail
umask 077
die() { echo "ERRO: $*" >&2; exit 1; }
[[ $# -eq 1 ]] || die "Uso: BACKUP_GPG_PASSPHRASE_FILE=/seguro/senha scripts/backup_erp.sh /backup/erp.gpg"
output=$1
passfile=$BACKUP_GPG_PASSPHRASE_FILE
[[ -r "$passfile" && -s "$passfile" ]] || die "Arquivo privado de senha GPG obrigatório."
[[ ! -e "$output" ]] || die "Destino já existe (backups imutáveis)."
[[ -d "$(dirname "$output")" ]] || die "Diretório não encontrado."
command -v gpg >/dev/null || die "GnuPG indisponível."
command -v docker >/dev/null || die "Docker indisponível."
project=erp-backup
if [[ -n "$ERP_COMPOSE_PROJECT" ]]; then project=$ERP_COMPOSE_PROJECT; fi
tmp="$output.partial.$$"
trap 'rm -f "$tmp"' EXIT
docker compose -p "$project" exec -T db sh -ec \
  'exec pg_dump -Fc --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  | gpg --batch --yes --pinentry-mode loopback --passphrase-file "$passfile" \
      --symmetric --cipher-algo AES256 --output "$tmp"
[[ -s "$tmp" ]] || die "Backup vazio."
chmod 600 "$tmp"
mv "$tmp" "$output"
sha256sum "$output" > "$output.sha256"
chmod 600 "$output.sha256"
echo "Backup cifrado e SHA-256: $output"
