#!/usr/bin/env bash
# Destructive restoration is explicitly gated and verifies integrity first.
set -Eeuo pipefail
umask 077
die() { echo "ERRO: $*" >&2; exit 1; }
[[ $# -eq 1 ]] || die "Uso: ERP_ALLOW_DESTRUCTIVE_RESTORE=SIM ... scripts/restore_erp.sh /backup/erp.gpg"
[[ "$ERP_ALLOW_DESTRUCTIVE_RESTORE" == "SIM" ]] || die "Exige ERP_ALLOW_DESTRUCTIVE_RESTORE=SIM"
input=$1
passfile=$BACKUP_GPG_PASSPHRASE_FILE
[[ -r "$input" && -s "$input" && -r "$input.sha256" ]] || die "Backup ou manifesto ausente."
[[ -r "$passfile" && -s "$passfile" ]] || die "Arquivo privado de senha GPG obrigatório."
( cd "$(dirname "$input")" && sha256sum -c "$(basename "$input.sha256")" ) || die "Integridade SHA-256 inválida."
project=erp-backup
if [[ -n "$ERP_COMPOSE_PROJECT" ]]; then project=$ERP_COMPOSE_PROJECT; fi
# Validate GPG authentication and archive format BEFORE changing the database.
fifo=$(mktemp -u)
mkfifo -m 600 "$fifo"
trap 'rm -f "$fifo"' EXIT
gpg --batch --yes --pinentry-mode loopback --passphrase-file "$passfile" --decrypt "$input" > "$fifo" &
pid=$!
if ! docker compose -p "$project" exec -T db sh -ec 'exec pg_restore --list' < "$fifo" >/dev/null; then
  wait "$pid" || :
  die "Arquivo não é um pg_dump íntegro."
fi
wait "$pid" || die "Falha de descriptografia."
gpg --batch --yes --pinentry-mode loopback --passphrase-file "$passfile" --decrypt "$input" \
  | docker compose -p "$project" exec -T db sh -ec \
    'exec pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
echo "Restauração concluída para projeto Compose: $project"
