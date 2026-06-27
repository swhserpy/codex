#!/usr/bin/env bash
# Whitelisted backup script
set -e
BACKUP_DIR="${HOME}/backups"
mkdir -p "$BACKUP_DIR"
tar -czf "${BACKUP_DIR}/codex-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C "${HOME}" codex 2>/dev/null || echo "codex dir not found"
echo "Backup saved to ${BACKUP_DIR}"
ls -lh "${BACKUP_DIR}" | tail -3
