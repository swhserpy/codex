"""Telegram Bot for server management + DeepSeek chat proxy + AI Agent.

No external dependencies. Runs alongside assistant.py.
"""

import json
import os
import subprocess
import threading
import time
import urllib.request

TOKEN = "8818484788:AAEUkVKt9BB8NlBbZCqtoFQyMmTqRCew2Sw"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"
LOCAL_PROXY = "http://localhost:18874"
ALLOWED_USER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bot_user")
AUTHORIZED_USER = None


def tg_url(method):
    return f"{TELEGRAM_API}/{method}"


def tg_request(method, data=None, timeout=10):
    """Send a request to Telegram Bot API."""
    url = tg_url(method)
    if data:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[TG] API error: {e}")
        return None


def send_msg(chat_id, text, parse_mode=None):
    data = {"chat_id": chat_id, "text": text}
    if parse_mode:
        data["parse_mode"] = parse_mode
    return tg_request("sendMessage", data)


def send_typing(chat_id):
    tg_request("sendChatAction", {"chat_id": chat_id, "action": "typing"})


def get_updates(offset=None):
    data = {"timeout": 25, "allowed_updates": ["message"]}
    if offset:
        data["offset"] = offset
    return tg_request("getUpdates", data, timeout=30)


def is_authorized(user_id):
    global AUTHORIZED_USER
    if AUTHORIZED_USER and AUTHORIZED_USER != user_id:
        return False
    return True


def authorize_user(user_id):
    global AUTHORIZED_USER
    AUTHORIZED_USER = user_id
    try:
        with open(ALLOWED_USER_FILE, "w") as f:
            f.write(str(user_id))
        print(f"[TG] Authorized user: {user_id}")
        return True
    except Exception as e:
        print(f"[TG] Failed to save authorized user: {e}")
        return False


def load_authorized_user():
    global AUTHORIZED_USER
    try:
        with open(ALLOWED_USER_FILE) as f:
            user_id = int(f.read().strip())
            AUTHORIZED_USER = user_id
            print(f"[TG] Loaded authorized user: {user_id}")
            return True
    except (FileNotFoundError, ValueError):
        return False


def exec_cmd(cmd, timeout=120):
    """Run a shell command, return output."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        output = r.stdout or ""
        if r.stderr:
            output += "\n⚠ " + r.stderr[:1000]
        if not output:
            output = "(no output)"
        if len(output) > 3500:
            output = output[:3500] + "\n... (truncated)"
        return output, r.returncode
    except subprocess.TimeoutExpired:
        return "Command timed out", -1
    except Exception as e:
        return f"Error: {e}", -1


def get_server_status():
    uptime = exec_cmd("uptime -p", timeout=5)[0].strip()
    disk = exec_cmd("df -h / | tail -1", timeout=5)[0].strip()
    load = exec_cmd("cat /proc/loadavg | awk '{print $1, $2, $3}'", timeout=5)[0].strip()
    ps_check = exec_cmd("ps aux | grep 'python3 assistant.py' | grep -v grep", timeout=5)[0]
    assistant_status = "✅ 运行中" if "assistant.py" in ps_check else "❌ 未运行"
    disk_parts = disk.split()
    disk_info = f"{disk_parts[2]} / {disk_parts[1]} ({disk_parts[4]})" if len(disk_parts) >= 5 else disk
    return (
        f"📊 **服务器状态**\n\n"
        f"⏱ 运行时间: {uptime}\n"
        f"📈 负载: {load}\n"
        f"💾 磁盘: {disk_info}\n"
        f"🤖 Assistant: {assistant_status}"
    )


def get_usage():
    try:
        req = urllib.request.Request(f"{LOCAL_PROXY}/api/usage")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return f"❌ 获取用量失败: {e}"
    today = data.get("today", {})
    total = today.get("_total", {})
    if not total:
        return "📊 今日暂无使用记录"
    models_html = ""
    for k, v in today.items():
        if k == "_total" or not isinstance(v, dict) or "requests" not in v:
            continue
        models_html += f"  • {k}: {v.get('requests', 0)} 次, {fmt_t(v.get('total_tokens', 0))}, ¥{v.get('cost', 0):.6f}\n"
    return (
        f"📊 **DeepSeek 用量**\n\n"
        f"**今日汇总**\n"
        f"  • 请求: {total.get('requests', 0)} 次\n"
        f"  • Token: {fmt_t(total.get('total_tokens', 0))}\n"
        f"  • 费用: ¥{total.get('cost', 0):.6f}\n\n"
        f"**按模型**\n{models_html or '  (无)'}"
    )


def get_balance():
    try:
        req = urllib.request.Request(f"{LOCAL_PROXY}/api/balance")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return f"❌ 获取余额失败: {e}"
    info = data.get("balance_infos", [{}])[0]
    return (
        f"💰 **DeepSeek 余额**\n\n"
        f"• 总余额: **¥{info.get('total_balance', '--')}**\n"
        f"• 状态: {'✅ 正常' if data.get('is_available', False) else '❌ 异常'}"
    )


def fmt_t(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(n)


def run_agent(task):
    """调用 agent.py 执行自动化任务，返回 (output, success)。"""
    try:
        r = subprocess.run(
            ["python3", "-u", "/home/ubuntu/agent.py", task],
            capture_output=True, text=True, timeout=120
        )
        output = (r.stdout or "") + (r.stderr or "")
        if len(output) > 3800:
            output = output[:3800] + "\n\n... (truncated)"
        return output, r.returncode == 0
    except subprocess.TimeoutExpired:
        return "⏱ Agent 执行超时 (120s)", False
    except Exception as e:
        return f"❌ Agent 执行失败: {e}", False


def chat_with_deepseek(chat_id, text):
    send_typing(chat_id)
    payload = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": text}],
        "max_tokens": 4096,
    }
    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(f"{LOCAL_PROXY}/api/chat", data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp_data = json.loads(resp.read().decode())
        if not resp_data.get("choices"):
            return f"❌ DeepSeek 无响应"
        reply = resp_data["choices"][0]["message"]["content"]
        rc = resp_data["choices"][0]["message"].get("reasoning_content")
        output = reply
        if rc:
            output = f"🧠 **深度思考**\n{rc}\n\n---\n\n{output}"
        if len(output) > 3800:
            output = output[:3800] + "\n\n... (truncated)"
        return output
    except Exception as e:
        return f"❌ 调用 DeepSeek 失败: {e}"


def handle_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = msg.get("text", "").strip()

    if not is_authorized(user_id):
        if not AUTHORIZED_USER and not load_authorized_user():
            authorize_user(user_id)
            send_msg(chat_id, "✅ 已授权，你可以使用本 Bot 了。")
        else:
            send_msg(chat_id, "❌ 未授权，请联系管理员。")
        return

    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/start":
            send_msg(chat_id, (
                "🤖 **Server Bot**\n\n"
                "**管理命令:**\n"
                "  /status — 服务器状态\n"
                "  /usage — DeepSeek 用量\n"
                "  /balance — DeepSeek 余额\n"
                "  /exec `<cmd>` — 执行 shell 命令\n"
                "  /restart — 重启 Assistant\n\n"
                "**🤖 AI 自动化:**\n"
                "  /task `<描述>` — 用自然语言指挥 AI 自动干活\n\n"
                "**对话:**\n"
                "  发送普通文字 → 与 DeepSeek 聊天\n\n"
                "**/task 示例:**\n"
                "  `/task 看看 index.html 有多少行`\n"
                "  `/task 把 honeymoon.html 里的标题改成红色`\n"
                "  `/task 检查服务器磁盘空间`"
            ), parse_mode="Markdown")

        elif cmd == "/status":
            send_msg(chat_id, get_server_status(), parse_mode="Markdown")

        elif cmd == "/usage":
            send_msg(chat_id, get_usage(), parse_mode="Markdown")

        elif cmd == "/balance":
            send_msg(chat_id, get_balance(), parse_mode="Markdown")

        elif cmd == "/exec":
            if not arg:
                send_msg(chat_id, "用法: /exec `<command>`")
                return
            send_typing(chat_id)
            output, rc = exec_cmd(arg)
            send_msg(chat_id, f"`$ {arg}`\n退出码: {rc}\n\n```\n{output}\n```", parse_mode="Markdown")

        elif cmd == "/restart":
            send_typing(chat_id)
            output, rc = exec_cmd(
                "pkill -f 'assistant.py' 2>/dev/null; "
                "cd /home/ubuntu && nohup python3 assistant.py > /tmp/assistant.log 2>&1 &"
            )
            time.sleep(2)
            send_msg(chat_id, "♻️ Assistant 已重启")

        elif cmd == "/task":
            if not arg:
                send_msg(chat_id, "用法: /task `<任务描述>`\n\n例如: `/task 看看 index.html 有多少行`")
                return
            send_typing(chat_id)
            send_msg(chat_id, f"🤔 AI 正在分析任务...\n\n`{arg}`")
            send_typing(chat_id)
            output, success = run_agent(arg)
            send_msg(chat_id, output, parse_mode="Markdown")

        else:
            send_msg(chat_id, f"未知命令: {cmd}\n发送 /start 查看可用命令")

    else:
        reply = chat_with_deepseek(chat_id, text)
        send_msg(chat_id, reply, parse_mode="Markdown")


def main():
    print("[TG] Bot starting...")
    load_authorized_user()
    offset = 0
    while True:
        try:
            updates = get_updates(offset)
            if updates and updates.get("ok") and updates.get("result"):
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    if msg and msg.get("text") is not None:
                        threading.Thread(target=handle_message, args=(msg,), daemon=True).start()
        except KeyboardInterrupt:
            print("\n[TG] Bot shutting down.")
            break
        except Exception as e:
            print(f"[TG] Poll error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
