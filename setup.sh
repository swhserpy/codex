#!/usr/bin/env bash
set -e

REPO="https://github.com/swhserpy/codex.git"
INSTALL_DIR="${CODEX_HOME:-$HOME/codex}"
PYTHON="${PYTHON:-python3}"

echo "============================================"
echo "  DeepSeek Dashboard - 一键安装脚本"
echo "============================================"

# 1. Check Python
if ! command -v $PYTHON &>/dev/null; then
  echo "❌ 未找到 Python3，请先安装: sudo apt install python3"
  exit 1
fi
echo "✅ Python: $($PYTHON --version)"

# 2. Check git
if ! command -v git &>/dev/null; then
  echo "📦 安装 git..."
  sudo apt install -y git
fi

# 3. Clone repo
if [ -d "$INSTALL_DIR" ]; then
  echo "📁 目录 $INSTALL_DIR 已存在，更新中..."
  cd "$INSTALL_DIR" && git pull
else
  echo "📦 克隆仓库..."
  git clone "$REPO" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# 4. Get API Key
if [ -z "$DEEPSEEK_API_KEY" ]; then
  echo ""
  echo "🔑 请输入你的 DeepSeek API Key（留空使用默认占位符）："
  read -r INPUT_KEY
  DEEPSEEK_API_KEY="${INPUT_KEY:-sk-your-key-here}"
fi

# 5. Write API Key
sed -i "s/API_KEY = \".*\"/API_KEY = \"$DEEPSEEK_API_KEY\"/" assistant.py
echo "✅ API Key 已配置"

# 6. Reset usage tracker
echo '{}' > usage_tracker.json

# 7. Create systemd service
echo ""
echo "⚙️ 创建 systemd 服务..."
sudo tee /etc/systemd/system/dashboard.service > /dev/null << UNIT
[Unit]
Description=DeepSeek Personal Assistant Dashboard
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$PYTHON $INSTALL_DIR/assistant.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable dashboard.service
sudo systemctl restart dashboard.service

sleep 2
PUBLIC_IP=$(curl -s --max-time 5 http://checkip.amazonaws.com 2>/dev/null || echo 'localhost')

echo ""
echo "============================================"
echo "  ✅ 安装完成！"
echo "============================================"
echo ""
echo "  Dashboard:  http://$PUBLIC_IP:18874/"
echo ""
echo "  管理命令:"
echo "    sudo systemctl status dashboard.service"
echo "    sudo systemctl restart dashboard.service"
echo "    sudo journalctl -u dashboard.service -f"
echo ""
echo "  如需启动 Telegram Bot:"
echo "    cd $INSTALL_DIR && nohup $PYTHON -u tg_bot.py > /tmp/tg_bot.log 2>&1 &"
echo ""

# Verify
if curl -s -o /dev/null -w "" --max-time 5 http://localhost:18874/ 2>/dev/null; then
  echo "  ✅ Dashboard 已启动！"
else
  echo "  ⚠️  Dashboard 启动中，请稍后检查..."
fi
echo ""
