"""Server Console configuration."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Whitelisted log files (key → path)
LOG_FILES = {
    "assistant": "/home/ubuntu/assistant.log",
    "dashboard": "/tmp/assistant.log",
    "telegram_bot": "/tmp/tg_bot.log",
    "system_auth": "/var/log/auth.log",
    "syslog": "/var/log/syslog",
}

# Whitelisted task scripts (key → path)
TASK_SCRIPTS = {
    "backup": "/home/ubuntu/scripts/backup.sh",
    "cleanup": "/home/ubuntu/scripts/cleanup.sh",
    "restart_dashboard": "/home/ubuntu/restart_dashboard.sh",
}

# Telegram bot config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
