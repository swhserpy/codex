# Server Console

Personal server control panel with monitoring, service management, and task execution.

**Stack:** Next.js (frontend) + FastAPI (backend) + Docker Compose

## Features

- **Dashboard** — CPU, memory, disk, uptime at a glance
- **Services** — View Docker container status (read-only)
- **Logs** — Browse whitelisted log files (last 100 lines)
- **Tasks** — Execute whitelisted scripts safely
- **Auth** — JWT login, no arbitrary shell execution
- **Telegram** — Optional bot notifications

## Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/swhserpy/codex.git
cd codex/server-console
cp .env.example .env
```

Edit `.env` and set your credentials:

```env
SECRET_KEY=generate-a-random-string-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-strong-password
```

### 2. Deploy

```bash
docker compose up -d --build
```

### 3. Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Docs | http://localhost:8000/docs |

## Configuration

### Log Files

Edit `backend/config.py` to add whitelisted log paths:

```python
LOG_FILES = {
    "myapp": "/var/log/myapp.log",
}
```

### Task Scripts

Place executable scripts on the server and add to `backend/config.py`:

```python
TASK_SCRIPTS = {
    "backup": "/path/to/backup.sh",
}
```

### Telegram Notifications

Set in `.env` after creating a bot via [@BotFather](https://t.me/botfather):

```env
TELEGRAM_BOT_TOKEN=123456:ABCdef...
TELEGRAM_CHAT_ID=123456789
```

## Security

- **No arbitrary shell execution** — all commands go through whitelists
- Log and script paths are hardcoded in `config.py`
- JWT tokens expire after 24 hours
- Telegram token is optional and stored in env

## Project Structure

```
server-console/
├── backend/             # FastAPI
│   ├── main.py          # API routes
│   ├── config.py        # Whitelists & settings
│   └── requirements.txt
├── frontend/            # Next.js + Tailwind
│   └── src/pages/       # Login, Dashboard, Services, Logs, Tasks
├── scripts/             # Example whitelisted scripts
├── docker-compose.yml
└── .env.example
```
