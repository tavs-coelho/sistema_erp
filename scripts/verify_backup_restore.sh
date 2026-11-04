#!/usr/bin/env bash
# Disposable backup+restore acceptance test. NEVER target an existing DB project.
set -Eeuo pipefail
umask 077
project="erp-restore-ci-$$"
tmp=$(mktemp -d)
export ERP_COMPOSE_PROJECT="$project"
cleanup() {
  docker compose -p "$project" down -v --remove-orphans >/dev/null 2>&1 || :
  rm -rf "$tmp"
}
trap cleanup EXIT
printf '%s\n' 'CI-ONLY-EPHEMERAL-AES256-passphrase' > "$tmp/gpg-pass"
chmod 600 "$tmp/gpg-pass"
export BACKUP_GPG_PASSPHRASE_FILE="$tmp/gpg-pass"
docker compose -p "$project" up -d db
for i in $(seq 1 30); do
  if docker compose -p "$project" exec -T db sh -ec \
      'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker compose -p "$project" exec -T db sh -ec \
  'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE TABLE backup_probe (id integer primary key, value text NOT NULL); INSERT INTO backup_probe VALUES (1, '\''durable-recovery-test'\'');"'
bash scripts/backup_erp.sh "$tmp/erp.gpg"
docker compose -p "$project" exec -T db sh -ec \
  'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP TABLE backup_probe"'
ERP_ALLOW_DESTRUCTIVE_RESTORE=SIM bash scripts/restore_erp.sh "$tmp/erp.gpg"
actual=$(docker compose -p "$project" exec -T db sh -ec \
  'psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT value FROM backup_probe WHERE id=1"')
[[ "$actual" == "durable-recovery-test" ]] || { echo "FALHA: dados não recuperados" >&2; exit 1; }
printf 'tampering' >> "$tmp/erp.gpg"
if ERP_ALLOW_DESTRUCTIVE_RESTORE=SIM bash scripts/restore_erp.sh "$tmp/erp.gpg"; then
  echo "FALHA: arquivo adulterado foi aceito" >&2; exit 1
fi
echo "PASS: backup criptografado, recuperação e rejeição de adulteração"
