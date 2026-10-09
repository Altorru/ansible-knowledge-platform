#!/bin/bash
set -euo pipefail
umask 077
if [[ -f /etc/knowledge/backup.env ]]; then
  set -a
  source /etc/knowledge/backup.env
  set +a
fi
mkdir -p /var/backups/knowledge
exec 9>/srv/knowledge/publish.lock
flock -w 300 9
systemctl stop forgejo
restart_forgejo() {
  if [[ -n "${partial:-}" ]]; then rm -f "$partial"; fi
  systemctl start forgejo
}
trap restart_forgejo EXIT
archive="/var/backups/knowledge/knowledge-$(date -u +%Y%m%dT%H%M%S)-$$.tar.gz"
partial="${archive}.partial"
tar -C / -czf "$partial" etc/forgejo etc/knowledge var/lib/forgejo srv/knowledge \
  opt/knowledge/requirements.txt opt/knowledge/mkdocs.yml \
  etc/nginx/sites-available/knowledge.conf etc/nginx/knowledge.htpasswd
tar -tzf "$partial" >/dev/null
mv "$partial" "$archive"
systemctl start forgejo
trap - EXIT
if [[ -n "${RESTIC_REPOSITORY:-}" ]]; then
  # Repository must have been initialized deliberately with restic init.
  restic backup "$archive" --tag knowledge
  restic forget --tag knowledge --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
fi
find /var/backups/knowledge -type f -name 'knowledge-*.tar.gz' \
  -mtime "+${BACKUP_RETENTION_DAYS:-7}" -delete
printf 'BACKUP_OK: %s\n' "$archive"
