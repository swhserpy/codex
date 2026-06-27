"""DeepSeep 自动化脚本 — 用自然语言指挥服务器干活。

用法:
  python3 agent.py "把 nginx 重启一下"
  python3 agent.py "查看 honeymoon.html 有多少行"
  python3 agent.py "把 index.html 中的标题改成红色"
"""

import json
import os
import subprocess
import sys
import urllib.request

PROXY_URL = "http://localhost:18874/api/chat"


def chat(messages):
    """调用本地 DeepSeek 代理。"""
    payload = {
        "model": "deepseek-v4-flash",
        "messages": messages,
        "max_tokens": 4096,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(PROXY_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp_data = json.loads(resp.read().decode())
        return resp_data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"错误: {e}"


def exec_cmd(cmd, timeout=30):
    """执行一条 shell 命令，返回 (stdout, stderr, returncode)。"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "超时 (30s)", -1
    except Exception as e:
        return "", str(e), -1


def parse_commands(text):
    """从 DeepSeek 回复中提取 ```bash ... ``` 代码块里的命令。"""
    commands = []
    in_block = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```bash"):
            in_block = True
            continue
        if stripped.startswith("```") and in_block:
            in_block = False
            continue
        if in_block and stripped and not stripped.startswith("#"):
            commands.append(stripped)
    return commands


def gather_context():
    """收集服务器上下文，帮助 DeepSeek 理解环境。"""
    ctx = []
    ctx.append(("当前目录", exec_cmd("pwd")[0].strip()))
    ctx.append(("目录结构", exec_cmd("ls -la")[0].strip()))
    ctx.append(("操作系统", exec_cmd("uname -a")[0].strip()))
    ctx.append(("运行中的 Python 进程", exec_cmd(
        "ps aux | grep python3 | grep -v grep | awk '{print $11, $12, $13}'")[0].strip()))
    ctx.append(("监听端口", exec_cmd("ss -tlnp | grep -E '18874|8877|8871' || echo '无'")[0].strip()))
    return "\n".join(f"# {k}\n{v}" for k, v in ctx if v)


def run(task):
    """主流程：用自然语言指令自动化执行服务器操作。"""
    context = gather_context()

    system_prompt = (
        "你是一个 Linux 服务器自动化助手，运行在 Ubuntu 上。\n"
        "用户给你一个任务，你需要生成 bash 命令来完成它。\n\n"
        "规则：\n"
        "- 把命令放在 ```bash ... ``` 代码块中\n"
        "- 每条命令单独一行\n"
        "- 修改文件前先 cat 看一下当前内容\n"
        "- 用 sed、echo、cat 等标准工具操作文件\n"
        "- 只输出命令本身，不要解释\n"
        "- 如果任务不明确，先执行探索性命令（比如 cat/ls），再决定下一步\n"
        "- 不要删除/破坏现有数据\n"
        "- 命令会按顺序在服务器上执行\n\n"
        f"当前服务器状态：\n{context}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    print(f"🤔 思考中...")
    reply = chat(messages)
    commands = parse_commands(reply)

    if not commands:
        print(f"❌ DeepSeek 没有生成可执行的命令。回复原文：\n{reply}")
        return False

    print(f"\n📋 计划执行 {len(commands)} 条命令：")
    for i, cmd in enumerate(commands, 1):
        print(f"  {i}. $ {cmd}")

    print()
    for i, cmd in enumerate(commands, 1):
        print(f"\n▶ [{i}/{len(commands)}] $ {cmd}")
        stdout, stderr, rc = exec_cmd(cmd)
        if stdout:
            print(stdout.rstrip())
        if stderr:
            print(f"⚠ {stderr.rstrip()}", file=sys.stderr)
        if rc != 0:
            print(f"❌ 退出码: {rc}")
            # 尝试让 DeepSeek 修复
            print(f"\n🤔 出错了，让 AI 修复...")
            fix_msgs = messages + [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": (
                    f"命令 `{cmd}` 执行失败 (退出码 {rc})。\n"
                    f"stdout: {stdout[:1000]}\n"
                    f"stderr: {stderr[:1000]}\n"
                    "请给出修复后的命令。"
                )}
            ]
            fix_reply = chat(fix_msgs)
            fix_commands = parse_commands(fix_reply)
            if fix_commands:
                print(f"📋 修复方案:")
                for fc in fix_commands:
                    print(f"  $ {fc}")
                for fc in fix_commands:
                    print(f"\n▶ $ {fc}")
                    s2, e2, rc2 = exec_cmd(fc)
                    if s2: print(s2.rstrip())
                    if e2: print(f"⚠ {e2.rstrip()}")
            return rc == 0

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    task = " ".join(sys.argv[1:])
    success = run(task)
    sys.exit(0 if success else 1)
